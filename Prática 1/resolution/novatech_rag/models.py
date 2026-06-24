"""Modelos de domínio do pipeline RAG da NovaTech.

Entidades de valor (imutáveis) que trafegam entre ingestão, retrieval e prompt.
Os identificadores são em inglês (code-standards-en); o conteúdo de domínio
(textos, títulos de documento) permanece em português, conforme política de produto.

Este módulo é a camada de dados: não importa nada de `retrieval/`, `prompt/` ou
`eval/`. A direção de dependência aponta para cá (python-conventions, Etapa 1).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

__all__ = [
    "DocumentSource",
    "ChunkMetadata",
    "Chunk",
    "RetrievalResult",
    "ConflictVersion",
    "ConflictGroup",
    "RetrievalBundle",
    "AssembledPrompt",
    "LoadedDocument",
    "Answer",
    "compute_chunk_id",
    "build_chunk",
]

CHUNK_ID_SEPARATOR = "|"


class DocumentSource(str, Enum):
    """Origem do documento ingerido.

    `str` como base garante que o valor serialize diretamente nos metadados do
    ChromaDB (que aceita apenas str/int/float/bool).
    """

    SHAREPOINT = "sharepoint"
    CONFLUENCE = "confluence"
    REDE = "rede"
    FAQ = "faq"


def compute_chunk_id(doc_id: str, section: str, ordinal: int) -> str:
    """Calcula o id determinístico de um chunk.

    O mesmo `(doc_id, section, ordinal)` sempre produz o mesmo id; entradas
    diferentes produzem ids diferentes. Essa estabilidade é a base do upsert
    idempotente (RF-10): reindexar substitui a versão anterior em vez de duplicar.
    """
    payload = CHUNK_ID_SEPARATOR.join((doc_id, section, str(ordinal)))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ChunkMetadata:
    """Metadados de proveniência e versão de um chunk.

    `version`/`version_date` e `is_official` são a base para a desambiguação de
    documentos conflitantes (G-07) e para priorizar documento oficial sobre o FAQ.
    """

    doc_id: str
    doc_title: str
    version: str
    version_date: str  # ISO-8601 (ex.: "2024-03-01"); ordenável lexicograficamente
    section: str
    source: DocumentSource
    is_official: bool
    ingested_at: datetime


@dataclass(frozen=True)
class Chunk:
    """Unidade indexável: texto + metadados, identificada por `chunk_id` estável."""

    chunk_id: str
    text: str
    metadata: ChunkMetadata


def build_chunk(text: str, metadata: ChunkMetadata, ordinal: int) -> Chunk:
    """Cria um `Chunk` derivando o `chunk_id` de `(doc_id, section, ordinal)`."""
    chunk_id = compute_chunk_id(metadata.doc_id, metadata.section, ordinal)
    return Chunk(chunk_id=chunk_id, text=text, metadata=metadata)


@dataclass(frozen=True)
class RetrievalResult:
    """Resultado individual da busca vetorial."""

    chunk: Chunk
    score: float
    rank: int


@dataclass(frozen=True)
class ConflictVersion:
    """Uma das versões envolvidas num conflito de documento."""

    version: str
    version_date: str
    chunk_id: str


@dataclass(frozen=True)
class ConflictGroup:
    """Versões divergentes de um mesmo `doc_id` recuperadas na mesma consulta.

    Ex.: PROC-042 v1 + v2 retornadas juntas exigem alerta de divergência (G-07/G-08).
    """

    doc_id: str
    versions: list[ConflictVersion]


@dataclass(frozen=True)
class RetrievalBundle:
    """Pacote completo retornado pelo `Retriever` para uma pergunta.

    `below_threshold` sinaliza que nenhum chunk superou o `min_score` — base da
    abstenção (G-03): o prompt instrui resposta de "não encontrado" + escalonamento.
    """

    results: list[RetrievalResult]
    conflicts: list[ConflictGroup] = field(default_factory=list)
    below_threshold: bool = False


@dataclass(frozen=True)
class AssembledPrompt:
    """Prompt final pronto para a geração (manual, Ollama ou GenerationAdapter)."""

    system: str
    context_blocks: list[str]
    question: str
    estimated_tokens: int
    dropped_chunks: list[Chunk] = field(default_factory=list)


@dataclass(frozen=True)
class LoadedDocument:
    """Documento normalizado pelo `DocumentLoader`, antes do chunking.

    Modelo mínimo da fundação; a ingestão (Tarefa 3.0) pode enriquecê-lo com
    estrutura de seções/tabelas sem quebrar os consumidores existentes.
    """

    doc_id: str
    doc_title: str
    version: str
    version_date: str
    source: DocumentSource
    is_official: bool
    text: str


@dataclass(frozen=True)
class Answer:
    """Resposta gerada. Produzida apenas pela produção via `GenerationAdapter`
    (seam); fora do caminho automatizado do MVP."""

    text: str
    citations: list[str] = field(default_factory=list)
