"""Teste de integração: pipeline ingestão→retrieval→prompt sobre o Anexo A.

Usa o `EmbeddingProvider` real (`all-MiniLM-L6-v2`) e um ChromaDB efêmero sob
`tmp_path`, fechando o pipeline da PoC (Tarefa 5.0). Valida os critérios de
sucesso: o prompt montado para PROC-042 contém as duas versões + alerta de
divergência (G-07); a pergunta fora da base produz prompt com instrução de
abstenção (G-03). Marcado `integration`: pode baixar o modelo.
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
from novatech_rag.prompt.assembler import (  # noqa: E402
    ABSTENTION_DIRECTIVE,
    StaticPromptAssembler,
    load_system_prompt,
)
from novatech_rag.retrieval.retriever import SimilarityRetriever  # noqa: E402

pytestmark = pytest.mark.integration

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


@pytest.fixture
def assembler() -> StaticPromptAssembler:
    return StaticPromptAssembler(load_system_prompt("v2"))


class TestConflictPrompt:
    def test_proc_042_prompt_carries_both_versions_and_alert(
        self, retriever: SimilarityRetriever, assembler: StaticPromptAssembler
    ) -> None:
        question = "como calcular o multiplicador regional Sul do frete especial"
        bundle = retriever.retrieve(question, top_k=10, min_score=0.0)

        assembled = assembler.assemble(question, bundle, token_budget=8_000)

        joined = "\n".join(assembled.context_blocks)
        assert "DIVERGÊNCIA" in joined, "alerta de divergência ausente no prompt"
        assert "PROC-042" in joined
        doc_ids = {result.chunk.metadata.doc_id for result in bundle.results}
        assert {"PROC-042-v1", "PROC-042-v2"} <= doc_ids


class TestAbstentionPrompt:
    def test_out_of_base_question_yields_abstention_instruction(
        self, retriever: SimilarityRetriever, assembler: StaticPromptAssembler
    ) -> None:
        question = "qual a capital da França"
        bundle = retriever.retrieve(question, top_k=5, min_score=_ABSTENTION_MIN_SCORE)

        assembled = assembler.assemble(question, bundle, token_budget=8_000)

        assert bundle.below_threshold is True
        assert ABSTENTION_DIRECTIVE in assembled.context_blocks
        assert assembled.dropped_chunks == []
