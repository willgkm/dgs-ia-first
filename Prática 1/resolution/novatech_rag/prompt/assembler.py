"""`StaticPromptAssembler`: compõe o prompt final (estático + dinâmico).

Implementa o `PromptAssembler` (Protocol). Junta o system prompt estático
(versionado, RF-12) com a parte dinâmica — diretivas de runtime (alerta de
conflito G-07/G-08; abstenção G-03), trechos recuperados e a pergunta —
respeitando o orçamento de tokens (RF-04 / RNF-06).

Decisões (techspec, "Prompt estático vs dinâmico + ordenação nas extremidades"):
- Os maiores scores ficam nas extremidades do contexto e os menores no meio, para
  mitigar o efeito *lost in the middle*.
- Ao exceder o `token_budget`, descarta primeiro os trechos de menor score e os
  registra em `dropped_chunks` (o prompt montado nunca ultrapassa o orçamento).
- Quando o `ConflictDetector` apontou divergência, injeta o alerta; quando o
  bundle veio `below_threshold`, injeta a instrução de abstenção + escalada.

`assemble` é puro (CQS): monta e devolve o `AssembledPrompt`, sem mutar estado.
A contagem de tokens é injetável (`token_counter`) — a produção fornece o
tokenizer exato do modelo; o default é uma estimativa determinística local, de
modo que a camada de prompt não depende da camada de ingestão.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from pathlib import Path

from ..models import (
    AssembledPrompt,
    Chunk,
    ConflictGroup,
    RetrievalBundle,
    RetrievalResult,
)

__all__ = [
    "ABSTENTION_DIRECTIVE",
    "StaticPromptAssembler",
    "estimate_prompt_tokens",
    "load_system_prompt",
]

_PROMPT_DIR = Path(__file__).resolve().parent
_TOKEN = re.compile(r"\w+|[^\w\s]", re.UNICODE)

ABSTENTION_DIRECTIVE = (
    "INSTRUÇÃO: Nenhum trecho da documentação responde a esta pergunta. "
    'Responda exatamente "Não encontrei informação sobre isso na documentação '
    'disponível." e recomende escalar para o supervisor ou para a área responsável '
    "(Operações, Compliance ou Comercial). Não responda com conhecimento geral."
)


def estimate_prompt_tokens(text: str) -> int:
    """Estima tokens contando palavras e pontuação — aproximação determinística do
    tokenizer real, suficiente para impor o orçamento de contexto (RNF-06)."""
    return len(_TOKEN.findall(text))


def load_system_prompt(version: str = "v2") -> str:
    """Carrega o system prompt versionado a partir do pacote (`system_prompt_<v>.md`).

    I/O fica aqui, fora do tempo de import (python-conventions): o assembler recebe
    o texto já carregado e permanece testável com prompts arbitrários.
    """
    path = _PROMPT_DIR / f"system_prompt_{version}.md"
    if not path.is_file():
        raise FileNotFoundError(f"System prompt não encontrado: {path}")
    return path.read_text(encoding="utf-8")


class StaticPromptAssembler:
    """Implementa o `PromptAssembler` (Protocol) sobre um system prompt estático."""

    def __init__(
        self,
        system_prompt: str,
        token_counter: Callable[[str], int] = estimate_prompt_tokens,
    ) -> None:
        self._system = system_prompt
        self._count = token_counter

    def assemble(
        self,
        question: str,
        bundle: RetrievalBundle,
        token_budget: int,
    ) -> AssembledPrompt:
        directives = self._build_directives(bundle)
        base_tokens = self._count(self._system) + self._count(question)
        base_tokens += sum(self._count(directive) for directive in directives)
        if base_tokens > token_budget:
            raise ValueError(
                f"token_budget ({token_budget}) insuficiente para o system prompt "
                f"e a pergunta ({base_tokens} tokens)."
            )
        kept, dropped, chunk_tokens = self._select_within_budget(
            bundle.results, token_budget - base_tokens
        )
        chunk_blocks = [block for _, block in self._order_for_edges(kept)]
        return AssembledPrompt(
            system=self._system,
            context_blocks=directives + chunk_blocks,
            question=question,
            estimated_tokens=base_tokens + chunk_tokens,
            dropped_chunks=dropped,
        )

    def _build_directives(self, bundle: RetrievalBundle) -> list[str]:
        if bundle.below_threshold:
            return [ABSTENTION_DIRECTIVE]
        return [self._conflict_alert(group) for group in bundle.conflicts]

    def _conflict_alert(self, group: ConflictGroup) -> str:
        versions = "; ".join(
            f"versão {version.version} ({version.version_date})" for version in group.versions
        )
        return (
            f"ALERTA DE DIVERGÊNCIA: o documento {group.doc_id} possui versões "
            f"divergentes ({versions}). Apresente os valores de ambas as versões ao "
            "atendente, identificando cada uma, e não escolha uma como vigente. "
            "Oriente a confirmar a versão vigente com o supervisor."
        )

    def _select_within_budget(
        self, results: Sequence[RetrievalResult], chunk_budget: int
    ) -> tuple[list[tuple[RetrievalResult, str]], list[Chunk], int]:
        ranked = sorted(results, key=lambda result: result.score, reverse=True)
        kept: list[tuple[RetrievalResult, str]] = []
        used = 0
        for index, result in enumerate(ranked):
            block = self._render_block(result)
            block_tokens = self._count(block)
            if used + block_tokens > chunk_budget:
                dropped = [dropped_result.chunk for dropped_result in ranked[index:]]
                return kept, dropped, used
            kept.append((result, block))
            used += block_tokens
        return kept, [], used

    def _order_for_edges(
        self, ranked: Sequence[tuple[RetrievalResult, str]]
    ) -> list[tuple[RetrievalResult, str]]:
        head: list[tuple[RetrievalResult, str]] = []
        tail: list[tuple[RetrievalResult, str]] = []
        for position, pair in enumerate(ranked):
            if position % 2 == 0:
                head.append(pair)
            else:
                tail.append(pair)
        return head + list(reversed(tail))

    def _render_block(self, result: RetrievalResult) -> str:
        metadata = result.chunk.metadata
        provenance = "fonte oficial" if metadata.is_official else "fonte não oficial — não validada"
        version = f"versão {metadata.version}"
        if metadata.version_date:
            version += f" ({metadata.version_date})"
        header = (
            f"[Documento: {metadata.doc_title} — seção {metadata.section} — "
            f"{version} — {provenance}]"
        )
        return f"{header}\n{result.chunk.text}"
