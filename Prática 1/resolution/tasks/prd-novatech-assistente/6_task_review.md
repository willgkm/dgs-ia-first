# Review: Task 6.0 - Avaliação: RetrievalEvaluator (recall@N) + GuardrailSuite (LLM-as-judge)

**Revisor**: AI Code Reviewer
**Data**: 2026-06-23
**Arquivo da task**: 6_task.md
**Status**: APROVADO COM OBSERVAÇÕES

## Resumo

A tarefa entrega a suíte de avaliação do Ex. 1.3 de forma completa e de alta qualidade. O `RetrievalEvaluator` mede recall@N (recall médio e taxa de cobertura) contra o gabarito do Anexo B; a `GuardrailSuite` executa os casos-armadilha (Platinum/G-06, carga perigosa/G-05, PROC-042/G-07-G-08, fora-da-base/G-03, citação/G-01) na camada determinística; o `llm_judge` define a rubrica (precisão/citação/aderência) tratando a geração como grau, não pass/fail. O `report.py` gera o relatório versionado com os ≥2 problemas exigidos e correções propostas, e a evidência 1.3 documenta as 5 perguntas com chunks/scores/comparação ao gabarito + respostas avaliadas.

A arquitetura segue fielmente as skills do projeto: módulos puros (CQS), `typing.Protocol` para o `Judge`, dataclasses `frozen`, identificadores em inglês com conteúdo de domínio em português, e a separação determinístico vs não-determinístico recomendada por `references/guardrails.md`. Verificações executadas: **120 testes unitários passam**, **4 testes de integração passam** (confirmando recall@5 ≥80%, críticos 100%, abstenção 10/10), **ruff** e **mypy** limpos em `novatech_rag/eval` e nos testes. Os resultados de homologação informados procedem.

Há uma observação MAJOR (parâmetro/atributo morto na `GuardrailSuite`) e algumas observações MINOR de DRY, nenhuma bloqueante.

## Arquivos Revisados

| Arquivo | Status | Problemas |
|---------|--------|-----------|
| novatech_rag/eval/anexo_b_gold.py | ✅ OK | 0 |
| novatech_rag/eval/retrieval_evaluator.py | ✅ OK | 0 |
| novatech_rag/eval/llm_judge.py | ⚠️ Problemas | 1 minor |
| novatech_rag/eval/guardrail_suite.py | ⚠️ Problemas | 1 major |
| novatech_rag/eval/report.py | ⚠️ Problemas | 1 minor |
| novatech_rag/eval/__init__.py | ✅ OK | 0 |
| tests/test_retrieval_evaluator.py | ✅ OK | 0 |
| tests/test_llm_judge.py | ✅ OK | 0 |
| tests/integration/test_guardrails.py | ✅ OK | 0 |
| reports/eval-report.json | ✅ OK | 0 |
| tasks/.../evidencias/1.3-teste-5-perguntas.md | ✅ OK | 0 |

## Problemas Encontrados

### 🔴 Problemas Críticos

Nenhum problema crítico encontrado.

### 🟡 Problemas Major

**M1 — Parâmetro/atributo `grounded_min_score` é morto (`guardrail_suite.py:113-118`, `130-131`, `140-141`).**

O construtor da `GuardrailSuite` recebe e armazena `grounded_min_score` (default `MIN_SCORE`):

```python
def __init__(self, retriever, assembler, abstain_min_score=ABSTAIN_OPERATING_SCORE,
             grounded_min_score=MIN_SCORE) -> None:
    ...
    self._grounded_min_score = grounded_min_score   # nunca é lido
```

Porém `_check_grounded` e `_check_conflict` passam `min_score=0.0` literal ao `retrieve`, nunca `self._grounded_min_score`. O atributo é atribuído e jamais consumido (confirmado por busca). Funcionalmente é inofensivo — os casos *grounded* propositalmente recuperam sem threshold para verificar se o doc-gabarito aparece no top-N —, mas o parâmetro cria uma API enganosa: um chamador que ajustasse `grounded_min_score` não teria efeito algum. O ruff não sinaliza atributos de instância, por isso passou no lint.

*Correção sugerida (escolher uma):*
1. Remover o parâmetro e o atributo, e manter `0.0` como constante nomeada (ex.: `_GROUNDED_NO_THRESHOLD = 0.0`) deixando explícito que *grounded* avalia presença no ranking, não corte por score; ou
2. Efetivamente usar `min_score=self._grounded_min_score` se a intenção for aplicar o threshold (não recomendado aqui, pois mudaria a semântica do teste de cobertura).

### 🟢 Problemas Minor

**m1 — Pesos da rubrica duplicados em `report.py:84` em vez de reusar `RUBRIC_WEIGHTS`.**

```python
"weights": {"precision": 0.4, "citation": 0.3, "guardrail_adherence": 0.3},
```

`llm_judge.RUBRIC_WEIGHTS` já é a fonte única desses valores e é exportado no `__init__`. Replicar o literal arrisca divergência futura. Sugestão: `from .llm_judge import RUBRIC_WEIGHTS` e `"weights": dict(RUBRIC_WEIGHTS)`.

