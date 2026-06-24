"""Testes unitários do `SentenceTransformerEmbeddingProvider`.

Dimensão 384 e tratamento de erro de download/carregamento — sem baixar o modelo
real: o `model_loader` é injetado por um fake (pytest-testing, determinismo).
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from novatech_rag.config import EMBEDDING_DIMENSIONS
from novatech_rag.ingestion.embeddings import (
    EmbeddingModelError,
    SentenceTransformerEmbeddingProvider,
)


class FakeModel:
    def __init__(self, dimensions: int) -> None:
        self._dimensions = dimensions

    def encode(self, texts: Sequence[str], **_: object) -> list[list[float]]:
        return [[0.1] * self._dimensions for _ in texts]


def loader_returning(dimensions: int):
    def _load(_model_name: str) -> FakeModel:
        return FakeModel(dimensions)

    return _load


class TestEmbed:
    def test_returns_vectors_with_expected_dimensions(self) -> None:
        provider = SentenceTransformerEmbeddingProvider(
            model_loader=loader_returning(EMBEDDING_DIMENSIONS)
        )

        vectors = provider.embed(["primeira", "segunda"])

        assert len(vectors) == 2
        assert all(len(vector) == EMBEDDING_DIMENSIONS for vector in vectors)

    def test_empty_input_returns_empty_without_loading_model(self) -> None:
        def _fail(_name: str):
            raise AssertionError("modelo não deveria ser carregado para entrada vazia")

        provider = SentenceTransformerEmbeddingProvider(model_loader=_fail)

        assert provider.embed([]) == []

    def test_model_is_loaded_once_and_cached(self) -> None:
        calls = {"count": 0}

        def _counting(_name: str) -> FakeModel:
            calls["count"] += 1
            return FakeModel(EMBEDDING_DIMENSIONS)

        provider = SentenceTransformerEmbeddingProvider(model_loader=_counting)
        provider.embed(["a"])
        provider.embed(["b"])

        assert calls["count"] == 1


class TestErrorHandling:
    def test_unexpected_dimension_raises(self) -> None:
        provider = SentenceTransformerEmbeddingProvider(
            model_loader=loader_returning(128)
        )

        with pytest.raises(EmbeddingModelError, match="dimensões"):
            provider.embed(["texto"])

    def test_download_failure_raises_clear_error(self) -> None:
        def _failing_loader(_name: str):
            raise EmbeddingModelError("Falha ao carregar o modelo de embeddings")

        provider = SentenceTransformerEmbeddingProvider(model_loader=_failing_loader)

        with pytest.raises(EmbeddingModelError, match="Falha ao carregar"):
            provider.embed(["texto"])
