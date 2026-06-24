"""Camada de ingestão (dados): DocumentLoader, Chunker, EmbeddingProvider, VectorStore.

Implementações concretas da fase de ingestão offline (Tarefa 3.0). As classes
satisfazem os `Protocol`s de `novatech_rag.interfaces`, mantendo os seams de
troca PoC↔produção (python-conventions / repo-folder-structure).
"""

from __future__ import annotations

from .chunker import SectionAwareChunker, estimate_tokens
from .embeddings import EmbeddingModelError, SentenceTransformerEmbeddingProvider
from .loader import (
    DocumentDescriptor,
    DocumentLoader,
    DocumentLoadError,
    UnsupportedFormatError,
    load_markdown,
)
from .pipeline import (
    ANEXO_A_DIRNAME,
    IngestionComponents,
    IngestionReport,
    build_anexo_a_descriptors,
    ingest_anexo_a,
    ingest_documents,
)
from .sections import Block, BlockKind, Section, parse_sections
from .vector_store import ChromaVectorStore, VectorStoreError

__all__ = [
    # loader
    "DocumentLoader",
    "DocumentDescriptor",
    "DocumentLoadError",
    "UnsupportedFormatError",
    "load_markdown",
    # estrutura
    "parse_sections",
    "Section",
    "Block",
    "BlockKind",
    # chunker
    "SectionAwareChunker",
    "estimate_tokens",
    # embeddings
    "SentenceTransformerEmbeddingProvider",
    "EmbeddingModelError",
    # vector store
    "ChromaVectorStore",
    "VectorStoreError",
    # orquestração
    "ingest_documents",
    "ingest_anexo_a",
    "build_anexo_a_descriptors",
    "IngestionComponents",
    "IngestionReport",
    "ANEXO_A_DIRNAME",
]
