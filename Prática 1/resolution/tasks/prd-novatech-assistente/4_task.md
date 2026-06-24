# Tarefa 4.0: Retrieval — Retriever (top-K + threshold) + ConflictDetector

## Visão geral

Implementar a recuperação em runtime: dada uma pergunta, gerar o embedding, buscar top-K por similaridade no `VectorStore`, aplicar o threshold mínimo (habilitando abstenção) e detectar versões conflitantes do mesmo documento (PROC-042 v1 + v2). Saída consumida pela camada de prompt.

<skills>
### Conformidade com skills

- `code-standards-en` — `Retriever.retrieve`, `ConflictDetector`; `query`/`retrieve` como operações puras (CQS), early return para `below_threshold`.
- `context7` — confirmar filtro `where` por metadados na API do ChromaDB.
- `repo-folder-structure` — módulo `retrieval/` (camada services).
</skills>

<requirements>
- `Retriever.retrieve(question, top_k, min_score)`: embeda a pergunta, busca top-K, retorna `RetrievalBundle` com `results`, `conflicts` e `below_threshold` (RF-03).
- Threshold mínimo configurável (PRD: 0,70); abaixo dele → `below_threshold=True` para acionar abstenção (RF-07, G-03).
- Suporte a filtro `where` por metadados (ex.: `is_official`) para priorização oficial vs FAQ.
- `ConflictDetector`: agrupa resultados por `doc_id` e retorna `ConflictGroup` com as versões (`version`, `version_date`, `chunk_id`) quando há divergência (RF-08, G-07).
- Desambiguação por **metadados**, nunca pelo modelo.
</requirements>

## Subtarefas

- [x] 4.1 Implementar `Retriever` (embed da pergunta + busca top-K + score).
- [x] 4.2 Aplicar threshold mínimo e marcar `below_threshold` quando nenhum chunk passa.
- [x] 4.3 Suportar filtro `where` por metadados na consulta.
- [x] 4.4 Implementar `ConflictDetector` (agrupamento por `doc_id`, montagem de `ConflictGroup`).

## Detalhes de implementação

Ver techspec **"Visão dos componentes → retrieval/"**, **"Modelos de dados (RetrievalBundle, ConflictGroup)"** e **"Principais decisões → Abstenção por threshold / Desambiguação por metadados"**. Não reproduzir o código — referenciar `techspec-novatech-assistente.md`.

## Critérios de sucesso

- Para perguntas do Anexo B, os chunks-gabarito aparecem no top-N (validação completa em 6.0).
- Pergunta sem cobertura na base resulta em `below_threshold=True`.
- Pergunta sobre o multiplicador regional Sul do PROC-042 retorna `ConflictGroup` com v1 (1.2, mar/2023) e v2 (1.3, nov/2023).

## Testes da tarefa

- [x] Testes unitários — `ConflictDetector`: resultados de PROC-042 v1+v2 → `ConflictGroup` com as duas versões; `Retriever`: `below_threshold` quando scores < min_score; aplicação do filtro `where` (com `EmbeddingProvider` mockado para determinismo).
- [x] Testes de integração — sobre o Anexo A em ChromaDB efêmero: pergunta com cobertura recupera chunk correto; pergunta fora da base marca abstenção; pergunta de frete recupera ambas as versões do PROC-042.
- [x] Testes E2E — N/A no MVP.

## Arquivos relevantes

- `novatech_rag/retrieval/retriever.py`, `conflict_detector.py` (a criar).
- `tests/test_retriever.py`, `tests/test_conflict_detector.py`, `tests/integration/test_retrieval.py` (a criar).
- `anexo-b-chunks-referencia-rag.md` — gabarito.
