"""Fixtures compartilhadas dos testes da ingestão.

Fornece o diretório do corpus (Anexo A), os descriptors do manifesto e um
`EmbeddingProvider` determinístico (sem rede) para isolar os testes unitários do
modelo real — a similaridade fica conhecida e estável (pytest-testing, Etapa 2).
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from pathlib import Path

import pytest

from novatech_rag.config import EMBEDDING_DIMENSIONS
from novatech_rag.ingestion.loader import DocumentDescriptor
from novatech_rag.ingestion.pipeline import ANEXO_A_DIRNAME, build_anexo_a_descriptors

_REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def corpus_dir() -> Path:
    directory = _REPO_ROOT / ANEXO_A_DIRNAME
    if not directory.is_dir():
        pytest.skip(f"Corpus do Anexo A ausente: {directory}")
    return directory


@pytest.fixture
def anexo_a_descriptors(corpus_dir: Path) -> list[DocumentDescriptor]:
    return build_anexo_a_descriptors(corpus_dir)


class DeterministicEmbeddingProvider:
    """`EmbeddingProvider` fake: vetor normalizado de 384 dims derivado das
    palavras do texto (bag-of-words com hash). Sem rede, sem modelo — textos com
    vocabulário parecido ficam próximos, o suficiente para ordenar resultados."""

    def __init__(self, dimensions: int = EMBEDDING_DIMENSIONS) -> None:
        self._dimensions = dimensions

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self._dimensions
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self._dimensions
            vector[index] += 1.0
        norm = sum(value * value for value in vector) ** 0.5
        if norm == 0.0:
            vector[0] = 1.0
            return vector
        return [value / norm for value in vector]


@pytest.fixture
def fake_embedding_provider() -> DeterministicEmbeddingProvider:
    return DeterministicEmbeddingProvider()
