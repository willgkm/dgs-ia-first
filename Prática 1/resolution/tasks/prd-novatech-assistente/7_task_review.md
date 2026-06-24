# Review: Task 7.0 - CLI (`ingest`/`query`/`eval`) + logging estruturado (JSON)

**Revisor**: AI Code Reviewer
**Data**: 2026-06-23
**Arquivo da task**: 7_task.md
**Status**: APROVADO

## Resumo

A tarefa expõe o pipeline da PoC como CLI (`python -m novatech_rag ingest|query|eval`) e instrumenta o logging estruturado JSON exigido pela observabilidade do MVP (RNF-05). A implementação está aderente: `cli.py` atua como camada de controllers/entrypoint que apenas costura componentes já existentes (loader → chunker → embeddings → store; retriever → assembler; eval/report) sem reimplementar lógica de domínio, exatamente como pede o techspec ("não reproduzir o código — referenciar"). O logging é minimalista e correto — uma linha JSON por evento, separação limpa entre logs (stderr) e o prompt montado (stdout), e configuração idempotente sem I/O em tempo de import. Os três comandos emitem precisamente os campos exigidos pelo techspec (seção "Monitoramento e observabilidade → MVP", linha 134).

Qualidade geral alta: identificadores em inglês com conteúdo/mensagens em português (política consciente do projeto), funções curtas e com verbo, CQS respeitado, early returns, captura de exceções restrita a um conjunto explícito de erros recuperáveis. ruff, mypy e os testes unitários passam de forma independente nesta revisão (7 passed). Não foram encontrados problemas críticos nem major.

## Arquivos Revisados

| Arquivo | Status | Problemas |
|---------|--------|-----------|
| novatech_rag/cli.py | ✅ OK | 2 minor |
| novatech_rag/logging.py | ✅ OK | 0 |
| novatech_rag/__main__.py | ✅ OK | 0 |
| tests/test_cli.py | ✅ OK | 1 minor |
| tests/integration/test_cli_pipeline.py | ✅ OK | 0 |

## Problemas Encontrados

### 🔴 Problemas Críticos

Nenhum problema crítico encontrado.

Verificações específicas realizadas:
- **Colisão com o `logging` da stdlib**: confirmado que NÃO há colisão problemática. `novatech_rag/logging.py` usa `from __future__ import annotations` + `import logging` (import absoluto), e graças aos imports absolutos do Python 3 o `import logging` resolve para o módulo padrão, não para o próprio módulo. mypy e o runtime confirmam (`logging.Formatter`, `logging.getLogger`, `logging.INFO` resolvem corretamente).
- **Tipos `any`**: nenhum uso de `Any` introduzido nos arquivos da task. O único `Any` do projeto está em `embeddings.py` (fora desta task).
- **Tratamento de erro**: `main()` captura apenas `_RECOVERABLE_ERRORS` (lista explícita) e loga `command_failed`; erros inesperados propagam — alinhado a python-conventions ("catch only the specific exceptions a step can recover from"). Falha de download do modelo vira `EmbeddingModelError`, que está na lista e aborta com log claro (não degrada em silêncio), atendendo ao requisito.

### 🟡 Problemas Major

Nenhum problema major encontrado.

### 🟢 Problemas Minor

1. **`cli.py:58` — comprimento de linha do `description` do parser.** A linha do `argparse.ArgumentParser(...)` e as definições de `--persist-dir`/`--collection` cabem no limite configurado do ruff (passou), mas algumas linhas (ex.: 58-62) misturam string longa em português com chamada. Sugestão opcional de estilo: extrair textos de help longos para constantes nomeadas em português, mantendo a chamada mais enxuta. Não bloqueante — ruff/format já aprovam.

2. **`cli.py:124-146` — `_run_query` mede latência apenas do par `retrieve + assemble`.** O `time.perf_counter()` envolve só retrieval + montagem, excluindo a carga preguiçosa do modelo de embeddings (`_build_embeddings`) que ocorre antes. Isso é defensável (a latência de retrieval/montagem é a métrica de runtime relevante e o carregamento do modelo é custo de cold-start), mas vale documentar a fronteira no log/docstring para não confundir leitura operacional. Correção sugerida (opcional): renomear o campo de `latency_seconds` para `retrieval_latency_seconds` ou anotar o escopo num comentário curto.

3. **`tests/test_cli.py:13` — os testes importam handlers privados (`_run_eval`, `_run_ingest`, `_run_query`).** Os testes asseguram que o parser liga cada subcomando ao handler certo (`args.handler is _run_ingest`), o que é uma asserção forte e correta; o custo é acoplar o teste a símbolos privados (`_`-prefixados). Aceitável aqui porque o objetivo é justamente verificar o roteamento do `set_defaults(handler=...)` sem executar o pipeline real. Sem ação necessária.

