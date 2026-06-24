"""Testes do `ChromaVectorStore` (RF-10).

Idempotência do `upsert` por `chunk_id`, ida-e-volta dos metadados e filtro
`where`. Usa um ChromaDB efêmero sob `tmp_path` e o `EmbeddingProvider` fake do
conftest (determinístico, sem rede). `chromadb` é requisito; se ausente, skip.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from novatech_rag.config import RagConfig
from novatech_rag.ingestion.vector_store import ChromaVectorStore
from novatech_rag.models import Chunk, ChunkMetadata, DocumentSource, build_chunk

pytest.importorskip("chromadb")


def make_chunk(
    doc_id: str,
    section: str,
    ordinal: int,
    text: str,
    *,
    version: str = "1.0",
    is_official: bool = True,
    source: DocumentSource = DocumentSource.SHAREPOINT,
) -> Chunk:
    metadata = ChunkMetadata(
        doc_id=doc_id,
        doc_title=f"Título {doc_id}",
        version=version,
        version_date="2024-01-01",
        section=section,
        source=source,
        is_official=is_official,
        ingested_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    return build_chunk(text, metadata, ordinal)


@pytest.fixture
def store(tmp_path: Path, fake_embedding_provider) -> ChromaVectorStore:
    config = RagConfig(persist_directory=tmp_path / "chroma", collection_name="test")
    return ChromaVectorStore(fake_embedding_provider, config)


@pytest.fixture
def embed(fake_embedding_provider):
    """Embeda a pergunta com o mesmo provider determinístico injetado no store."""

    def _embed(text: str) -> list[float]:
        return fake_embedding_provider.embed([text])[0]

    return _embed


class TestUpsertIdempotency:
    def test_reindexing_same_chunk_id_replaces_not_duplicates(
        self, store: ChromaVectorStore, embed
    ) -> None:
        original = make_chunk("POL-001", "3.1", 0, "prazo de devolução de 7 dias úteis")
        store.upsert([original])
        revised = make_chunk("POL-001", "3.1", 0, "prazo de devolução revisado para 10 dias")

        store.upsert([revised])

        assert store.count() == 1
        results = store.query(embed("prazo de devolução"), top_k=1)
        assert results[0].chunk.text == "prazo de devolução revisado para 10 dias"

    def test_distinct_chunk_ids_coexist(self, store: ChromaVectorStore) -> None:
        v1 = make_chunk("PROC-042-v1", "2", 0, "fator de peso 1.2", version="1.0")
        v2 = make_chunk("PROC-042-v2", "2", 0, "fator de peso 1.15", version="2.0")

        store.upsert([v1, v2])

        assert store.count() == 2


class TestMetadataRoundTrip:
    def test_query_reconstructs_metadata(self, store: ChromaVectorStore, embed) -> None:
        chunk = make_chunk(
            "FAQ-atendimento", "Item 15", 0, "tier Platinum não existe",
            is_official=False, source=DocumentSource.FAQ,
        )
        store.upsert([chunk])

        result = store.query(embed("tier Platinum"), top_k=1)[0]

        assert result.chunk.chunk_id == chunk.chunk_id
        assert result.chunk.metadata.is_official is False
        assert result.chunk.metadata.source is DocumentSource.FAQ
        assert result.chunk.metadata.doc_id == "FAQ-atendimento"
        assert result.rank == 0

    def test_score_is_one_minus_cosine_distance(
        self, store: ChromaVectorStore, embed
    ) -> None:
        chunk = make_chunk("POL-001", "1", 0, "objetivo da política de devolução")
        store.upsert([chunk])

        result = store.query(embed("objetivo da política de devolução"), top_k=1)[0]

        assert result.score == pytest.approx(1.0, abs=1e-6)  # vetor idêntico → cosseno 1


class TestWhereFilter:
    def test_filter_restricts_to_official_documents(
        self, store: ChromaVectorStore, embed
    ) -> None:
        official = make_chunk("POL-001", "1", 0, "carga perigosa não pode ser devolvida")
        faq = make_chunk(
            "FAQ-atendimento", "Item 3", 0, "carga perigosa ligue para o ramal 4500",
            is_official=False, source=DocumentSource.FAQ,
        )
        store.upsert([official, faq])

        results = store.query(embed("carga perigosa"), top_k=5, where={"is_official": True})

        assert results
        assert all(r.chunk.metadata.is_official for r in results)
