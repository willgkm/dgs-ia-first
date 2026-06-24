"""Testes unitários do `ConflictDetector` (RF-08 / G-07).

Versões divergentes do mesmo documento-base → `ConflictGroup` com ambas; um único
documento, ou documentos sem base comum, não geram conflito. Constrói
`RetrievalResult` direto — a detecção opera só sobre metadados, sem ChromaDB.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from novatech_rag.models import (
    ChunkMetadata,
    DocumentSource,
    RetrievalResult,
    build_chunk,
)
from novatech_rag.retrieval.conflict_detector import ConflictDetector, conflict_key


def make_result(
    doc_id: str,
    version: str,
    version_date: str,
    rank: int,
    *,
    section: str = "2",
    text: str = "conteúdo do chunk",
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
    return RetrievalResult(chunk=chunk, score=1.0 - rank * 0.1, rank=rank)


class TestConflictKey:
    @pytest.mark.parametrize(
        ("doc_id", "expected"),
        [
            ("PROC-042-v1", "PROC-042"),
            ("PROC-042-v2", "PROC-042"),
            ("PROC-042-V3", "PROC-042"),
            ("POL-001", "POL-001"),
            ("SLA-2024", "SLA-2024"),
            ("FAQ-atendimento", "FAQ-atendimento"),
        ],
    )
    def test_strips_only_version_suffix(self, doc_id: str, expected: str) -> None:
        assert conflict_key(doc_id) == expected


class TestDetect:
    def test_proc_042_v1_and_v2_yield_single_group_with_both_versions(self) -> None:
        results = [
            make_result("PROC-042-v1", "1.0", "2023-03-03", rank=0),
            make_result("PROC-042-v2", "2.0", "2023-11-10", rank=1),
        ]

        groups = ConflictDetector().detect(results)

        assert len(groups) == 1
        group = groups[0]
        assert group.doc_id == "PROC-042"
        assert [(v.version, v.version_date) for v in group.versions] == [
            ("1.0", "2023-03-03"),
            ("2.0", "2023-11-10"),
        ]

    def test_versions_are_ordered_chronologically(self) -> None:
        results = [
            make_result("PROC-042-v2", "2.0", "2023-11-10", rank=0),
            make_result("PROC-042-v1", "1.0", "2023-03-03", rank=1),
        ]

        group = ConflictDetector().detect(results)[0]

        assert [v.version for v in group.versions] == ["1.0", "2.0"]

    def test_single_version_yields_no_conflict(self) -> None:
        results = [make_result("PROC-042-v1", "1.0", "2023-03-03", rank=0)]

        assert ConflictDetector().detect(results) == []

    def test_repeated_chunks_of_same_version_yield_no_conflict(self) -> None:
        results = [
            make_result("PROC-042-v1", "1.0", "2023-03-03", rank=0, section="1"),
            make_result("PROC-042-v1", "1.0", "2023-03-03", rank=1, section="2"),
        ]

        assert ConflictDetector().detect(results) == []

    def test_distinct_documents_without_common_base_yield_no_conflict(self) -> None:
        results = [
            make_result("POL-001", "3.1", "2024-01-15", rank=0),
            make_result("SLA-2024", "2024.1", "2024-01-02", rank=1),
        ]

        assert ConflictDetector().detect(results) == []

    def test_empty_results_yield_no_conflict(self) -> None:
        assert ConflictDetector().detect([]) == []

    def test_representative_chunk_id_is_the_best_ranked_per_version(self) -> None:
        best = make_result("PROC-042-v1", "1.0", "2023-03-03", rank=0, section="1")
        worse = make_result("PROC-042-v1", "1.0", "2023-03-03", rank=2, section="9")
        results = [best, worse, make_result("PROC-042-v2", "2.0", "2023-11-10", rank=1)]

        group = ConflictDetector().detect(results)[0]

        v1 = next(v for v in group.versions if v.version == "1.0")
        assert v1.chunk_id == best.chunk.chunk_id
