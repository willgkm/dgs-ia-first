"""Testes unitários da rubrica do LLM-as-judge.

A agregação é determinística e testável sem chamar modelo algum (pytest-testing,
Etapa 4): a geração é tratada como **grau** de qualidade, não pass/fail binário.
"""

from __future__ import annotations

import pytest

from novatech_rag.eval.llm_judge import (
    RubricScore,
    aggregate_rubric,
    passes_critical_guardrail,
    passes_rubric,
)


class TestRubricScoreValidation:
    def test_rejects_criterion_out_of_range(self) -> None:
        with pytest.raises(ValueError):
            RubricScore(precision=1.2, citation=0.5, guardrail_adherence=1.0)


class TestAggregate:
    def test_perfect_score_aggregates_to_one(self) -> None:
        score = RubricScore(precision=1.0, citation=1.0, guardrail_adherence=1.0)

        assert aggregate_rubric(score) == pytest.approx(1.0)

    def test_weighted_mean_uses_default_weights(self) -> None:
        score = RubricScore(precision=1.0, citation=0.0, guardrail_adherence=0.0)

        assert aggregate_rubric(score) == pytest.approx(0.4)


class TestThresholds:
    def test_passes_rubric_when_above_threshold(self) -> None:
        score = RubricScore(precision=0.9, citation=0.8, guardrail_adherence=1.0)

        assert passes_rubric(score) is True

    def test_fails_rubric_when_below_threshold(self) -> None:
        score = RubricScore(precision=0.3, citation=0.3, guardrail_adherence=0.3)

        assert passes_rubric(score) is False

    def test_critical_guardrail_requires_full_adherence(self) -> None:
        full = RubricScore(precision=0.6, citation=0.6, guardrail_adherence=1.0)
        partial = RubricScore(precision=1.0, citation=1.0, guardrail_adherence=0.9)

        assert passes_critical_guardrail(full) is True
        assert passes_critical_guardrail(partial) is False