## ✅ Destaques Positivos

- **Separação de canais correta**: logs JSON em `sys.stderr` e o prompt montado em `sys.stdout` (`print(_render_prompt(...))`), permitindo `... query "..." 2>logs.json` sem misturar saída para colar no Claude/Ollama. Excelente para o uso operacional descrito na task.
- **`log_event` determinístico e parseável**: `json.dumps(..., ensure_ascii=False, sort_keys=True)` numa única linha por evento. `ensure_ascii=False` preserva acentuação portuguesa; `sort_keys=True` dá saída estável (bom para diffs/testes). Atende literalmente "uma linha por evento, JSON parseável".
- **Cobertura exata dos campos do techspec**: `ingest_done` loga `documents`/`chunks`/`oversized_chunks`; `query_done` loga `scores`/`below_threshold`/`conflicts`/`prompt_tokens`/`latency_seconds`; `eval_done` loga recall e guardrails. Mapeia 1:1 com a linha 134 do techspec.
- **CLI como controller fino**: nenhuma regra de domínio reimplementada; reusa `ingest_documents`, `SimilarityRetriever`, `StaticPromptAssembler`, `build_eval_report`/`write_eval_report`. Respeita repo-folder-structure (controllers → services → data) e mantém o módulo abaixo dos limites de tamanho.
- **`configure_json_logging` idempotente** (remove handlers antes de adicionar; `propagate=False`), com teste dedicado garantindo handler único — evita logs duplicados quando a CLI roda múltiplas vezes no mesmo processo (relevante para os testes de integração que chamam `main` em sequência).
- **Validação de entrada com early return e log de causa**: `_run_ingest` (`directory_not_found`) e `_run_eval` (`gold_not_found`) verificam o caminho antes de carregar o modelo, retornando 1 com motivo logado — falha rápida e barata.
- **Teste de integração é o "E2E funcional" do MVP**: `ingest → query` valida prompt não-vazio com citação (`POL-001`), out-of-base emite prompt sem erro, e `eval` valida `target_met`/`critical_all_passed` com `importorskip` para chromadb/sentence-transformers e marcador `integration` — exatamente o previsto em pytest-testing e na task.

## Conformidade com Padrões

| Padrão | Status |
|--------|--------|
| Padrões de Código (code-standards-en) | ✅ |
| Python (python-conventions) | ✅ |
| REST/HTTP | N/A (MVP é CLI, sem HTTP) |
| Logging | ✅ |
| React | N/A |
| Testes (pytest-testing) | ✅ |

Notas de conformidade:
- **code-standards-en**: comandos como verbos (`_run_ingest`, `build_parser`), CQS (handlers retornam exit code; `log_event`/`print` são efeitos isolados), early returns, sem números mágicos (constantes `_EVAL_TOP_N`, `_DEFAULT_*`), funções < 50 linhas, módulo < 300 linhas. Identificadores em inglês; textos ao usuário e domínio em português — desvio consciente documentado.
- **python-conventions**: Python 3.10+ (`list[str] | None`), type hints completos, `pathlib.Path`, exceções explícitas, sem side effects de import. mypy limpo.
- **pytest-testing**: AAA, nomes descritivos, marcador `integration` registrado, asserções específicas (valor + razão), determinismo nos unitários (sem modelo real; logging em `io.StringIO`), recursos efêmeros via `tmp_path`.

## Recomendações

1. (Minor, opcional) Anotar/renomear o escopo da métrica de latência em `query_done` para deixar claro que mede retrieval + montagem, não o cold-start do modelo.
2. (Minor, opcional) Extrair os textos de `help` mais longos do `argparse` para constantes nomeadas, mantendo as chamadas do parser mais enxutas.
3. (Acompanhamento, não-bloqueante) Considerar um teste unitário leve para o caminho de erro de `main()` (ex.: `_RECOVERABLE_ERRORS` capturada → retorna 1 e loga `command_failed`), usando um handler fake que levanta `ValueError`. O comportamento já é coberto indiretamente, mas um teste direto fixaria o contrato.

## Veredito

APROVADO. A implementação cumpre integralmente os requisitos e critérios de sucesso da Task 7.0: os três comandos funcionam, o logging JSON é parseável (uma linha por evento) com todos os campos exigidos pelo techspec, a separação stdout/stderr viabiliza o uso operacional, e o pipeline roda localmente sem serviço pago (RNF-09). Validação independente confirmada (ruff e mypy limpos; `tests/test_cli.py` 7 passed). Não há colisão problemática com o módulo `logging` da stdlib. Os três itens minor são melhorias opcionais e não bloqueiam a aceitação — podem ser endereçados em manutenção futura. Código pronto para seguir.
