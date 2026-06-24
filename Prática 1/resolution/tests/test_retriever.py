"""Testes unitários do `SimilarityRetriever` (RF-03 / RF-07 / G-03).

Threshold/abstenção (`below_threshold`), repasse do filtro `where` e detecção de
conflito são exercitados com um `VectorStore` stub (resultados e scores
controlados) e o `EmbeddingProvider` determinístico do conftest — sem ChromaDB
nem modelo real (pytest-testing: unidade determinística).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone

from novatech_rag.models import (
    Chunk,
    ChunkMetadata,
    DocumentSource,
    RetrievalResult,
    build_chunk,
)
from novatech_rag.retrieval.retriever import SimilarityRetriever


def make_result(
    score: float,
    rank: int,
    *,
    doc_id: str = "POL-001",
    version: str = "3.1",
    version_date: str = "2024-01-15",
    section: str = "3.2",
    text: str = "carga perigosa não pode ser devolvida",
) -> RetrievalResult:
    metadata = ChunkMetadata(
        doc_id=doc_id,
        doc_title=f"Título {doc_id}",
        version=version,
        version_date=version_date,
        section=section,
        source=DocumentSource.SHAREPOINT,
        is_official=True,
        ingested_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    chunk = build_chunk(text, metadata, rank)
    return RetrievalResult(chunk=chunk, score=score, rank=rank)


class StubVectorStore:
    """`VectorStore` falso: devolve resultados pré-definidos e registra a última
    consulta para verificar o repasse de `top_k`/`where`."""

    def __init__(self, results: Sequence[RetrievalResult]) -> None:
        self._results = list(results)
        self.last_where: dict | None = None
        self.last_top_k: int | None = None

    def upsert(self, chunks: Sequence[Chunk]) -> None:  # pragma: no cover - não usado
        raise NotImplementedError

    def query(
        self, embedding: list[float], top_k: int, where: dict | None = None
    ) -> list[RetrievalResult]:
        self.last_where = where
        self.last_top_k = top_k
        return self._results[:top_k]


def make_retriever(
    results: Sequence[RetrievalResult], fake_embedding_provider
) -> tuple[SimilarityRetriever, StubVectorStore]:
    store = StubVectorStore(results)
    return SimilarityRetriever(fake_embedding_provider, store), store


class TestThresholdAbstention:
    def test_below_threshold_when_all_scores_under_min_score(self, fake_embedding_provider) -> None:
        retriever, _ = make_retriever(
            [make_result(0.30, 0), make_result(0.20, 1)], fake_embedding_provider
        )

        bundle = retriever.retrieve("pergunta sem cobertura", top_k=5, min_score=0.70)

        assert bundle.below_threshold is True
        assert bundle.results == []
        assert bundle.conflicts == []

    def test_keeps_only_results_at_or_above_min_score(self, fake_embedding_provider) -> None:
        retriever, _ = make_retriever(
            [make_result(0.80, 0), make_result(0.50, 1), make_result(0.40, 2)],
            fake_embedding_provider,
        )

        bundle = retriever.retrieve("pergunta", top_k=5, min_score=0.50)

        assert bundle.below_threshold is False
        assert [result.score for result in bundle.results] == [0.80, 0.50]

    def test_score_equal_to_min_score_is_kept(self, fake_embedding_provider) -> None:
        retriever, _ = make_retriever([make_result(0.70, 0)], fake_embedding_provider)

        bundle = retriever.retrieve("pergunta", top_k=5, min_score=0.70)

        assert bundle.below_threshold is False
        assert len(bundle.results) == 1


class TestWhereFilter:
    def test_where_filter_is_passed_through_to_the_store(self, fake_embedding_provider) -> None:
        retriever, store = make_retriever([make_result(0.90, 0)], fake_embedding_provider)
        where = {"is_official": True}

        retriever.retrieve("carga perigosa", top_k=3, min_score=0.0, where=where)

        assert store.last_where == where
        assert store.last_top_k == 3

    def test_no_where_filter_passes_none(self, fake_embedding_provider) -> None:
        retriever, store = make_retriever([make_result(0.90, 0)], fake_embedding_provider)

        retriever.retrieve("carga perigosa", top_k=3, min_score=0.0)

        assert store.last_where is None


class TestConflictDetectionWiring:
    def test_conflicting_versions_above_threshold_produce_conflict_group(
        self, fake_embedding_provider
    ) -> None:
        results = [
            make_result(0.80, 0, doc_id="PROC-042-v1", version="1.0", version_date="2023-03-03"),
            make_result(0.75, 1, doc_id="PROC-042-v2", version="2.0", version_date="2023-11-10"),
        ]
        retriever, _ = make_retriever(results, fake_embedding_provider)

        bundle = retriever.retrieve("frete região Sul", top_k=5, min_score=0.50)

        assert len(bundle.conflicts) == 1
        assert bundle.conflicts[0].doc_id == "PROC-042"
        assert {v.version for v in bundle.conflicts[0].versions} == {"1.0", "2.0"}

    def test_conflict_dropped_when_one_version_is_below_threshold(
        self, fake_embedding_provider
    ) -> None:
        results = [
            make_result(0.80, 0, doc_id="PROC-042-v1", version="1.0", version_date="2023-03-03"),
            make_result(0.40, 1, doc_id="PROC-042-v2", version="2.0", version_date="2023-11-10"),
        ]
        retriever, _ = make_retriever(results, fake_embedding_provider)

        bundle = retriever.retrieve("frete região Sul", top_k=5, min_score=0.50)

        assert bundle.conflicts == []
        assert len(bundle.results) == 1
