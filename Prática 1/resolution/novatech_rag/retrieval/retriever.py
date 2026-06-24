"""`SimilarityRetriever`: recuperação em runtime (embed + top-K + threshold).

Implementa o `Retriever` (Protocol): embeda a pergunta com o mesmo provider da
ingestão, busca top-K no `VectorStore` e descarta os chunks abaixo de `min_score`.
Quando nenhum chunk sobrevive ao threshold, marca `below_threshold` para acionar
a abstenção (RF-07/G-03) — o prompt instruirá "não encontrado" + escalonamento,
nunca uma resposta gerada por conhecimento geral. O filtro `where` por metadados
(ex.: `is_official`) é repassado ao store, habilitando a priorização oficial vs FAQ.
O `ConflictDetector` reagrupa os sobreviventes e sinaliza versões divergentes (G-07).

`retrieve` é puro (CQS): consulta e devolve o `RetrievalBundle`, sem mutar estado.
"""

from __future__ import annotations

from ..interfaces import EmbeddingProvider, VectorStore
from ..models import RetrievalBundle
from .conflict_detector import ConflictDetector

__all__ = ["SimilarityRetriever"]


class SimilarityRetriever:
    """Implementa o `Retriever` (Protocol) sobre um `VectorStore` por similaridade."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        conflict_detector: ConflictDetector | None = None,
    ) -> None:
        self._embeddings = embedding_provider
        self._vector_store = vector_store
        self._conflicts = conflict_detector if conflict_detector is not None else ConflictDetector()

    def retrieve(
        self,
        question: str,
        top_k: int,
        min_score: float,
        where: dict | None = None,
    ) -> RetrievalBundle:
        embedding = self._embeddings.embed([question])[0]
        candidates = self._vector_store.query(embedding, top_k, where)
        results = [result for result in candidates if result.score >= min_score]
        if not results:
            return RetrievalBundle(results=[], conflicts=[], below_threshold=True)
        conflicts = self._conflicts.detect(results)
        return RetrievalBundle(results=results, conflicts=conflicts, below_threshold=False)
