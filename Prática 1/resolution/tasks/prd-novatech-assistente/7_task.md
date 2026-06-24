# Tarefa 7.0: CLI (`ingest`/`query`/`eval`) + logging estruturado (JSON)

## Visão geral

Expor o pipeline da PoC como interface de linha de comando (`python -m novatech_rag ingest|query|eval`) e instrumentar o logging estruturado (JSON) exigido para observabilidade do MVP. É o ponto de orquestração que costura ingestão (3.0), retrieval (4.0) e montagem de prompt (5.0), e dispara a avaliação (6.0).

<skills>
### Conformidade com skills

- `code-standards-en` — comandos como verbos, CQS, early return; identificadores em inglês.
- `repo-folder-structure` — CLI como camada de controllers/entrypoint.
- `express-rest-http` — **N/A** (MVP é CLI, sem HTTP; aplicável só ao bot de produção).
</skills>

<requirements>
- Comandos CLI: `ingest <dir>` (indexa Anexo A), `query "<pergunta>"` (recupera + monta e emite o prompt), `eval --gold anexo-b` (roda avaliação).
- `query` emite o prompt montado (para colar no Claude/Ollama) — geração fica fora do pipeline automatizado (`GenerationAdapter` é seam).
- Logging estruturado JSON: por ingestão (nº de docs, chunks gerados, chunks descartados por tamanho); por query (scores de similaridade, `below_threshold`, conflitos detectados, tokens do prompt, latência) — RNF-05/observabilidade MVP.
- Mensagens de erro claras (ex.: falha de download do modelo aborta com mensagem, não degrada em silêncio).
</requirements>

## Subtarefas

- [x] 7.1 Implementar o entrypoint `__main__` e o parser de subcomandos.
- [x] 7.2 Implementar `ingest` (orquestra DocumentLoader→Chunker→Embedding→VectorStore).
- [x] 7.3 Implementar `query` (Retriever→ConflictDetector→PromptAssembler→emite prompt).
- [x] 7.4 Implementar `eval` (dispara RetrievalEvaluator + GuardrailSuite, escreve relatório).
- [x] 7.5 Implementar logging estruturado JSON nos três comandos.

## Detalhes de implementação

Ver techspec **"Endpoints da API → MVP (CLI)"** e **"Monitoramento e observabilidade → MVP"**. Não reproduzir o código — referenciar `techspec-novatech-assistente.md`.

## Critérios de sucesso

- `ingest` indexa o Anexo A e loga nº de docs/chunks; `query` retorna o prompt montado com logs de score/tokens/latência; `eval` produz o relatório de 6.0.
- Logs em JANELA JSON parseável (uma linha por evento) com os campos exigidos.
- Pipeline PoC roda localmente sem dependência de serviço pago (RNF-09).

## Testes da tarefa

- [x] Testes unitários — parsing de argumentos dos subcomandos; formatação/campos do log estruturado.
- [x] Testes de integração — `ingest` seguido de `query` sobre o Anexo A em store efêmero produz prompt não-vazio com citação; `eval` gera relatório com recall@N.
- [x] Testes E2E — N/A no MVP (sem frontend; o E2E funcional é o fluxo de integração CLI ingestão→prompt).

## Arquivos relevantes

- `novatech_rag/__main__.py`, `novatech_rag/cli.py`, `novatech_rag/logging.py` (a criar).
- `tests/test_cli.py`, `tests/integration/test_cli_pipeline.py` (a criar).
