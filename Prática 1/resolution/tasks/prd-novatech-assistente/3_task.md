# Tarefa 3.0: Ingestão — DocumentLoader + Chunker + EmbeddingProvider + VectorStore

## Visão geral

Implementar a fase de ingestão offline: ler os documentos do Anexo A, dividir em chunks *section-aware* preservando tabelas e passos numerados, gerar embeddings com `all-MiniLM-L6-v2` e indexar no ChromaDB com metadados de versão/fonte. É a base de maior risco técnico (chunking de tabelas) e deve ser validada primeiro.

<skills>
### Conformidade com skills

- `code-standards-en` — `DocumentLoader`, `Chunker.split`, `EmbeddingProvider.embed`, `VectorStore.upsert`; CQS (`upsert` mutador), early return, métodos <50 linhas.
- `context7` — validar API do ChromaDB (`PersistentClient`, `upsert`, filtro `where`) e do `sentence-transformers` antes de implementar.
- `repo-folder-structure` — manter no módulo `ingestion/` (camada data).
</skills>

<requirements>
- `DocumentLoader`: ler os `.md` do Anexo A (pasta `anexo-a-documentos-individuais/` na raiz do repositório) normalizando para texto + estrutura (títulos, seções, tabelas); loaders PDF/DOCX/HTML/XLSX plugáveis (RF-01, RNF-07).
- `Chunker`: divisão section-aware, teto ~256 tokens, overlap 10–15%; **não cortar tabelas** (PROC-042, 15+ colunas) nem passos numerados (RF-02).
- `EmbeddingProvider`: `all-MiniLM-L6-v2` (384 dims), cache local do modelo; falha de download → abortar com mensagem clara (não degradar em silêncio).
- `VectorStore`: `ChromaDB PersistentClient`; `upsert` idempotente por `chunk_id`; gravar metadados (`doc_id`, `version`, `version_date`, `source`, `is_official`, `ingested_at`).
- Atualização incremental: reindexar um documento substitui os chunks da versão anterior sem duplicar (RF-10).
</requirements>

## Subtarefas

- [x] 3.1 Implementar `DocumentLoader` para `.md` do Anexo A (com extração de seções/tabelas).
- [x] 3.2 Implementar `Chunker` section-aware com teto de tokens, overlap e preservação de tabelas/passos.
- [x] 3.3 Implementar `EmbeddingProvider` (`all-MiniLM-L6-v2`) com cache e tratamento de erro de download.
- [x] 3.4 Implementar `VectorStore` sobre ChromaDB `PersistentClient` com `upsert` idempotente e metadados.
- [x] 3.5 Orquestrar o fluxo de ingestão do Anexo A (FAQ marcado `is_official=false`).

## Detalhes de implementação

Ver techspec **"Visão dos componentes → ingestion/"**, **"Modelos de dados"**, **"Pontos de integração (sentence-transformers, ChromaDB)"** e a decisão do **teto de ~256 tokens**. Não reproduzir o código — referenciar `techspec-novatech-assistente.md`. Corpus: `POL-001`, `PROC-042-v1`, `PROC-042-v2`, `SLA-2024`, `FAQ-atendimento` (Anexo A).

## Critérios de sucesso

- Os 5 documentos do Anexo A são indexados e recuperáveis por busca semântica relacionada ao conteúdo (RF-01).
- Nenhum chunk de tabela do PROC-042 é cortado no meio de uma linha; passos numerados ficam íntegros (RF-02).
- Reindexar o mesmo documento mantém o nº de chunks estável (sem duplicação) — RF-10.
- FAQ indexado com `is_official=false`.

## Testes da tarefa

- [x] Testes unitários — `Chunker`: teto de ~256 tokens, overlap aplicado, tabela do PROC-042 não cortada, passo numerado íntegro; `VectorStore.upsert`: reindexar mesmo `chunk_id` substitui (não duplica); `EmbeddingProvider`: dimensão 384 e erro de download tratado.
- [x] Testes de integração — ingestão→retrieval ponta a ponta sobre o Anexo A em ChromaDB efêmero (pergunta relacionada recupera o doc correto).
- [x] Testes E2E — N/A no MVP.

## Arquivos relevantes

- `novatech_rag/ingestion/loader.py`, `chunker.py`, `embeddings.py`, `vector_store.py` (a criar).
- `tests/test_chunker.py`, `tests/test_vector_store.py`, `tests/integration/test_ingestion_retrieval.py` (a criar).
- Anexo A — pasta `anexo-a-documentos-individuais/` (raiz): `POL-001-politica-devolucao.md`, `PROC-042-frete-especial-v1.md`, `PROC-042-v2-frete-especial-revisado.md`, `SLA-2024-tabela-sla-clientes.md`, `FAQ-atendimento.md`.
