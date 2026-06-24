"""Teste de integração: ingestão → retrieval ponta a ponta sobre o Anexo A.

Usa o `EmbeddingProvider` real (`all-MiniLM-L6-v2`) e um ChromaDB efêmero sob
`tmp_path`. Marcado `integration`: pode baixar o modelo no primeiro uso
(pytest-testing). Valida os critérios de sucesso da Tarefa 3.0: os 5 documentos
são recuperáveis por busca semântica, o FAQ entra como `is_official=False` e
reindexar não duplica (RF-01/RF-10).
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("chromadb")
pytest.importorskip("sentence_transformers")

from novatech_rag.config import RagConfig  # noqa: E402
from novatech_rag.ingestion.chunker import SectionAwareChunker  # noqa: E402
from novatech_rag.ingestion.embeddings import (  # noqa: E402
    SentenceTransformerEmbeddingProvider,
)
from novatech_rag.ingestion.loader import DocumentLoader  # noqa: E402
from novatech_rag.ingestion.pipeline import (  # noqa: E402
    IngestionComponents,
    ingest_documents,
)
from novatech_rag.ingestion.vector_store import ChromaVectorStore  # noqa: E402

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def shared_embeddings() -> SentenceTransformerEmbeddingProvider:
    # Carregado uma vez por módulo: o download/inicialização do modelo é caro.
    return SentenceTransformerEmbeddingProvider()


@pytest.fixture
def indexed_store(
    tmp_path: Path, corpus_dir: Path, anexo_a_descriptors, shared_embeddings
) -> ChromaVectorStore:
    config = RagConfig(persist_directory=tmp_path / "chroma", collection_name="anexo_a")
    store = ChromaVectorStore(shared_embeddings, config)
    components = IngestionComponents(DocumentLoader(), SectionAwareChunker(config), store)
    report = ingest_documents(anexo_a_descriptors, components, config=config)
    assert report.document_count == 5
    assert report.chunk_count > 5
    return store


def _retrieve(store: ChromaVectorStore, embeddings, question: str, top_k: int = 5):
    return store.query(embeddings.embed([question])[0], top_k=top_k)


class TestSemanticRetrieval:
    def test_devolution_question_retrieves_pol_001(
        self, indexed_store: ChromaVectorStore, shared_embeddings
    ) -> None:
        results = _retrieve(indexed_store, shared_embeddings, "prazo para devolver mercadoria")

        doc_ids = {r.chunk.metadata.doc_id for r in results}
        assert "POL-001" in doc_ids

    def test_sla_tier_question_retrieves_sla_2024(
        self, indexed_store: ChromaVectorStore, shared_embeddings
    ) -> None:
        results = _retrieve(indexed_store, shared_embeddings, "quais são os tiers de cliente")

        doc_ids = {r.chunk.metadata.doc_id for r in results}
        assert "SLA-2024" in doc_ids

    def test_freight_question_retrieves_both_proc_042_versions(
        self, indexed_store: ChromaVectorStore, shared_embeddings
    ) -> None:
        results = _retrieve(
            indexed_store, shared_embeddings, "como calcular frete especial por região", top_k=10
        )

        doc_ids = {r.chunk.metadata.doc_id for r in results}
        assert "PROC-042-v1" in doc_ids
        assert "PROC-042-v2" in doc_ids


class TestProvenance:
    def test_faq_is_indexed_as_unofficial(
        self, indexed_store: ChromaVectorStore, shared_embeddings
    ) -> None:
        results = _retrieve(
            indexed_store, shared_embeddings, "cliente diz que é Platinum", top_k=10
        )

        faq = [r for r in results if r.chunk.metadata.doc_id == "FAQ-atendimento"]
        assert faq, "FAQ não recuperado para pergunta sobre Platinum"
        assert all(r.chunk.metadata.is_official is False for r in faq)


class TestIdempotentReindex:
    def test_reingesting_keeps_chunk_count_stable(
        self,
        indexed_store: ChromaVectorStore,
        anexo_a_descriptors,
        shared_embeddings,
    ) -> None:
        count_before = indexed_store.count()
        config = RagConfig()
        components = IngestionComponents(
            DocumentLoader(), SectionAwareChunker(config), indexed_store
        )

        ingest_documents(anexo_a_descriptors, components, config=config)

        assert indexed_store.count() == count_before
