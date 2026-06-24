"""Camada de avaliação (ferramentas): recall@N, guardrails e LLM-as-judge.

Expõe o `RetrievalEvaluator` (recall@N contra o Anexo B), a `GuardrailSuite`
(casos-armadilha sobre o pipeline real), a rubrica do `llm_judge` e o gerador de
relatório versionado (Ex. 1.3). Validação das tarefas 3.0–5.0.
"""

from .anexo_b_gold import GoldEntry, chunk_label_to_doc_id, load_anexo_b_gold
from .guardrail_suite import (
    ABSTAIN_OPERATING_SCORE,
    GUARDRAIL_CASES,
    GuardrailCase,
    GuardrailKind,
    GuardrailOutcome,
    GuardrailSuite,
)
from .llm_judge import (
    DEFAULT_PASS_THRESHOLD,
    RUBRIC_WEIGHTS,
    Judge,
    RubricScore,
    aggregate_rubric,
    passes_critical_guardrail,
    passes_rubric,
)
from .report import KNOWN_PROBLEMS, build_eval_report, write_eval_report
from .retrieval_evaluator import (
    QuestionRecall,
    RecallReport,
    RetrievalEvaluator,
)

__all__ = [
    "GoldEntry",
    "chunk_label_to_doc_id",
    "load_anexo_b_gold",
    "RetrievalEvaluator",
    "RecallReport",
    "QuestionRecall",
    "GuardrailSuite",
    "GuardrailCase",
    "GuardrailKind",
    "GuardrailOutcome",
    "GUARDRAIL_CASES",
    "ABSTAIN_OPERATING_SCORE",
    "RubricScore",
    "Judge",
    "aggregate_rubric",
    "passes_rubric",
    "passes_critical_guardrail",
    "RUBRIC_WEIGHTS",
    "DEFAULT_PASS_THRESHOLD",
    "build_eval_report",
    "write_eval_report",
    "KNOWN_PROBLEMS",
]
