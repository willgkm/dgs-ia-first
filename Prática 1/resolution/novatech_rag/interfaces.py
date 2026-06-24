"""Interfaces (Protocols) que isolam os pontos de troca PoC↔produção.

Definidas como `typing.Protocol` (não ABCs) para que as implementações não
precisem herdar explicitamente: a PoC usa ChromaDB/sentence-transformers, a
produção troca por Azure AI Search/OpenAI reusando estas mesmas assinaturas.

`GenerationAdapter` é apenas o *seam* da geração: declarado aqui, não implementado
no MVP (o pipeline programático termina na montagem do prompt).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from .models import (
    Answer,
    AssembledPrompt,
    Chunk,
    LoadedDocument,
    RetrievalBundle,
    RetrievalResult,
)

__all__ = [
    "Chunker",
    "EmbeddingProvider",
    "VectorStore",
    "Retriever",
    "PromptAssembler",
    "GenerationAdapter",
]


@runtime_checkable
class Chunker(Protocol):
    """Divide um documento carregado em chunks section-aware."""

    def split(self, document: LoadedDocument) -> list[Chunk]: ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Gera embeddings densos para uma sequência de textos (384 dims no MVP)."""

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


@runtime_checkable
class VectorStore(Protocol):
    """Persistência vetorial com upsert idempotente por `chunk_id` (RF-10)."""

    def upsert(self, chunks: Sequence[Chunk]) -> None: ...

    def query(
        self,
        embedding: list[float],
        top_k: int,
        where: dict | None = None,
    ) -> list[RetrievalResult]: ...


@runtime_checkable
class Retriever(Protocol):
    """Embeda a pergunta, busca top-K por similaridade e aplica o threshold.

    Aceita filtro `where` por metadados (ex.: `is_official`) para priorização
    oficial vs FAQ; o mesmo contrato vale na produção (Azure AI Search)."""

    def retrieve(
        self,
        question: str,
        top_k: int,
        min_score: float,
        where: dict | None = None,
    ) -> RetrievalBundle: ...


@runtime_checkable
class PromptAssembler(Protocol):
    """Compõe system prompt estático + chunks ordenados + pergunta dentro do orçamento."""

    def assemble(
        self,
        question: str,
        bundle: RetrievalBundle,
        token_budget: int,
    ) -> AssembledPrompt: ...


@runtime_checkable
class GenerationAdapter(Protocol):
    """Seam de geração (produção). NÃO implementado no MVP.

    A geração da PoC é manual (colar o prompt no Claude) ou via Ollama local;
    a produção fornece um adaptador para Azure OpenAI atrás desta interface.
    """

    def generate(self, prompt: AssembledPrompt) -> Answer: ...
