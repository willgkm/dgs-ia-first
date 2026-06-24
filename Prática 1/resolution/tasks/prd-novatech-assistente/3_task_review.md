# Review: Task 3.0 - Ingestão — DocumentLoader + Chunker + EmbeddingProvider + VectorStore

**Revisor**: AI Code Reviewer
**Data**: 2026-06-15
**Arquivo da task**: 3_task.md
**Status**: APROVADO COM OBSERVAÇÕES

## Resumo

A Tarefa 3.0 entrega a fase de ingestão offline completa: `DocumentLoader` (com loaders plugáveis por extensão), `SectionAwareChunker` (chunking section-aware com teto de tokens e overlap), `SentenceTransformerEmbeddingProvider` (`all-MiniLM-L6-v2`, 384 dims) e `ChromaVectorStore` (upsert idempotente sobre `PersistentClient`), além da orquestração `ingest_documents`/`ingest_anexo_a`. Um módulo auxiliar `sections.py` isola a extração estrutural do Markdown (blocos atômicos), que é o coração do RF-02.

A implementação é de alta qualidade: respeita estritamente os requisitos da task (RF-01, RF-02, RF-10), a direção de dependência (camada de dados não importa de `retrieval/`/`prompt/`/`eval/`), CQS, tratamento explícito de erro (sem degradação silenciosa) e o desvio consciente de idioma (identificadores em inglês, conteúdo de domínio em português). Verificações de ambiente executadas e confirmadas: **75 testes unitários passando** (`-m "not integration"`), **80 passando** com integração, **ruff** limpo e **mypy** sem erros. Não foram encontrados problemas críticos nem major bloqueantes; apenas observações minor.

## Arquivos Revisados

| Arquivo | Status | Problemas |
|---------|--------|-----------|
| `novatech_rag/ingestion/sections.py` | OK | Nenhum |
| `novatech_rag/ingestion/loader.py` | OK | Nenhum |
| `novatech_rag/ingestion/chunker.py` | OK | 1 minor (🟢) |
| `novatech_rag/ingestion/embeddings.py` | OK | Nenhum |
| `novatech_rag/ingestion/vector_store.py` | OK | 1 minor (🟢) |
| `novatech_rag/ingestion/pipeline.py` | OK | 2 minor (🟢) |
| `novatech_rag/ingestion/__init__.py` | OK | Nenhum |
| `tests/conftest.py` | OK | Nenhum |
| `tests/test_chunker.py` | OK | Nenhum |
| `tests/test_vector_store.py` | OK | 1 minor (🟢) |
| `tests/test_embeddings.py` | OK | Nenhum |
| `tests/test_loader.py` | OK | Nenhum |
| `tests/integration/test_ingestion_retrieval.py` | OK | Nenhum |
| `pyproject.toml` | OK | Nenhum |

## Problemas Encontrados

### 🔴 Problemas Críticos

Nenhum.

Verificações específicas confirmadas como corretas:

