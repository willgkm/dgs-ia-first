# Review: Task 5.0 - Camada de prompt (system prompt versionado v1→v2 + PromptAssembler)

**Revisor**: AI Code Reviewer
**Data**: 2026-06-23
**Arquivo da task**: 5_task.md
**Status**: APROVADO

## Resumo

A tarefa entrega a camada de prompt da PoC (Ex. 1.2 + fechamento do pipeline) de
forma completa e aderente aos padrões do projeto. Foram entregues: (a) o system
prompt versionado em português formal (v1 baseline → v2 endurecido pelos
guardrails G-01..G-08), com `CHANGELOG.md` documentando o mapeamento estático vs
dinâmico e a estimativa de tokens (RF-12), a seção de ordem de prioridade entre
fontes (subtarefa 5.2) e a análise crítica v1→v2; (b) a evidência das duas rodadas
de teste no Claude (entregável obrigatório do Ex. 1.2); (c) o `StaticPromptAssembler`,
que implementa o `Protocol` `PromptAssembler` do techspec, respeita o `token_budget`,
descarta os trechos de menor score em `dropped_chunks`, posiciona os maiores scores
nas extremidades, injeta o alerta de conflito (G-07/G-08) e a instrução de abstenção
(G-03).

O código é limpo, segue CQS (`assemble` é puro), usa early return ao exceder o
orçamento, métodos curtos e bem decompostos, identificadores em inglês e conteúdo
de domínio/prompt em português (desvio consciente de política, conforme
`code-standards-en` e `python-conventions`). Verificações executadas, todas verdes:

- `pytest tests/test_prompt_assembler.py -m "not integration" -q` → **10 passed**
- `ruff check novatech_rag/prompt tests/test_prompt_assembler.py tests/integration/test_pipeline_prompt.py` → **All checks passed!**
- `mypy novatech_rag/prompt` → **Success: no issues found**

Todos os requisitos e critérios de sucesso da task foram atendidos. Nenhum problema
crítico ou major. As observações abaixo são apenas minor (otimização/estilo opcional).

## Arquivos Revisados

| Arquivo | Status | Problemas |
|---------|--------|-----------|
| novatech_rag/prompt/assembler.py | ⚠️ Problemas | 2 minor |
| novatech_rag/prompt/__init__.py | ✅ OK | 0 |
| novatech_rag/prompt/system_prompt_v1.md | ✅ OK | 0 |
| novatech_rag/prompt/system_prompt_v2.md | ✅ OK | 0 |
| novatech_rag/prompt/CHANGELOG.md | ✅ OK | 0 |
| tests/test_prompt_assembler.py | ⚠️ Problemas | 1 minor |
| tests/integration/test_pipeline_prompt.py | ✅ OK | 0 |
| tasks/prd-novatech-assistente/evidencias/1.2-respostas-v1-v2.md | ✅ OK | 0 |

## Problemas Encontrados

### 🔴 Problemas Críticos

Nenhum problema crítico encontrado.

### 🟡 Problemas Major

Nenhum problema major encontrado.

### 🟢 Problemas Minor

**1. `_render_block` é computado duas vezes por trecho mantido** — `assembler.py`,
linhas 100, 132 e 150.
Em `_select_within_budget` (linha 132) cada bloco é renderizado para contagem de
tokens; depois, em `assemble` (linha 100), os mantidos são renderizados de novo via
`_order_for_edges(kept)`. É trabalho redundante (renderização + contagem dobradas).
Não afeta a corretude — o número de trechos é pequeno (cap de top-K) — mas pode ser
eliminado memorizando o bloco junto do resultado. Sugestão:

```python
def _select_within_budget(self, results, chunk_budget):
    ranked = sorted(results, key=lambda result: result.score, reverse=True)
    kept: list[tuple[RetrievalResult, str]] = []
    used = 0
    for index, result in enumerate(ranked):
        block = self._render_block(result)
        block_tokens = self._count(block)
        if used + block_tokens > chunk_budget:
            dropped = [r.chunk for r in ranked[index:]]
            return kept, dropped, used
        kept.append((result, block))
        used += block_tokens
    return kept, [], used
```
e ordenar os pares `(result, block)` nas extremidades, reaproveitando `block`.
Opcional — o ganho de performance é desprezível na escala do MVP.

**2. Estimativa de tokens subestima frente a um tokenizer BPE real** —
`assembler.py`, linhas 44 e 54-57.
`estimate_prompt_tokens` conta `\w+|[^\w\s]` (palavras + pontuação), o que tende a
contar menos tokens que um tokenizer BPE (que quebra subpalavras e acentos). O
risco é o orçamento real estourar quando o estimado fica próximo do teto. O design
mitiga isto corretamente: a contagem é injetável (`token_counter`) e o docstring/
CHANGELOG declaram explicitamente que a produção fornece o tokenizer exato e que o
default é apenas uma aproximação determinística. Aceitável para o MVP; registrado
apenas como ciência do trade-off.

