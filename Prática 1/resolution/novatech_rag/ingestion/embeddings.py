"""`SentenceTransformerEmbeddingProvider`: embeddings densos com `all-MiniLM-L6-v2`.

O modelo é carregado preguiçosamente (sem I/O em tempo de import) e cacheado na
instância. Falha de download/carregamento → `EmbeddingModelError` explícito:
nunca degradar em silêncio nem indexar com dimensionalidade divergente (a
mudança de dimensão corromperia o índice). Os vetores são normalizados (norma 1)
para que a distância de cosseno do ChromaDB seja diretamente comparável.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from ..config import DEFAULT_EMBEDDING_MODEL, EMBEDDING_DIMENSIONS

__all__ = ["EmbeddingModelError", "SentenceTransformerEmbeddingProvider"]


class EmbeddingModelError(RuntimeError):
    """Falha ao baixar/carregar o modelo ou dimensão inesperada do embedding."""


def _load_sentence_transformer(model_name: str) -> Any:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as error:  # dependência ausente: abortar com mensagem clara
        raise EmbeddingModelError(
            "Pacote 'sentence-transformers' não instalado; instale as dependências "
            "do PoC (pyproject) antes de gerar embeddings."
        ) from error
    try:
        return SentenceTransformer(model_name)
    except Exception as error:  # download/carregamento: não degradar silenciosamente
        raise EmbeddingModelError(
            f"Falha ao carregar o modelo de embeddings {model_name!r}: {error}. "
            "Verifique a conexão para o primeiro download ou o cache local."
        ) from error


class SentenceTransformerEmbeddingProvider:
    """Implementa o `EmbeddingProvider` (Protocol). 384 dimensões no MVP."""

    def __init__(
        self,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        expected_dimensions: int = EMBEDDING_DIMENSIONS,
        model_loader: Callable[[str], Any] = _load_sentence_transformer,
    ) -> None:
        self._model_name = model_name
        self._expected_dimensions = expected_dimensions
        self._model_loader = model_loader
        self._model: Any | None = None

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._ensure_model()
        vectors = model.encode(
            list(texts),
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        embeddings = [[float(value) for value in vector] for vector in vectors]
        self._verify_dimensions(embeddings)
        return embeddings

    def _ensure_model(self) -> Any:
        if self._model is None:
            self._model = self._model_loader(self._model_name)
        return self._model

    def _verify_dimensions(self, embeddings: list[list[float]]) -> None:
        actual = len(embeddings[0])
        if actual != self._expected_dimensions:
            raise EmbeddingModelError(
                f"Embedding com {actual} dimensões; esperado "
                f"{self._expected_dimensions} ({self._model_name})."
            )
