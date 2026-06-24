"""Configuração central tipada do pipeline RAG.

Concentra os parâmetros de troca PoC↔produção e os limites de engenharia
(teto de chunk, orçamento de tokens, threshold de abstenção). Valores expressos
como constantes nomeadas para que a lógica revele a intenção (code-standards-en).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "DEFAULT_EMBEDDING_MODEL",
    "EMBEDDING_DIMENSIONS",
    "MAX_CHUNK_TOKENS",
    "DEFAULT_CHUNK_OVERLAP_RATIO",
    "DEFAULT_TOP_K",
    "MIN_SCORE",
    "DEFAULT_TOKEN_BUDGET",
    "TOKEN_BUDGET_LIMIT",
    "DEFAULT_PERSIST_DIRECTORY",
    "DEFAULT_COLLECTION_NAME",
    "RagConfig",
]

# Embeddings — all-MiniLM-L6-v2 trunca a entrada em 256 word pieces (384 dims).
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSIONS = 384

# Chunking section-aware: teto de ~256 tokens + overlap ~10-15%.
MAX_CHUNK_TOKENS = 256
DEFAULT_CHUNK_OVERLAP_RATIO = 0.12

# Retrieval e abstenção por threshold.
DEFAULT_TOP_K = 5
MIN_SCORE = 0.35

# Orçamento de contexto — RNF-06 impõe teto de 128K tokens.
DEFAULT_TOKEN_BUDGET = 8_000
TOKEN_BUDGET_LIMIT = 128_000

# Persistência local do ChromaDB (PersistentClient).
DEFAULT_PERSIST_DIRECTORY = Path(".chroma")
DEFAULT_COLLECTION_NAME = "novatech"


@dataclass(frozen=True)
class RagConfig:
    """Parâmetros centrais do pipeline, com defaults voltados à PoC.

    Imutável: variações de configuração são instâncias distintas, evitando
    estado compartilhado mutável entre ingestão, retrieval e prompt.
    """

    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    embedding_dimensions: int = EMBEDDING_DIMENSIONS
    max_chunk_tokens: int = MAX_CHUNK_TOKENS
    chunk_overlap_ratio: float = DEFAULT_CHUNK_OVERLAP_RATIO
    top_k: int = DEFAULT_TOP_K
    min_score: float = MIN_SCORE
    token_budget: int = DEFAULT_TOKEN_BUDGET
    persist_directory: Path = DEFAULT_PERSIST_DIRECTORY
    collection_name: str = DEFAULT_COLLECTION_NAME

    def __post_init__(self) -> None:
        if self.token_budget <= 0:
            raise ValueError("token_budget deve ser positivo.")
        if self.token_budget > TOKEN_BUDGET_LIMIT:
            raise ValueError(
                f"token_budget ({self.token_budget}) excede o limite de "
                f"{TOKEN_BUDGET_LIMIT} tokens (RNF-06)."
            )
        if self.top_k <= 0:
            raise ValueError("top_k deve ser positivo.")
        if not 0.0 <= self.min_score <= 1.0:
            raise ValueError("min_score deve estar no intervalo [0.0, 1.0].")
        if not 0.0 <= self.chunk_overlap_ratio < 1.0:
            raise ValueError("chunk_overlap_ratio deve estar no intervalo [0.0, 1.0).")
        if self.max_chunk_tokens <= 0:
            raise ValueError("max_chunk_tokens deve ser positivo.")
        if self.embedding_dimensions <= 0:
            raise ValueError("embedding_dimensions deve ser positivo.")