**3. `test_lowest_scores_are_dropped_when_budget_is_tight` depende de blocos de
tamanho uniforme** — `tests/test_prompt_assembler.py`, linhas 72-89.
O teste deriva `block_tokens = (full - base) // 3` assumindo que os três blocos têm
o mesmo custo em tokens. Isso só é verdade porque os textos (`"alfa " * 15` etc.)
têm a mesma contagem e os metadados são idênticos — uma premissa implícita e
frágil a futuras mudanças no cabeçalho de proveniência. O teste passa e valida o
comportamento certo (descarta o menor score, mantém os dois maiores); apenas se
recomenda um comentário explicitando a premissa de uniformidade, ou construir os
trechos com tamanho garantidamente igual de forma explícita.

## ✅ Destaques Positivos

- **Aderência fiel ao techspec e ao `Protocol`.** A assinatura
  `assemble(question, bundle, token_budget) -> AssembledPrompt` e o shape de
  `AssembledPrompt` (`system`, `context_blocks`, `question`, `estimated_tokens`,
  `dropped_chunks`) batem exatamente com o contrato definido no techspec.
- **CQS e early return aplicados corretamente** (`code-standards-en`): `assemble` é
  puro, levanta `ValueError` antecipado quando o orçamento não cobre system+pergunta,
  métodos curtos e decompostos (`_build_directives`, `_conflict_alert`,
  `_select_within_budget`, `_order_for_edges`, `_render_block`).
- **I/O fora do tempo de import** (`python-conventions` Step 3.5):
  `load_system_prompt` usa `pathlib.Path`, não carrega nada no import; o assembler
  recebe o texto já carregado e permanece testável com prompts arbitrários.
- **Ordenação nas extremidades correta** (mitigação *lost in the middle*): a partir
  da lista descendente por score, os maiores ficam nas duas bordas e os menores no
  meio — verificado por `test_highest_scores_sit_at_the_edges`.
- **Guardrails do v2 endereçam exatamente as armadilhas do Anexo B**: carga
  perigosa não devolvível (G-05), tier Platinum inexistente (G-06), versões
  divergentes com ambas + alerta (G-07/G-08), citação em formato fixo (G-01),
  abstenção com frase exata (G-03), seção de ordem de prioridade oficial > FAQ.
- **Evidência de IA completa e analítica**: as três perguntas do Ex. 1.2 com
  respostas v1 e v2 lado a lado, análise crítica por guardrail e síntese das
  diferenças de qualidade — atende ao entregável obrigatório.
- **`ConflictGroup.doc_id` consistente** entre `ConflictDetector` (chave-base
  `PROC-042`) e o alerta renderizado pelo assembler, garantindo que o teste de
  integração e a injeção do alerta concordem.
- **Suíte de testes específica e em AAA**: nomes descritivos, asserções no valor e
  na razão (`bundle.below_threshold is True`), casos de borda (orçamento
  insuficiente, nenhum drop, fonte não oficial sinalizada). Integração fecha o
  pipeline ingestão→retrieval→prompt sobre o Anexo A com `tmp_path` efêmero e marker
  `integration` registrado.

## Conformidade com Padrões

| Padrão | Status |
|--------|--------|
| Padrões de Código (code-standards-en) | ✅ |
| Python (python-conventions) | ✅ |
| RAG pipeline (rag-pipeline) | ✅ |
| REST/HTTP | N/A |
| Logging | N/A |
| React | N/A |
| Testes (pytest-testing) | ✅ |

## Recomendações

1. (Opcional) Eliminar a dupla renderização de `_render_block` memorizando o bloco
   já renderizado em `_select_within_budget` (Minor #1).
2. (Opcional) Documentar/garantir explicitamente a premissa de uniformidade de
   tokens em `test_lowest_scores_are_dropped_when_budget_is_tight` (Minor #3).
3. Manter o `token_counter` injetável e, na migração de produção, plugar o tokenizer
   exato do modelo para que a verificação de teto ≤128K (RNF-06) seja exata e não
   apenas estimada (Minor #2).

## Veredito

**APROVADO.** A implementação está pronta. Todos os requisitos, critérios de
sucesso e testes da task foram cumpridos; os padrões do projeto (incluindo o desvio
consciente de idioma para conteúdo de domínio/prompt) foram respeitados; lint, type
check e testes unitários passam. Os três pontos minor são otimizações/clarezas
opcionais e não bloqueiam a aceitação. Próximo passo natural: a Tarefa 6.0
(`eval/`), que consome este `AssembledPrompt` para a `GuardrailSuite` e o recall@N.
