"""Teste de integração: retrieval ponta a ponta sobre o Anexo A.

Usa o `EmbeddingProvider` real (`all-MiniLM-L6-v2`) e um ChromaDB efêmero sob
`tmp_path`. Valida os critérios de sucesso da Tarefa 4.0: pergunta com cobertura
recupera o documento certo sem abster; pergunta fora da base marca abstenção;
pergunta sobre frete recupera ambas as versões do PROC-042 e o `ConflictDetector`
emite o grupo de divergência (G-07). Marcado `integration`: pode baixar o modelo.
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
from novatech_rag.retrieval.retriever import SimilarityRetriever  # noqa: E402

pytestmark = pytest.mark.integration

# Threshold alto: nenhuma pergunta fora da base produz chunk quase idêntico, então
# a abstenção é validada sem depender da calibração absoluta do score (o modelo é
# primariamente anglófono — risco documentado no techspec). O retrieval com
# cobertura usa min_score=0.0 (validação fina de recall@N fica na Tarefa 6.0).
_ABSTENTION_MIN_SCORE = 0.90


@pytest.fixture(scope="module")
def shared_embeddings() -> SentenceTransformerEmbeddingProvider:
    return SentenceTransformerEmbeddingProvider()


@pytest.fixture
def retriever(tmp_path: Path, anexo_a_descriptors, shared_embeddings) -> SimilarityRetriever:
    config = RagConfig(persist_directory=tmp_path / "chroma", collection_name="anexo_a")
    store = ChromaVectorStore(shared_embeddings, config)
    components = IngestionComponents(DocumentLoader(), SectionAwareChunker(config), store)
    report = ingest_documents(anexo_a_descriptors, components, config=config)
    assert report.document_count == 5
    return SimilarityRetriever(shared_embeddings, store)


class TestCoverage:
    def test_covered_question_retrieves_pol_001_without_abstaining(
        self, retriever: SimilarityRetriever
    ) -> None:
        bundle = retriever.retrieve("prazo para devolver mercadoria", top_k=5, min_score=0.0)

        assert bundle.below_threshold is False
        assert "POL-001" in {r.chunk.metadata.doc_id for r in bundle.results}


class TestAbstention:
    def test_out_of_base_question_marks_below_threshold(
        self, retriever: SimilarityRetriever
    ) -> None:
        bundle = retriever.retrieve(
            "qual a capital da França", top_k=5, min_score=_ABSTENTION_MIN_SCORE
        )

        assert bundle.below_threshold is True
        assert bundle.results == []


class TestConflict:
    def test_freight_question_detects_both_proc_042_versions(
        self, retriever: SimilarityRetriever
    ) -> None:
        bundle = retriever.retrieve(
            "como calcular o multiplicador regional Sul do frete especial",
            top_k=10,
            min_score=0.0,
        )

        groups = {group.doc_id: group for group in bundle.conflicts}
        assert "PROC-042" in groups, "conflito PROC-042 não detectado"
        assert {v.version for v in groups["PROC-042"].versions} == {"1.0", "2.0"}
