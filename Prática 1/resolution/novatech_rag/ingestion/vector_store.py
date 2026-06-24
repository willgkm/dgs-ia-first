"""`ChromaVectorStore`: índice vetorial sobre ChromaDB `PersistentClient`.

`upsert` é idempotente por `chunk_id` determinístico (RF-10): reindexar um
documento substitui seus chunks em vez de duplicar. O `upsert` embeda o texto
dos chunks internamente (via `EmbeddingProvider`); `query` recebe o embedding já
calculado da pergunta (CQS: `upsert` muta e retorna `None`, `query` é puro).

Espaço de similaridade = cosseno; o score reportado é `1 − distância`, com os
vetores normalizados pelo provider. O cliente ChromaDB é criado preguiçosamente
(sem I/O em import).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from ..config import RagConfig
from ..interfaces import EmbeddingProvider
from ..models import Chunk, ChunkMetadata, DocumentSource, RetrievalResult

__all__ = ["VectorStoreError", "ChromaVectorStore"]

_COSINE_SPACE = {"hnsw:space": "cosine"}


class VectorStoreError(RuntimeError):
    """Falha ao inicializar o ChromaDB ou ao persistir/consultar chunks."""


class ChromaVectorStore:
    """Implementa o `VectorStore` (Protocol) sobre ChromaDB persistente em disco."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        config: RagConfig,
        client: Any | None = None,
    ) -> None:
        self._embeddings = embedding_provider
        self._persist_directory = config.persist_directory
        self._collection_name = config.collection_name
        self._client = client
        self._collection: Any | None = None

    def upsert(self, chunks: Sequence[Chunk]) -> None:
        if not chunks:
            return
        embeddings = self._embeddings.embed([chunk.text for chunk in chunks])
        self._require_collection().upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            embeddings=embeddings,
            documents=[chunk.text for chunk in chunks],
            metadatas=[_to_metadata_dict(chunk.metadata) for chunk in chunks],
        )

    def query(
        self,
        embedding: list[float],
        top_k: int,
        where: dict | None = None,
    ) -> list[RetrievalResult]:
        response = self._require_collection().query(
            query_embeddings=[embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        return _to_results(response)

    def count(self) -> int:
        return int(self._require_collection().count())

    def _require_collection(self) -> Any:
        if self._collection is None:
            self._collection = self._build_collection()
        return self._collection

    def _build_collection(self) -> Any:
        client = self._client if self._client is not None else self._build_client()
        try:
            return client.get_or_create_collection(
                name=self._collection_name,
                metadata=_COSINE_SPACE,
            )
        except Exception as error:
            raise VectorStoreError(
                f"Falha ao abrir a coleção {self._collection_name!r}: {error}"
            ) from error

    def _build_client(self) -> Any:
        try:
            import chromadb
        except ImportError as error:
            raise VectorStoreError(
                "Pacote 'chromadb' não instalado; instale as dependências do PoC."
            ) from error
        self._persist_directory.mkdir(parents=True, exist_ok=True)
        return chromadb.PersistentClient(path=str(self._persist_directory))


def _to_metadata_dict(metadata: ChunkMetadata) -> dict[str, Any]:
    """Serializa metadados para os tipos aceitos pelo ChromaDB (str/int/float/bool)."""
    return {
        "doc_id": metadata.doc_id,
        "doc_title": metadata.doc_title,
        "version": metadata.version,
        "version_date": metadata.version_date,
        "section": metadata.section,
        "source": metadata.source.value,
        "is_official": metadata.is_official,
        "ingested_at": metadata.ingested_at.isoformat(),
    }


def _to_results(response: dict[str, Any]) -> list[RetrievalResult]:
    ids = _first_row(response, "ids")
    documents = _first_row(response, "documents")
    metadatas = _first_row(response, "metadatas")
    distances = _first_row(response, "distances")
    results: list[RetrievalResult] = []
    for rank, chunk_id in enumerate(ids):
        chunk = Chunk(
            chunk_id=chunk_id,
            text=documents[rank],
            metadata=_from_metadata_dict(metadatas[rank]),
        )
        score = 1.0 - float(distances[rank])
        results.append(RetrievalResult(chunk=chunk, score=score, rank=rank))
    return results


def _first_row(response: dict[str, Any], key: str) -> list[Any]:
    rows = response.get(key)
    if not rows:
        return []
    return rows[0]


def _from_metadata_dict(metadata: dict[str, Any]) -> ChunkMetadata:
    return ChunkMetadata(
        doc_id=str(metadata["doc_id"]),
        doc_title=str(metadata["doc_title"]),
        version=str(metadata["version"]),
        version_date=str(metadata["version_date"]),
        section=str(metadata["section"]),
        source=DocumentSource(str(metadata["source"])),
        is_official=bool(metadata["is_official"]),
        ingested_at=datetime.fromisoformat(str(metadata["ingested_at"])),
    )
