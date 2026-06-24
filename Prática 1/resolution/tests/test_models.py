"""Testes unitários dos modelos de domínio e do `chunk_id` determinístico."""

from __future__ import annotations

import dataclasses
from datetime import datetime

import pytest

from novatech_rag.models import (
    AssembledPrompt,
    ChunkMetadata,
    ConflictGroup,
    ConflictVersion,
    DocumentSource,
    RetrievalBundle,
    RetrievalResult,
    build_chunk,
    compute_chunk_id,
)


def make_metadata(
    *,
    doc_id: str = "PROC-042",
    section: str = "Frete especial",
    version: str = "v2",
    is_official: bool = True,
) -> ChunkMetadata:
    return ChunkMetadata(
        doc_id=doc_id,
        doc_title="Procedimento de frete especial",
        version=version,
        version_date="2024-05-10",
        section=section,
        source=DocumentSource.SHAREPOINT,
        is_official=is_official,
        ingested_at=datetime(2024, 6, 1, 12, 0, 0),
    )


class TestComputeChunkId:
    def test_same_inputs_yield_same_id(self) -> None:
        first = compute_chunk_id("PROC-042", "Frete especial", 3)
        second = compute_chunk_id("PROC-042", "Frete especial", 3)
        assert first == second

    @pytest.mark.parametrize(
        "doc_id, section, ordinal",
        [
            ("PROC-042", "Frete especial", 4),
            ("PROC-042", "Outra seção", 3),
            ("POL-001", "Frete especial", 3),
        ],
    )
    def test_different_inputs_yield_different_ids(
        self, doc_id: str, section: str, ordinal: int
    ) -> None:
        baseline = compute_chunk_id("PROC-042", "Frete especial", 3)
        assert compute_chunk_id(doc_id, section, ordinal) != baseline

    def test_consecutive_ordinals_are_distinct(self) -> None:
        ids = {compute_chunk_id("PROC-042", "Frete especial", n) for n in range(10)}
        assert len(ids) == 10

    def test_id_is_hex_sha256(self) -> None:
        chunk_id = compute_chunk_id("PROC-042", "Frete especial", 0)
        assert len(chunk_id) == 64
        assert all(ch in "0123456789abcdef" for ch in chunk_id)


class TestBuildChunk:
    def test_build_chunk_derives_id_from_metadata_and_ordinal(self) -> None:
        metadata = make_metadata()
        chunk = build_chunk("texto do chunk", metadata, ordinal=2)
        expected = compute_chunk_id(metadata.doc_id, metadata.section, 2)
        assert chunk.chunk_id == expected
        assert chunk.text == "texto do chunk"
        assert chunk.metadata is metadata

    def test_same_position_reindexes_to_same_id(self) -> None:
        # base do upsert idempotente (RF-10): reindexar substitui, não duplica.
        metadata = make_metadata()
        first = build_chunk("v1 do texto", metadata, ordinal=0)
        second = build_chunk("texto editado", metadata, ordinal=0)
        assert first.chunk_id == second.chunk_id


class TestDomainDataclasses:
    def test_chunk_is_frozen(self) -> None:
        chunk = build_chunk("t", make_metadata(), ordinal=0)
        with pytest.raises(dataclasses.FrozenInstanceError):
            chunk.text = "outro"  # type: ignore[misc]

    def test_document_source_values(self) -> None:
        assert {s.value for s in DocumentSource} == {
            "sharepoint",
            "confluence",
            "rede",
            "faq",
        }

    def test_faq_metadata_is_not_official(self) -> None:
        faq = ChunkMetadata(
            doc_id="FAQ",
            doc_title="FAQ de atendimento",
            version="1",
            version_date="2024-01-01",
            section="Devoluções",
            source=DocumentSource.FAQ,
            is_official=False,
            ingested_at=datetime(2024, 6, 1),
        )
        assert faq.is_official is False
        assert faq.source is DocumentSource.FAQ

    def test_conflict_group_holds_multiple_versions(self) -> None:
        group = ConflictGroup(
            doc_id="PROC-042",
            versions=[
                ConflictVersion("v1", "2023-01-01", compute_chunk_id("PROC-042", "s", 0)),
                ConflictVersion("v2", "2024-05-10", compute_chunk_id("PROC-042", "s", 1)),
            ],
        )
        assert len(group.versions) == 2
        assert {v.version for v in group.versions} == {"v1", "v2"}

    def test_retrieval_bundle_defaults(self) -> None:
        result = RetrievalResult(
            chunk=build_chunk("t", make_metadata(), ordinal=0), score=0.9, rank=1
        )
        bundle = RetrievalBundle(results=[result])
        assert bundle.conflicts == []
        assert bundle.below_threshold is False

    def test_assembled_prompt_defaults(self) -> None:
        prompt = AssembledPrompt(
            system="prompt do sistema",
            context_blocks=["bloco 1"],
            question="Qual o prazo de devolução?",
            estimated_tokens=42,
        )
        assert prompt.dropped_chunks == []
