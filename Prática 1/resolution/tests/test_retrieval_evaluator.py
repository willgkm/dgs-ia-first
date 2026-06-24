"""Testes unitários do `RetrievalEvaluator` e do parsing do gabarito do Anexo B.

Recall@N é determinístico: um `Retriever` stub devolve doc_ids controlados, então
acerto/erro/parcial são exatos, sem ChromaDB nem modelo (pytest-testing, Etapa 2/4).
O parsing do gabarito roda sobre o arquivo real do Anexo B.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from novatech_rag.eval.anexo_b_gold import (
    GoldEntry,
    chunk_label_to_doc_id,
    load_anexo_b_gold,
)
from novatech_rag.eval.retrieval_evaluator import RetrievalEvaluator
from novatech_rag.models import (
    ChunkMetadata,
    DocumentSource,
    RetrievalBundle,
    RetrievalResult,
    build_chunk,
)

_ANEXO_B = Path(__file__).resolve().parents[2] / "anexo-b-chunks-referencia-rag.md"


def make_result(doc_id: str, rank: int) -> RetrievalResult:
    metadata = ChunkMetadata(
        doc_id=doc_id,
        doc_title=f"Título {doc_id}",
        version="1.0",
        version_date="2024-01-01",
        section="1",
        source=DocumentSource.SHAREPOINT,
        is_official=True,
        ingested_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    chunk = build_chunk(f"texto {doc_id}", metadata, rank)
    return RetrievalResult(chunk=chunk, score=0.9 - rank * 0.1, rank=rank)


class StubRetriever:
    """`Retriever` falso: mapeia pergunta → resultados pré-definidos (por doc_id)."""

    def __init__(self, by_question: dict[str, list[str]]) -> None:
        self._by_question = by_question

    def retrieve(
        self, question: str, top_k: int, min_score: float, where: dict | None = None
    ) -> RetrievalBundle:
        doc_ids = self._by_question.get(question, [])[:top_k]
        results = [make_result(doc_id, rank) for rank, doc_id in enumerate(doc_ids)]
        return RetrievalBundle(results=results, below_threshold=not results)


class TestChunkLabelMapping:
    def test_proc_042_v2_label_maps_before_v1(self) -> None:
        assert chunk_label_to_doc_id("PROC-042v2-B") == "PROC-042-v2"

    def test_proc_042_v1_label_maps_to_v1(self) -> None:
        assert chunk_label_to_doc_id("PROC-042-B") == "PROC-042-v1"

    def test_faq_label_collapses_to_single_doc(self) -> None:
        assert chunk_label_to_doc_id("FAQ-15") == "FAQ-atendimento"


class TestGoldParsing:
    def test_loads_coverage_entries_from_anexo_b(self) -> None:
        entries = load_anexo_b_gold(_ANEXO_B)

        assert len(entries) >= 9
        by_question = {entry.question: entry for entry in entries}
        carga = next(e for q, e in by_question.items() if "carga perigosa" in q.lower()
                     and "devolver" in q.lower())
        assert "POL-001" in carga.expected_doc_ids

    def test_out_of_base_question_marked_as_abstain(self) -> None:
        entries = load_anexo_b_gold(_ANEXO_B)

        salvador = next(e for e in entries if "Salvador" in e.question)
        assert salvador.should_abstain is True
        assert salvador.expected_doc_ids == frozenset()


class TestRecall:
    def test_full_coverage_yields_recall_one_and_covered(self) -> None:
        gold = [GoldEntry("q1", frozenset({"POL-001"}), frozenset(), False)]
        retriever = StubRetriever({"q1": ["FAQ-atendimento", "POL-001"]})

        report = RetrievalEvaluator(retriever).evaluate(gold, top_n=5)

        assert report.results[0].recall == 1.0
        assert report.results[0].covered is True
        assert report.coverage_ratio == 1.0

    def test_partial_coverage_yields_fractional_recall_not_covered(self) -> None:
        gold = [GoldEntry("q1", frozenset({"POL-001", "PROC-042-v2"}), frozenset(), False)]
        retriever = StubRetriever({"q1": ["POL-001", "FAQ-atendimento"]})

        report = RetrievalEvaluator(retriever).evaluate(gold, top_n=5)

        assert report.results[0].recall == 0.5
        assert report.results[0].covered is False
        assert report.coverage_ratio == 0.0

    def test_missing_doc_beyond_top_n_is_not_counted(self) -> None:
        gold = [GoldEntry("q1", frozenset({"PROC-042-v2"}), frozenset(), False)]
        retriever = StubRetriever({"q1": ["POL-001", "FAQ-atendimento", "PROC-042-v2"]})

        report = RetrievalEvaluator(retriever).evaluate(gold, top_n=2)

        assert report.results[0].covered is False

    def test_abstain_entries_excluded_from_recall(self) -> None:
        gold = [
            GoldEntry("q1", frozenset({"POL-001"}), frozenset(), False),
            GoldEntry("q2", frozenset(), frozenset(), True),
        ]
        retriever = StubRetriever({"q1": ["POL-001"]})

        report = RetrievalEvaluator(retriever).evaluate(gold, top_n=5)

        assert report.question_count == 1
