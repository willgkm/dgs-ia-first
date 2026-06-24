# novatech_rag

PoC RAG da NovaTech (Exercício 1.3 — papel Desenvolvedor). Biblioteca/CLI Python que
ingere a documentação da NovaTech, indexa em ChromaDB local com embeddings
`all-MiniLM-L6-v2` e monta o prompt final (system prompt estático + chunks dinâmicos +
pergunta). A geração é manual (Claude) ou via Ollama; a produção troca as
implementações por Azure AI Search/OpenAI reusando as mesmas interfaces.

> PRD: `resolution/prd/prd-novatech-assistente.md` · Techspec: `resolution/prd/techspec-novatech-assistente.md`

## Estado atual

Tarefa 2.0 — **fundação**: modelos de domínio, `Protocol`s das interfaces e
configuração central. As implementações concretas chegam nas tarefas 3.0–7.0.

## Layout

```
novatech_rag/
  __init__.py        # surface pública
  models.py          # dataclasses de domínio + chunk_id determinístico
  interfaces.py      # Protocols (Chunker, EmbeddingProvider, VectorStore, ...)
  config.py          # RagConfig tipado
  ingestion/         # (3.0) DocumentLoader, Chunker, EmbeddingProvider, VectorStore
  retrieval/         # (4.0) Retriever + ConflictDetector
  prompt/            # (5.0) system prompt versionado + PromptAssembler
  eval/              # (6.0) RetrievalEvaluator + GuardrailSuite
tests/               # pytest
```

## Desenvolvimento

```bash
python -m venv .venv && . .venv/Scripts/activate   # Windows
pip install -e ".[dev]"
pytest
ruff check . && ruff format --check .
mypy novatech_rag
```
