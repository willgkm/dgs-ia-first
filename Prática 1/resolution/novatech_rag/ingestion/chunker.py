"""`SectionAwareChunker`: divisão section-aware com teto de tokens e overlap.

Decisão central (techspec): o `all-MiniLM-L6-v2` trunca a entrada em ~256 word
pieces; chunks maiores degradam silenciosamente o embedding. Aqui o teto é
respeitado **sem** cortar tabelas nem passos numerados (RF-02): o empacotamento
opera sobre blocos atômicos (`sections.py`) e só quebra entre eles.

Orçamento por chunk = teto − tokens do heading − orçamento de overlap, de modo
que heading + overlap + corpo nunca ultrapassem o teto. O overlap (~10–15%)
repete apenas parágrafos da extremidade do chunk anterior — nunca tabelas/passos.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime, timezone

from ..config import RagConfig
from ..models import Chunk, ChunkMetadata, LoadedDocument, build_chunk
from .sections import Block, BlockKind, Section, parse_sections

__all__ = ["estimate_tokens", "SectionAwareChunker"]

_TOKEN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def estimate_tokens(text: str) -> int:
    """Estima word pieces contando palavras e pontuação. Aproximação determinística
    do tokenizer real, suficiente para impor o teto de ~256 (a produção pode
    injetar o tokenizer exato via `token_counter`)."""
    return len(_TOKEN.findall(text))


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SectionAwareChunker:
    """Implementa o `Chunker` (Protocol). Empacota blocos por seção sob o teto de
    tokens, preservando tabelas/passos e aplicando overlap entre chunks vizinhos."""

    def __init__(
        self,
        config: RagConfig,
        token_counter: Callable[[str], int] = estimate_tokens,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._max_tokens = config.max_chunk_tokens
        self._overlap_ratio = config.chunk_overlap_ratio
        self._count = token_counter
        self._clock = clock

    def split(self, document: LoadedDocument) -> list[Chunk]:
        ingested_at = self._clock()
        chunks: list[Chunk] = []
        for section in parse_sections(document.text):
            chunks.extend(self._split_section(document, section, ingested_at))
        return chunks

    def _split_section(
        self, document: LoadedDocument, section: Section, ingested_at: datetime
    ) -> list[Chunk]:
        heading = section.title
        overlap_budget = round(self._overlap_ratio * self._max_tokens)
        core_budget = max(1, self._max_tokens - self._count(heading) - overlap_budget)

        groups = self._pack_blocks(section.blocks, core_budget)
        texts = self._render_with_overlap(heading, groups, overlap_budget)
        return [
            build_chunk(text, self._metadata(document, heading, ingested_at), ordinal)
            for ordinal, text in enumerate(texts)
        ]

    def _pack_blocks(self, blocks: list[Block], core_budget: int) -> list[list[Block]]:
        groups: list[list[Block]] = []
        current: list[Block] = []
        current_tokens = 0
        for block in blocks:
            block_tokens = self._count(block.text)
            if current and current_tokens + block_tokens > core_budget:
                groups.append(current)
                current, current_tokens = [], 0
            if not current and block_tokens > core_budget:
                groups.append([block])  # bloco atômico maior que o teto: não cortar
                continue
            current.append(block)
            current_tokens += block_tokens
        if current:
            groups.append(current)
        return groups

    def _render_with_overlap(
        self, heading: str, groups: list[list[Block]], overlap_budget: int
    ) -> list[str]:
        texts: list[str] = []
        for index, group in enumerate(groups):
            parts = [heading]
            if index > 0:
                overlap = self._overlap_text(groups[index - 1], overlap_budget)
                if overlap:
                    parts.append(overlap)
            parts.append("\n\n".join(block.text for block in group))
            texts.append("\n\n".join(parts))
        return texts

    def _overlap_text(self, previous_group: list[Block], overlap_budget: int) -> str:
        paragraphs = [b for b in previous_group if b.kind is BlockKind.PARAGRAPH]
        carried: list[str] = []
        tokens = 0
        for block in reversed(paragraphs):
            block_tokens = self._count(block.text)
            if tokens + block_tokens > overlap_budget:
                break
            carried.insert(0, block.text)
            tokens += block_tokens
        return "\n\n".join(carried)

    def _metadata(
        self, document: LoadedDocument, section: str, ingested_at: datetime
    ) -> ChunkMetadata:
        return ChunkMetadata(
            doc_id=document.doc_id,
            doc_title=document.doc_title,
            version=document.version,
            version_date=document.version_date,
            section=section,
            source=document.source,
            is_official=document.is_official,
            ingested_at=ingested_at,
        )