**m2 — Lógica de dedupe de `doc_id` duplicada entre dois módulos.**

`RetrievalEvaluator._ordered_doc_ids` (`retrieval_evaluator.py:85-91`) e `GuardrailSuite._doc_ids` (`guardrail_suite.py:178-183`) implementam o mesmo "deduplica doc_ids preservando ordem". Poderia ser um helper compartilhado (ex.: em `anexo_b_gold.py` ou um pequeno util de eval). Custo baixo; não bloqueia.

**m3 — `aggregate_rubric` aceita `weights` parametrizável mas referencia chaves fixas (`llm_judge.py:70-80`).**

A assinatura sugere pesos arbitrários, porém o corpo acessa `weights["precision"]`/`["citation"]`/`["guardrail_adherence"]` diretamente; um dicionário com chaves diferentes levanta `KeyError`. Como o único uso é o default `RUBRIC_WEIGHTS`, é aceitável, mas a flexibilidade aparente é ilusória. Sugestão: iterar sobre `score._criteria()` ponderando pelos pesos correspondentes, ou documentar que as chaves são fixas.

## ✅ Destaques Positivos

- **Separação determinístico × não-determinístico** exemplar: a camada de retrieval/prompt é asserção direta (`GuardrailSuite`) e a geração é grau de rubrica (`llm_judge`), exatamente como `references/guardrails.md` e `pytest-testing` Etapa 4 prescrevem. O `Judge` é um `Protocol` não exercitado nos testes — o seam produção/humano está corretamente isolado.
- **Pureza/CQS** consistente: `evaluate`, `run`, `aggregate_rubric`, `build_eval_report` são puros; o I/O fica isolado em `write_eval_report`. `RubricScore` valida o intervalo `[0,1]` em `__post_init__`.
- **Mapeamento robusto de rótulos** em `chunk_label_to_doc_id`: a ordem `PROC-042v2` antes de `PROC-042` evita a confusão entre versão revisada e original — armadilha real do Anexo B — e há teste dedicado para isso.
- **Métrica de homologação correta**: distinguir `coverage_ratio` (todos os docs esperados no top-N — métrica de meta ≥80%) de `mean_recall` é a leitura certa do critério RF-03; perguntas de abstenção são excluídas do recall e avaliadas à parte.
- **Cobertura de testes alinhada às subtarefas**: parsing do gabarito sobre o arquivo real, recall sintético (acerto/parcial/erro/top-N excedido), agregação da rubrica e os casos-armadilha como testes individualmente nomeados na integração (críticos, conflito+alerta, abstenção ≥9/10).
- **Calibração honesta da abstenção**: `ABSTAIN_OPERATING_SCORE = 0.55` é uma constante nomeada com justificativa documentada (limitação do modelo anglófono), e o trade-off recall × abstenção é analisado na evidência 1.3 e no problema P3 — não é número mágico escondido.
- **Evidência 1.3 e `eval-report.json`** completos e coerentes entre si: 5 perguntas com chunks/scores/comparação ao gabarito, respostas do Claude avaliadas por critério, e ≥2 problemas (3 entregues) com raiz comum bem identificada e correções acionáveis ligadas à arquitetura-alvo.

## Conformidade com Padrões

| Padrão | Status |
|--------|--------|
| Padrões de Código (code-standards-en) | ✅ |
| Python (python-conventions: Protocol, dataclasses, type hints, paths) | ✅ |
| RAG pipeline (recall@N / guardrails / determinístico vs grau) | ✅ |
| Testes (pytest-testing) | ✅ |
| Lint / Type check (ruff + mypy) | ✅ |
| Idioma (identificadores en / conteúdo pt) | ✅ |

## Recomendações

1. (MAJOR) Remover `grounded_min_score` da `GuardrailSuite` ou passá-lo de fato a `retrieve`; preferir a remoção com uma constante nomeada para o `0.0`, deixando explícita a semântica de "cobertura no top-N".
2. (MINOR) Reusar `RUBRIC_WEIGHTS` em `report.py` em vez de replicar o literal dos pesos.
3. (MINOR) Extrair o dedupe de `doc_id` preservando ordem para um único helper compartilhado.
4. (MINOR) Tornar `aggregate_rubric` coerente com sua assinatura (iterar critérios) ou documentar chaves fixas.

## Veredito

**APROVADO COM OBSERVAÇÕES.** Todos os requisitos e critérios de sucesso da task foram atendidos e verificados: recall@5 = 88,9% (≥80%), guardrails críticos 100%, abstenção 10/10, relatório versionado com 3 problemas + correções, e a evidência obrigatória das ≥5 perguntas. Os testes (unitários e integração), o ruff e o mypy passam. As observações são de qualidade interna e não bloqueantes; recomenda-se tratar a M1 (atributo morto) numa próxima iteração para evitar API enganosa. Código apto a seguir.
