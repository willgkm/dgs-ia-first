"""Relatório de avaliação versionado: recall@N + guardrails + problemas (Ex. 1.3).

Reúne o `RetrievalEvaluator` e a `GuardrailSuite` num relatório serializável (JSON)
com os agregados de homologação (recall@N, taxa de abstenção correta, aderência aos
guardrails críticos) e a lista de problemas identificados com correções propostas.
A avaliação da geração (texto) é manual no MVP — registrada na evidência 1.3 — e
referenciada aqui pela rubrica do `llm_judge`.

`build_eval_report` é puro (monta o dicionário); `write_eval_report` faz o I/O.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from ..interfaces import PromptAssembler, Retriever
from .anexo_b_gold import GoldEntry
from .guardrail_suite import GuardrailKind, GuardrailOutcome, GuardrailSuite
from .llm_judge import RUBRIC_WEIGHTS
from .retrieval_evaluator import RecallReport, RetrievalEvaluator

__all__ = ["KNOWN_PROBLEMS", "build_eval_report", "write_eval_report"]

_DEFAULT_TOP_N = 5

# Problemas identificados na avaliação (Ex. 1.3, subtarefa 6.7), com correção
# proposta. Evidência empírica detalhada na evidência 1.3.
KNOWN_PROBLEMS: tuple[dict[str, str], ...] = (
    {
        "id": "P1",
        "title": "FAQ não validado supera o documento oficial no ranking",
        "evidence": (
            "Para 'Posso devolver carga perigosa?', os 4 primeiros chunks são do "
            "FAQ (não oficial); POL-001 §3.2 só aparece em 5º (score 0.513)."
        ),
        "fix": (
            "Aplicar filtro/priorização por metadado is_official (where) ou rerank "
            "que promova fonte oficial; já há o seam where no Retriever (G-02)."
        ),
    },
    {
        "id": "P2",
        "title": "Seção com a resposta perde para seções genéricas",
        "evidence": (
            "Para 'Frete para 600kg para Manaus?', 'Objetivo'/'Fórmula' superam a "
            "seção '2.1 Multiplicadores regionais', que contém o valor do Norte."
        ),
        "fix": (
            "Avaliar modelo de embedding multilíngue (paraphrase-multilingual / "
            "bge-m3) e/ou reranker cross-encoder; em produção, busca híbrida + "
            "semantic ranker do Azure AI Search."
        ),
    },
    {
        "id": "P3",
        "title": "Threshold absoluto não separa dentro vs fora da base",
        "evidence": (
            "Scores fora-da-base (0.39–0.54) se sobrepõem aos de perguntas válidas "
            "fracas (~0.50): o all-MiniLM-L6-v2 anglófono comprime a similaridade."
        ),
        "fix": (
            "Calibrar o threshold por validação no Anexo B (operação ~0.55 abstém "
            "10/10 fora-da-base) e migrar para embedding multilíngue para abrir a "
            "margem entre as faixas."
        ),
    },
)


def build_eval_report(
    retriever: Retriever,
    assembler: PromptAssembler,
    gold_entries: Sequence[GoldEntry],
    top_n: int = _DEFAULT_TOP_N,
) -> dict[str, object]:
    """Monta o relatório de avaliação completo (recall@N + guardrails + problemas)."""
    recall = RetrievalEvaluator(retriever).evaluate(gold_entries, top_n=top_n)
    outcomes = GuardrailSuite(retriever, assembler).run()
    return {
        "recall": _recall_section(recall),
        "guardrails": _guardrail_section(outcomes),
        "rubric": {
            "weights": dict(RUBRIC_WEIGHTS),
            "note": (
                "Avaliação de geração é manual no MVP — ver "
                "evidencias/1.3-teste-5-perguntas.md."
            ),
        },
        "problems": [dict(problem) for problem in KNOWN_PROBLEMS],
    }


def write_eval_report(path: Path, report: dict[str, object]) -> None:
    """Persiste o relatório em JSON (I/O isolado do cálculo)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    path.write_text(serialized, encoding="utf-8")


def _recall_section(recall: RecallReport) -> dict[str, object]:
    return {
        "top_n": recall.top_n,
        "question_count": recall.question_count,
        "mean_recall": round(recall.mean_recall, 4),
        "coverage_ratio": round(recall.coverage_ratio, 4),
        "target_met": recall.coverage_ratio >= 0.8,
        "per_question": [
            {
                "question": result.question,
                "expected": result.expected_doc_ids,
                "retrieved": result.retrieved_doc_ids,
                "recall": round(result.recall, 4),
                "covered": result.covered,
            }
            for result in recall.results
        ],
    }


def _guardrail_section(outcomes: Sequence[GuardrailOutcome]) -> dict[str, object]:
    abstain = [outcome for outcome in outcomes if outcome.case.kind is GuardrailKind.ABSTAIN]
    critical = [outcome for outcome in outcomes if outcome.case.critical]
    abstain_passed = sum(1 for outcome in abstain if outcome.passed)
    return {
        "cases": [
            {
                "name": outcome.case.name,
                "guardrail": outcome.case.guardrail,
                "kind": outcome.case.kind.value,
                "critical": outcome.case.critical,
                "passed": outcome.passed,
                "detail": outcome.detail,
            }
            for outcome in outcomes
        ],
        "critical_all_passed": all(outcome.passed for outcome in critical),
        "abstention_rate": f"{abstain_passed}/{len(abstain)}",
        "abstention_target_met": abstain_passed >= 9,
    }
