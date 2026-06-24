"""Teste de integração (smoke): o pacote e seus módulos importam e expõem o surface."""

from __future__ import annotations

import importlib

import pytest


def test_top_level_package_imports() -> None:
    package = importlib.import_module("novatech_rag")
    assert package.__version__


@pytest.mark.parametrize(
    "module_name",
    [
        "novatech_rag.models",
        "novatech_rag.interfaces",
        "novatech_rag.config",
        "novatech_rag.ingestion",
        "novatech_rag.retrieval",
        "novatech_rag.prompt",
        "novatech_rag.eval",
    ],
)
def test_submodules_import(module_name: str) -> None:
    assert importlib.import_module(module_name) is not None


@pytest.mark.parametrize(
    "symbol",
    [
        "RagConfig",
        "Chunk",
        "ChunkMetadata",
        "RetrievalResult",
        "RetrievalBundle",
        "ConflictGroup",
        "AssembledPrompt",
        "DocumentSource",
        "compute_chunk_id",
        "build_chunk",
        "Chunker",
        "EmbeddingProvider",
        "VectorStore",
        "Retriever",
        "PromptAssembler",
        "GenerationAdapter",
    ],
)
def test_public_surface_is_exported(symbol: str) -> None:
    package = importlib.import_module("novatech_rag")
    assert hasattr(package, symbol)
    assert symbol in package.__all__


def test_protocols_are_runtime_checkable() -> None:
    from datetime import datetime

    from novatech_rag.interfaces import EmbeddingProvider
    from novatech_rag.models import (
        Chunk,
        ChunkMetadata,
        DocumentSource,
        build_chunk,
    )

    class StubEmbeddingProvider:
        def embed(self, texts):  # type: ignore[no-untyped-def]
            return [[0.0] * 384 for _ in texts]

    assert isinstance(StubEmbeddingProvider(), EmbeddingProvider)

    metadata = ChunkMetadata(
        doc_id="d",
        doc_title="t",
        version="v1",
        version_date="2024-01-01",
        section="s",
        source=DocumentSource.REDE,
        is_official=True,
        ingested_at=datetime(2024, 1, 1),
    )
    chunk = build_chunk("texto", metadata, ordinal=0)
    assert isinstance(chunk, Chunk)