- **RF-02 (tabelas/passos íntegros)**: `sections.py` reconhece tabela (`_TABLE`), passo numerado (`_NUMBERED`) e lista como blocos atômicos; `_consume_table` e `_consume_indented_run` consomem o bloco inteiro, e `_pack_blocks` só quebra **entre** blocos (`chunker.py:75-91`). Um bloco atômico maior que o teto é mantido inteiro (`chunker.py:84-86`, comentário "bloco atômico maior que o teto: não cortar"). Os testes `test_oversized_atomic_table_is_kept_whole`, `test_numbered_step_is_not_split_across_chunks`, `test_proc_042_v1_multiplier_table_stays_intact` e `test_pol_001_procedure_steps_are_each_intact` cobrem isso; confirmei que as linhas `| Sul | 1.2 |`, `| Sudeste | 1.0 |`, `| Norte | 1.6 |` existem no `PROC-042-frete-especial-v1.md` (linhas 27/28/31).
- **RF-10 (idempotência)**: `chunk_id` determinístico via `hashlib.sha256` de `doc_id|section|ordinal` (`models.py:49-57`); `ChromaVectorStore.upsert` usa `collection.upsert(ids=...)`. Testes `test_reindexing_same_chunk_id_replaces_not_duplicates`, `test_distinct_chunk_ids_coexist` e o de integração `test_reingesting_keeps_chunk_count_stable` validam contagem estável.
- **CQS**: `upsert` muta e retorna `None`; `query`/`count` são puros (`vector_store.py:47-73`). O `upsert` embeda internamente (mutador) e `query` recebe o embedding já calculado — separação correta.
- **Tratamento de erro explícito**: dependência ausente (`ImportError`) e falha de download/carregamento são convertidas em `EmbeddingModelError`/`VectorStoreError` com mensagem clara, sem fallback que mude a dimensionalidade (`embeddings.py:24-38`, `vector_store.py:92-100`). `_verify_dimensions` aborta se a dimensão divergir (`embeddings.py:73-79`). Alinhado ao `rag-pipeline` ("never index with a fallback that changes vector dimensionality").
- **Determinismo dos testes**: `conftest.py` injeta `DeterministicEmbeddingProvider` (bag-of-words com hash, sem rede); `test_embeddings` injeta `model_loader` fake; ChromaDB roda sob `tmp_path` efêmero; `importorskip("chromadb")`/`importorskip("sentence_transformers")` e marker `integration` isolam o caminho que baixa o modelo.
- **Direção de dependência**: `ingestion/` importa apenas de `..config`, `..models`, `..interfaces` e do próprio pacote — nunca de `retrieval/`/`prompt/`/`eval/`.

### 🟡 Problemas Major

Nenhum.

### 🟢 Problemas Minor

1. **`pipeline.py:119-127` — `ingest_documents` com 4 parâmetros posicionais.** `code-standards-en` recomenda ≤3 parâmetros, preferindo objeto de configuração acima disso. Aqui são colaboradores injetados distintos (`descriptors`, `loader`, `chunker`, `vector_store`) + dois keyword-only (`config`, `logger`). É um caso legítimo de injeção de dependência e a legibilidade não sofre, mas, se quiser aderência estrita, considere um pequeno dataclass `IngestionComponents(loader, chunker, vector_store)`:
   ```python
   @dataclass(frozen=True)
   class IngestionComponents:
       loader: DocumentLoader
       chunker: Chunker
       vector_store: VectorStore

   def ingest_documents(descriptors: Sequence[DocumentDescriptor],
                        components: IngestionComponents, *, config=None, logger=_LOGGER): ...
   ```
   Não-bloqueante.

2. **`pipeline.py:54` — manifesto tipado como `tuple[dict, ...]` (dict sem parâmetros).** Os valores misturam `str`, `bool` e `DocumentSource`, então um `dict[str, object]` seria mais honesto que `dict` nu. Como mypy está configurado com `ignore_missing_imports`/sem `disallow_any_generics`, não acusa; é apenas precisão de tipo. Alternativa mais robusta: tornar o manifesto uma tupla de `DocumentDescriptor` parciais ou de um dataclass dedicado, eliminando o acesso por string `entry["doc_id"]`.

3. **`vector_store.py:62 e interfaces.py:59` — `where: dict | None` usa `dict` nu.** Coerente com a assinatura do `Protocol` na techspec, então não é divergência. Ainda assim, `Mapping[str, Any] | None` exprimiria melhor a intenção de leitura. Minor de estilo; manter consistência com o Protocol é aceitável.

