# Tarefa 2.0: Fundação do pacote `novatech_rag/` — modelos de domínio, Protocols e configuração

## Visão geral

Estabelecer a base do pacote Python: estrutura de módulos (`ingestion/`, `retrieval/`, `prompt/`, `eval/`), as dataclasses de domínio, os `Protocol`s que isolam os pontos de troca PoC↔produção e a configuração central (threshold, top_k, token_budget, modelo de embeddings). Tudo o que as demais tarefas consomem.

<skills>
### Conformidade com skills

- `code-standards-en` — identificadores/símbolos/constantes em **inglês** (`Chunk`, `ChunkMetadata`, `Retriever`, `MAX_CHUNK_TOKENS`, `MIN_SCORE`), `PascalCase` para classes, CQS, métodos curtos. Conteúdo de domínio/prompts em português.
- `repo-folder-structure` — adaptação do layout para pacote Python em camadas (`ingestion/`→data, `retrieval/`/`prompt/`→services, CLI→controllers), respeitando a direção de dependência.
- `context7` — **N/A** aqui (sem dependência externa nova nesta tarefa).
</skills>

<requirements>
- Criar o pacote `novatech_rag/` com os módulos `ingestion/`, `retrieval/`, `prompt/`, `eval/` e `__init__` adequados.
- Definir as dataclasses: `ChunkMetadata`, `Chunk`, `RetrievalResult`, `RetrievalBundle`, `ConflictGroup`, `AssembledPrompt` conforme techspec "Modelos de dados".
- `chunk_id` determinístico: hash de `doc_id|section|ordinal` (base para RF-10 / upsert idempotente).
- Definir os `Protocol`s: `Chunker`, `EmbeddingProvider`, `VectorStore`, `Retriever`, `PromptAssembler` e o *seam* `GenerationAdapter` (não implementado).
- Configuração central tipada (top_k, min_score/threshold, token_budget ≤128K, nome do modelo de embeddings, caminho de persistência do ChromaDB).
- `pyproject.toml`/deps mínimas (Python 3.10+, `chromadb`, `sentence-transformers`; `ollama` opcional).
</requirements>

## Subtarefas

- [x] 2.1 Criar estrutura de pastas e `pyproject.toml` com dependências do PoC.
- [x] 2.2 Implementar as dataclasses de domínio (com `source`/`is_official`/`version`/`version_date`).
- [x] 2.3 Implementar `chunk_id` determinístico e função utilitária de geração.
- [x] 2.4 Definir os `Protocol`s das interfaces e o `GenerationAdapter` (seam).
- [x] 2.5 Implementar objeto de configuração central tipado.

## Detalhes de implementação

Ver techspec **"Design de implementação → Principais interfaces / Modelos de dados"** e **"Considerações técnicas"**. Não reproduzir as assinaturas aqui — referenciar `techspec-novatech-assistente.md`.

## Critérios de sucesso

- Pacote importável; `import novatech_rag` e submódulos funcionam.
- `chunk_id` é estável: mesma `(doc_id, section, ordinal)` → mesmo id; entradas diferentes → ids diferentes.
- Dataclasses cobrem todos os campos de metadados exigidos por G-07 (versão) e priorização oficial vs FAQ (`is_official`).

## Testes da tarefa

- [x] Testes unitários — determinismo e unicidade de `chunk_id`; construção/validação das dataclasses; valores default da configuração.
- [x] Testes de integração — *smoke test* de importação do pacote e dos módulos.
- [x] Testes E2E — N/A no MVP.

## Arquivos relevantes

- `novatech_rag/__init__.py`, `novatech_rag/models.py`, `novatech_rag/interfaces.py`, `novatech_rag/config.py` (a criar).
- `novatech_rag/{ingestion,retrieval,prompt,eval}/__init__.py` (a criar).
- `pyproject.toml` (a criar).
- `tests/test_models.py`, `tests/test_config.py` (a criar).
