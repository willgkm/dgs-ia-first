"""Orquestração da ingestão offline do Anexo A (subtarefa 3.5).

Encadeia `DocumentLoader → SectionAwareChunker → VectorStore`, emitindo um log
estruturado (JSON) por documento e um resumo (nº de docs, chunks gerados, chunks
acima do teto). O manifesto fixa a proveniência dos 5 documentos do Anexo A; o
FAQ é marcado `is_official=False` (fonte não validada).

`build_anexo_a_descriptors` é puro (só monta caminhos/metadados); `ingest_documents`
recebe os componentes já construídos — assim os testes injetam fakes sem tocar
ChromaDB/sentence-transformers, e a produção troca as implementações pelos seams.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from ..config import RagConfig
from ..interfaces import Chunker, VectorStore
from ..models import DocumentSource
from .chunker import estimate_tokens
from .embeddings import SentenceTransformerEmbeddingProvider
from .loader import DocumentDescriptor, DocumentLoader
from .vector_store import ChromaVectorStore

__all__ = [
    "ANEXO_A_DIRNAME",
    "IngestionComponents",
    "IngestionReport",
    "build_anexo_a_descriptors",
    "ingest_documents",
    "ingest_anexo_a",
]

ANEXO_A_DIRNAME = "anexo-a-documentos-individuais"
_LOGGER = logging.getLogger("novatech_rag.ingestion")


@dataclass(frozen=True)
class IngestionComponents:
    """Os três colaboradores encadeados da ingestão, agrupados para serem
    passados como uma unidade (loader → chunker → vector store)."""

    loader: DocumentLoader
    chunker: Chunker
    vector_store: VectorStore


@dataclass(frozen=True)
class IngestionReport:
    """Evidência da ingestão (observabilidade do MVP)."""

    document_count: int
    chunk_count: int
    oversized_chunk_count: int
    chunks_by_doc: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class _ManifestEntry:
    """Entrada do manifesto do Anexo A: proveniência + nome do arquivo-fonte."""

    doc_id: str
    doc_title: str
    version: str
    version_date: str
    source: DocumentSource
    is_official: bool
    filename: str


# Proveniência do Anexo A. PROC-042 v1 e v2 são `doc_id` distintos (coexistem,
# RF-10) — a detecção de conflito (Tarefa 4.0) os reagrupa por versão/título.
# version_date em ISO-8601 (ordenável); o FAQ não tem data nem validação.
_ANEXO_A_MANIFEST: tuple[_ManifestEntry, ...] = (
    _ManifestEntry(
        doc_id="POL-001",
        doc_title="POL-001 — Política de Devolução de Mercadorias",
        version="3.1",
        version_date="2024-01-15",
        source=DocumentSource.SHAREPOINT,
        is_official=True,
        filename="POL-001-politica-devolucao.md",
    ),
    _ManifestEntry(
        doc_id="PROC-042-v1",
        doc_title="PROC-042 — Procedimento de Cálculo de Frete Especial",
        version="1.0",
        version_date="2023-03-03",
        source=DocumentSource.SHAREPOINT,
        is_official=True,
        filename="PROC-042-frete-especial-v1.md",
    ),
    _ManifestEntry(
        doc_id="PROC-042-v2",
        doc_title="PROC-042-v2 — Procedimento de Cálculo de Frete Especial (Revisado)",
        version="2.0",
        version_date="2023-11-10",
        source=DocumentSource.SHAREPOINT,
        is_official=True,
        filename="PROC-042-v2-frete-especial-revisado.md",
    ),
    _ManifestEntry(
        doc_id="SLA-2024",
        doc_title="SLA-2024 — Tabela de SLA por Tipo de Cliente",
        version="2024.1",
        version_date="2024-01-02",
        source=DocumentSource.SHAREPOINT,
        is_official=True,
        filename="SLA-2024-tabela-sla-clientes.md",
    ),
    _ManifestEntry(
        doc_id="FAQ-atendimento",
        doc_title="FAQ-Atendimento — Perguntas Frequentes do Time de Suporte",
        version="não-controlada",
        version_date="",
        source=DocumentSource.FAQ,
        is_official=False,
        filename="FAQ-atendimento.md",
    ),
)


def build_anexo_a_descriptors(corpus_dir: Path) -> list[DocumentDescriptor]:
    """Monta os descriptors dos 5 documentos do Anexo A a partir do manifesto."""
    return [
        DocumentDescriptor(
            doc_id=entry.doc_id,
            doc_title=entry.doc_title,
            version=entry.version,
            version_date=entry.version_date,
            source=entry.source,
            is_official=entry.is_official,
            path=corpus_dir / entry.filename,
        )
        for entry in _ANEXO_A_MANIFEST
    ]


def ingest_documents(
    descriptors: Sequence[DocumentDescriptor],
    components: IngestionComponents,
    *,
    config: RagConfig | None = None,
    logger: logging.Logger = _LOGGER,
) -> IngestionReport:
    """Carrega, divide e indexa cada documento; devolve o relatório de ingestão."""
    cap = (config if config is not None else RagConfig()).max_chunk_tokens
    chunks_by_doc: dict[str, int] = {}
    oversized = 0
    for descriptor in descriptors:
        document = components.loader.load(descriptor)
        chunks = components.chunker.split(document)
        components.vector_store.upsert(chunks)
        chunks_by_doc[descriptor.doc_id] = len(chunks)
        oversized += sum(1 for chunk in chunks if estimate_tokens(chunk.text) > cap)
        _log_json(
            logger,
            event="document_ingested",
            doc_id=descriptor.doc_id,
            source=descriptor.source.value,
            is_official=descriptor.is_official,
            chunks=len(chunks),
        )
    report = IngestionReport(
        document_count=len(descriptors),
        chunk_count=sum(chunks_by_doc.values()),
        oversized_chunk_count=oversized,
        chunks_by_doc=chunks_by_doc,
    )
    _log_json(
        logger,
        event="ingestion_completed",
        documents=report.document_count,
        chunks=report.chunk_count,
        oversized_chunks=report.oversized_chunk_count,
    )
    return report


def ingest_anexo_a(corpus_dir: Path, config: RagConfig | None = None) -> IngestionReport:
    """Conveniência: constrói os componentes reais (ChromaDB + sentence-transformers)
    e ingere o Anexo A. Usada pela CLI; os testes preferem `ingest_documents`."""
    from .chunker import SectionAwareChunker

    resolved = config if config is not None else RagConfig()
    embeddings = SentenceTransformerEmbeddingProvider(resolved.embedding_model)
    components = IngestionComponents(
        loader=DocumentLoader(),
        chunker=SectionAwareChunker(resolved),
        vector_store=ChromaVectorStore(embeddings, resolved),
    )
    return ingest_documents(build_anexo_a_descriptors(corpus_dir), components, config=resolved)


def _log_json(logger: logging.Logger, **fields: object) -> None:
    logger.info(json.dumps(fields, ensure_ascii=False, sort_keys=True))