4. **`test_vector_store.py:117 / 62 / 82 / 94 — acesso a `store._embeddings` (atributo privado) nos testes.** `_query_vector` usa `store._embeddings.embed(...)`. Funciona e mantém o teste determinístico, mas acoplar ao atributo privado é frágil se a interna mudar. Como o fixture `fake_embedding_provider` já está disponível, seria preferível injetá-lo diretamente no helper:
   ```python
   def _query_vector(provider, text: str) -> list[float]:
       return provider.embed([text])[0]
   ```
   Não-bloqueante.

## ✅ Destaques Positivos

- **Separação `sections.py` pura**: extrair o reconhecimento de blocos atômicos para um módulo sem I/O e sem dependências externas é a decisão de design que torna o RF-02 testável e reaproveitável entre `DocumentLoader` e `Chunker`. Excelente.
- **Orçamento de chunk explícito**: `core_budget = max(1, max_tokens − tokens(heading) − overlap_budget)` (`chunker.py:65-66`) garante que heading + overlap + corpo nunca estourem o teto — raciocínio de engenharia correto e documentado no docstring.
- **Overlap só de parágrafos**: `_overlap_text` filtra `BlockKind.PARAGRAPH` (`chunker.py:107-117`), evitando duplicar tabelas/passos no overlap — exatamente o que o `rag-pipeline` pede.
- **Carregamento preguiçoso sem efeito colateral em import**: tanto o modelo de embeddings quanto o cliente ChromaDB são construídos sob demanda (`_ensure_model`, `_require_collection`), respeitando o `python-conventions` (Etapa 3.5: sem I/O em import).
- **Observabilidade**: `IngestionReport` + logs JSON estruturados (`document_ingested`, `ingestion_completed`) com nº de docs, chunks e chunks oversized atendem o item de monitoramento do MVP na techspec.
- **`__init__.py` com superfície pública explícita** (`__all__`) por subgrupo, alinhado ao `python-conventions` ("expose only the intended public surface").
- **Testes minuciosos e legíveis**: nomes no padrão `test_<unit>_<condition>_<expected>`, AAA claro, marcadores únicos (`TokenNN`) para provar overlap sem ambiguidade, asserções específicas (`is False`, `is DocumentSource.FAQ`, `pytest.approx(1.0)`).

## Conformidade com Padrões

| Padrão | Status |
|--------|--------|
| Padrões de Código (`code-standards-en`: inglês, snake_case/PascalCase, CQS, early return, métodos <50 linhas, sem números mágicos) | ✅ Conforme (1 observação minor sobre arity em `ingest_documents`) |
| Python / Type hints (mypy) | ✅ `mypy novatech_rag` sem erros; type hints em todas as funções públicas; `dict` nu em 2 pontos (minor, não acusado) |
| RAG pipeline (section-aware, teto de tokens, overlap, upsert idempotente por `chunk_id`, metadados de versão/fonte, `is_official=False` no FAQ) | ✅ Conforme |
| Logging (estruturado JSON por documento e resumo de ingestão) | ✅ Conforme |
| Testes (`pytest-testing`: unit determinístico, mock de embeddings, ChromaDB efêmero, `importorskip`, marker `integration`) | ✅ Conforme — 75 unit / 80 total passando |

## Recomendações

1. (Opcional) Agrupar os colaboradores de `ingest_documents` em um dataclass `IngestionComponents` para aderência estrita à regra de arity.
2. (Opcional) Tipar o manifesto do Anexo A com precisão (`dict[str, object]` ou dataclass dedicado) e eliminar o acesso por string literal.
3. (Opcional) Trocar `where: dict | None` por `Mapping[str, Any] | None` nas assinaturas — combinando, ajustar também o `Protocol` em `interfaces.py` para manter coerência.
4. (Opcional) Nos testes de `vector_store`, injetar o `fake_embedding_provider` no helper `_query_vector` em vez de acessar `store._embeddings`.

Nenhuma recomendação é bloqueante.

## Veredito

**APROVADO COM OBSERVAÇÕES.** A tarefa cumpre todos os requisitos e critérios de sucesso (RF-01, RF-02, RF-10, FAQ `is_official=False`), com testes unitários e de integração cobrindo os comportamentos exigidos pela techspec e pelas skills. Verificações de ambiente (pytest, ruff, mypy) passam integralmente. Os quatro itens minor são melhorias opcionais de estilo/precisão de tipo e não impedem a aprovação. Liberado para prosseguir à Tarefa 4.0 (Retriever + threshold + ConflictDetector).
