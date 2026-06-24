"""novatech_rag — PoC RAG da NovaTech (Ex. 1.3).

Pacote em camadas: `ingestion/` (dados), `retrieval/` e `prompt/` (serviços),
`eval/` (ferramentas). A direção de dependência aponta para os modelos de domínio;
as fronteiras de troca PoC↔produção são `Protocol`s em `interfaces`.

Esta é a fundação (Tarefa 2.0): modelos, interfaces e configuração. As
implementações concretas chegam nas tarefas seguintes.
"""

from __future__ import annotations

from .config import RagConfig
from .interfaces import (
    Chunker,
    EmbeddingProvider,
    GenerationAdapter,
    PromptAssembler,
    Retriever,
    VectorStore,
)
from .models import (
    Answer,
    AssembledPrompt,
    Chunk,
    ChunkMetadata,
    ConflictGroup,
    ConflictVersion,
    DocumentSource,
    LoadedDocument,
    RetrievalBundle,
    RetrievalResult,
    build_chunk,
    compute_chunk_id,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # configuração
    "RagConfig",
    # modelos de domínio
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
    # interfaces (seams)
    "Chunker",
    "EmbeddingProvider",
    "VectorStore",
    "Retriever",
    "PromptAssembler",
    "GenerationAdapter",
]
