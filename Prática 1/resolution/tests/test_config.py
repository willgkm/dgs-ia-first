"""Testes unitários da configuração central tipada."""

from __future__ import annotations

from pathlib import Path

import pytest

from novatech_rag.config import (
    DEFAULT_EMBEDDING_MODEL,
    EMBEDDING_DIMENSIONS,
    MAX_CHUNK_TOKENS,
    TOKEN_BUDGET_LIMIT,
    RagConfig,
)


class TestDefaults:
    def test_default_values(self) -> None:
        config = RagConfig()
        assert config.embedding_model == DEFAULT_EMBEDDING_MODEL
        assert config.embedding_dimensions == EMBEDDING_DIMENSIONS
        assert config.max_chunk_tokens == MAX_CHUNK_TOKENS
        assert config.top_k > 0
        assert 0.0 <= config.min_score <= 1.0
        assert config.token_budget <= TOKEN_BUDGET_LIMIT
        assert isinstance(config.persist_directory, Path)

    def test_is_immutable(self) -> None:
        import dataclasses

        config = RagConfig()
        with pytest.raises(dataclasses.FrozenInstanceError):
            config.top_k = 99  # type: ignore[misc]


class TestValidation:
    def test_token_budget_above_limit_raises(self) -> None:
        with pytest.raises(ValueError, match="excede o limite"):
            RagConfig(token_budget=TOKEN_BUDGET_LIMIT + 1)

    def test_token_budget_at_limit_is_allowed(self) -> None:
        config = RagConfig(token_budget=TOKEN_BUDGET_LIMIT)
        assert config.token_budget == TOKEN_BUDGET_LIMIT

    def test_non_positive_token_budget_raises(self) -> None:
        with pytest.raises(ValueError, match="token_budget"):
            RagConfig(token_budget=0)

    def test_non_positive_top_k_raises(self) -> None:
        with pytest.raises(ValueError, match="top_k"):
            RagConfig(top_k=0)

    @pytest.mark.parametrize("min_score", [-0.1, 1.1])
    def test_min_score_out_of_range_raises(self, min_score: float) -> None:
        with pytest.raises(ValueError, match="min_score"):
            RagConfig(min_score=min_score)

    @pytest.mark.parametrize("overlap", [-0.1, 1.0, 1.5])
    def test_overlap_out_of_range_raises(self, overlap: float) -> None:
        with pytest.raises(ValueError, match="chunk_overlap_ratio"):
            RagConfig(chunk_overlap_ratio=overlap)

    def test_custom_valid_config(self) -> None:
        config = RagConfig(top_k=8, min_score=0.5, token_budget=16_000)
        assert config.top_k == 8
        assert config.min_score == 0.5
        assert config.token_budget == 16_000
