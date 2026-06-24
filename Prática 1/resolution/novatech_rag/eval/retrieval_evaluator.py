"""`RetrievalEvaluator`: mede recall@N contra o gabarito do Anexo B (RF-03).

Para cada pergunta com cobertura, recupera o top-N e verifica se os documentos
esperados aparecem. Reporta o recall por pergunta e dois agregados: o recall médio
e a taxa de cobertura (fração de perguntas com **todos** os documentos esperados no
top-N) — esta última é a métrica de homologação (meta ≥80%). As perguntas de
abstenção (sem cobertura) ficam fora do recall; são avaliadas pela `GuardrailSuite`.

`evaluate` é puro (CQS): consulta o retriever e devolve o relatório, sem mutar nada.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..interfaces import Retriever
from ..models import RetrievalResult
from .anexo_b_gold import GoldEntry

__all__ = ["QuestionRecall", "RecallReport", "RetrievalEvaluator"]


@dataclass(frozen=True)
class QuestionRecall:
    """Recall de uma pergunta: documentos esperados vs recuperados no top-N."""

    question: str
    expected_doc_ids: list[str]
    retrieved_doc_ids: list[str]
    found_doc_ids: list[str]
    recall: float
    covered: bool


@dataclass(frozen=True)
class RecallReport:
    """Agregado do recall@N sobre as perguntas com cobertura."""

    top_n: int
    question_count: int
    mean_recall: float
    coverage_ratio: float
    results: list[QuestionRecall]


class RetrievalEvaluator:
    """Avalia o recall@N de um `Retriever` contra o gabarito do Anexo B."""

    def __init__(self, retriever: Retriever) -> None:
        self._retriever = retriever

    def evaluate(self, gold_entries: Sequence[GoldEntry], top_n: int) -> RecallReport:
        graded = [
            self._grade(entry, top_n)
            for entry in gold_entries
            if not entry.should_abstain and entry.expected_doc_ids
        ]
        count = len(graded)
        mean_recall = sum(result.recall for result in graded) / count if count else 0.0
        coverage = sum(1 for result in graded if result.covered) / count if count else 0.0
        return RecallReport(
            top_n=top_n,
            question_count=count,
            mean_recall=mean_recall,
            coverage_ratio=coverage,
            results=graded,
        )

    def _grade(self, entry: GoldEntry, top_n: int) -> QuestionRecall:
        bundle = self._retriever.retrieve(entry.question, top_k=top_n, min_score=0.0)
        retrieved = self._ordered_doc_ids(bundle.results)
        expected = set(entry.expected_doc_ids)
        found = [doc_id for doc_id in retrieved if doc_id in expected]
        recall = len(set(found)) / len(expected)
        return QuestionRecall(
            question=entry.question,
            expected_doc_ids=sorted(expected),
            retrieved_doc_ids=retrieved,
            found_doc_ids=sorted(set(found)),
            recall=recall,
            covered=expected <= set(retrieved),
        )

    def _ordered_doc_ids(self, results: Sequence[RetrievalResult]) -> list[str]:
        ordered: list[str] = []
        for result in results:
            doc_id = result.chunk.metadata.doc_id
            if doc_id not in ordered:
                ordered.append(doc_id)
        return ordered
