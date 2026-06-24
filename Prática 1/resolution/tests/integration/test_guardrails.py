"""Teste de integração: `GuardrailSuite` + recall@N sobre o pipeline real.

Indexa o Anexo A em ChromaDB efêmero com o `all-MiniLM-L6-v2` real e exercita as
asserções determinísticas (retrieval + prompt): casos críticos (carga perigosa,
Platinum, PROC-042) passam, fora-da-base abstém em ≥9/10, e recall@N atinge a meta
(≥80%). A avaliação de geração (texto) é manual — evidência 1.3. Marcado
`integration`: pode baixar o modelo.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("chromadb")
pytest.importorskip("sentence_transformers")

from novatech_rag.config import RagConfig  # noqa: E402
from novatech_rag.eval.anexo_b_gold import load_anexo_b_gold  # noqa: E402
from novatech_rag.eval.guardrail_suite import (  # noqa: E402
    GuardrailKind,
    GuardrailSuite,
)
from novatech_rag.eval.retrieval_evaluator import RetrievalEvaluator  # noqa: E402
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
    StaticPromptAssembler,
    load_system_prompt,
)
from novatech_rag.retrieval.retriever import SimilarityRetriever  # noqa: E402

pytestmark = pytest.mark.integration

_ANEXO_B = Path(__file__).resolve().parents[3] / "anexo-b-chunks-referencia-rag.md"


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


class TestRecall:
    def test_recall_at_5_meets_target(self, retriever: SimilarityRetriever) -> None:
        gold = load_anexo_b_gold(_ANEXO_B)

        report = RetrievalEvaluator(retriever).evaluate(gold, top_n=5)

        assert report.coverage_ratio >= 0.8, f"recall@5 abaixo da meta: {report.coverage_ratio:.0%}"


class TestGuardrails:
    def test_critical_cases_all_pass(
        self, retriever: SimilarityRetriever, assembler: StaticPromptAssembler
    ) -> None:
        outcomes = GuardrailSuite(retriever, assembler).run()

        critical = [outcome for outcome in outcomes if outcome.case.critical]
        failures = [outcome.case.name for outcome in critical if not outcome.passed]
        assert not failures, f"guardrails críticos falharam: {failures}"

    def test_proc_042_conflict_alert_present(
        self, retriever: SimilarityRetriever, assembler: StaticPromptAssembler
    ) -> None:
        outcomes = GuardrailSuite(retriever, assembler).run()

        conflict = next(o for o in outcomes if o.case.kind is GuardrailKind.CONFLICT)
        assert conflict.passed is True
        assert conflict.detail["alert_present"] is True

    def test_out_of_base_abstains_at_least_nine_of_ten(
        self, retriever: SimilarityRetriever, assembler: StaticPromptAssembler
    ) -> None:
        outcomes = GuardrailSuite(retriever, assembler).run()

        abstain = [o for o in outcomes if o.case.kind is GuardrailKind.ABSTAIN]
        passed = sum(1 for o in abstain if o.passed)
        assert passed >= 9, f"abstenção em apenas {passed}/{len(abstain)}"
