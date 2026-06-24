"""Testes unitários do `StaticPromptAssembler` (RF-04 / RF-12 / G-03 / G-07).

Sem LLM (o MVP não gera) e sem embeddings: o assembler recebe um `RetrievalBundle`
pronto. Os trechos e scores são construídos diretamente, de modo determinístico,
para verificar orçamento de tokens, ordenação nas extremidades, alerta de conflito
e instrução de abstenção (pytest-testing, Etapa 3).
"""

from __future__ import annotations

from datetime import datetime, timezone

from novatech_rag.models import (
    ChunkMetadata,
    ConflictGroup,
    ConflictVersion,
    DocumentSource,
    RetrievalBundle,
    RetrievalResult,
    build_chunk,
)
from novatech_rag.prompt.assembler import (
    ABSTENTION_DIRECTIVE,
    StaticPromptAssembler,
    estimate_prompt_tokens,
)

_SYSTEM_PROMPT = "System prompt estático de teste."


def make_result(
    score: float,
    rank: int,
    *,
    doc_id: str = "POL-001",
    doc_title: str = "POL-001 — Política",
    version: str = "3.1",
    version_date: str = "2024-01-15",
    section: str = "3.2",
    is_official: bool = True,
    text: str = "conteúdo do trecho recuperado",
) -> RetrievalResult:
    metadata = ChunkMetadata(
        doc_id=doc_id,
        doc_title=doc_title,
        version=version,
        version_date=version_date,
        section=section,
        source=DocumentSource.SHAREPOINT,
        is_official=is_official,
        ingested_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    chunk = build_chunk(text, metadata, rank)
    return RetrievalResult(chunk=chunk, score=score, rank=rank)


def make_assembler() -> StaticPromptAssembler:
    return StaticPromptAssembler(_SYSTEM_PROMPT)


class TestTokenBudget:
    def test_prompt_never_exceeds_token_budget(self) -> None:
        results = [make_result(0.9 - index * 0.1, index, text=f"trecho {index} " * 20)
                   for index in range(5)]
        bundle = RetrievalBundle(results=results)
        budget = estimate_prompt_tokens(_SYSTEM_PROMPT) + estimate_prompt_tokens("pergunta") + 80

        assembled = make_assembler().assemble("pergunta", bundle, token_budget=budget)

        assert assembled.estimated_tokens <= budget

    def test_lowest_scores_are_dropped_when_budget_is_tight(self) -> None:
        results = [
            make_result(0.90, 0, text="alfa " * 15),
            make_result(0.50, 1, text="bravo " * 15),
            make_result(0.20, 2, text="charlie " * 15),
        ]
        bundle = RetrievalBundle(results=results)
        assembler = make_assembler()
        base = estimate_prompt_tokens(_SYSTEM_PROMPT) + estimate_prompt_tokens("pergunta")
        full = assembler.assemble("pergunta", bundle, token_budget=10_000).estimated_tokens
        # Os três trechos têm o mesmo nº de palavras e o mesmo cabeçalho, logo blocos
        # de tamanho uniforme: (full - base) / 3 dá o custo de um bloco.
        block_tokens = (full - base) // 3
        budget = base + 2 * block_tokens + 1

        assembled = assembler.assemble("pergunta", bundle, token_budget=budget)

        dropped_text = " ".join(chunk.text for chunk in assembled.dropped_chunks)
        assert "charlie" in dropped_text
        assert "alfa" not in dropped_text and "bravo" not in dropped_text

    def test_no_chunks_dropped_when_all_fit(self) -> None:
        results = [make_result(0.9, 0), make_result(0.8, 1)]
        bundle = RetrievalBundle(results=results)

        assembled = make_assembler().assemble("pergunta", bundle, token_budget=10_000)

        assert assembled.dropped_chunks == []

    def test_raises_when_budget_below_system_plus_question(self) -> None:
        bundle = RetrievalBundle(results=[make_result(0.9, 0)])
        try:
            make_assembler().assemble("pergunta", bundle, token_budget=1)
        except ValueError as error:
            assert "insuficiente" in str(error)
        else:
            raise AssertionError("esperava ValueError por orçamento insuficiente")


class TestEdgeOrdering:
    def test_highest_scores_sit_at_the_edges(self) -> None:
        results = [make_result(0.9 - index * 0.1, index, text=f"score-{index}")
                   for index in range(5)]
        bundle = RetrievalBundle(results=results)

        assembled = make_assembler().assemble("pergunta", bundle, token_budget=10_000)

        assert "score-0" in assembled.context_blocks[0]
        assert "score-1" in assembled.context_blocks[-1]
        assert "score-4" in assembled.context_blocks[2]


class TestConflictAlert:
    def test_conflict_alert_injected_when_conflict_group_present(self) -> None:
        results = [
            make_result(0.8, 0, doc_id="PROC-042-v1", version="1.0", version_date="2023-03-03"),
            make_result(0.7, 1, doc_id="PROC-042-v2", version="2.0", version_date="2023-11-10"),
        ]
        conflict = ConflictGroup(
            doc_id="PROC-042",
            versions=[
                ConflictVersion("1.0", "2023-03-03", results[0].chunk.chunk_id),
                ConflictVersion("2.0", "2023-11-10", results[1].chunk.chunk_id),
            ],
        )
        bundle = RetrievalBundle(results=results, conflicts=[conflict])

        assembled = make_assembler().assemble("multiplicador Sul", bundle, token_budget=10_000)

        alert = assembled.context_blocks[0]
        assert "DIVERGÊNCIA" in alert
        assert "PROC-042" in alert
        assert "1.0" in alert and "2.0" in alert

    def test_no_alert_when_no_conflict(self) -> None:
        bundle = RetrievalBundle(results=[make_result(0.9, 0)])

        assembled = make_assembler().assemble("pergunta", bundle, token_budget=10_000)

        assert all("DIVERGÊNCIA" not in block for block in assembled.context_blocks)


class TestAbstention:
    def test_abstention_directive_injected_when_below_threshold(self) -> None:
        bundle = RetrievalBundle(results=[], below_threshold=True)

        assembled = make_assembler().assemble("pergunta fora da base", bundle, token_budget=10_000)

        assert ABSTENTION_DIRECTIVE in assembled.context_blocks
        assert assembled.dropped_chunks == []


class TestCitation:
    def test_each_chunk_block_carries_document_and_section(self) -> None:
        bundle = RetrievalBundle(results=[make_result(0.9, 0, doc_title="POL-001 — Política",
                                                      section="3.2")])

        assembled = make_assembler().assemble("pergunta", bundle, token_budget=10_000)

        block = assembled.context_blocks[0]
        assert "POL-001 — Política" in block
        assert "seção 3.2" in block

    def test_unofficial_source_is_flagged_in_block(self) -> None:
        bundle = RetrievalBundle(results=[make_result(0.9, 0, is_official=False)])

        assembled = make_assembler().assemble("pergunta", bundle, token_budget=10_000)

        assert "não validada" in assembled.context_blocks[0]
