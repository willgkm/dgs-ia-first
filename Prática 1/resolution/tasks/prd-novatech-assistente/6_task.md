# Tarefa 6.0: Avaliação — RetrievalEvaluator (recall@N) + GuardrailSuite (LLM-as-judge)

## Visão geral

Implementar a suíte de avaliação que produz as evidências de homologação do Ex. 1.3: `RetrievalEvaluator` mede recall@N contra o mapa de cobertura do Anexo B, e `GuardrailSuite` executa os casos-armadilha (Platinum, carga perigosa, PROC-042, pergunta fora da base) avaliando a geração por LLM-as-judge com rubrica. Valida as tarefas 3.0–5.0.

<skills>
### Conformidade com skills

- `code-standards-en` — `RetrievalEvaluator`, `GuardrailSuite`; funções verbais, CQS, métodos curtos.
- `repo-folder-structure` — módulo `eval/`.
- `context7`, `express-rest-http`, `skill-best-practices` — N/A.
</skills>

<requirements>
- `RetrievalEvaluator`: para cada pergunta do Anexo B, verificar se os chunks-gabarito aparecem no top-N; reportar recall@N agregado (meta ≥80% — RF-03, critério de homologação).
- `GuardrailSuite` com os casos-armadilha:
  - **Platinum** (G-06): tier inexistente → abstenção/declaração de ausência.
  - **Carga perigosa** (G-05): POL-001 §3.2 → NÃO pode ser devolvida (não inverter a exceção).
  - **PROC-042** (G-07/G-08): exige ambas as versões + alerta de divergência.
  - **Pergunta fora da base** (G-03): abstém e recomenda escalada (≥9/10).
  - **Citação de fonte** (G-01): presença do documento de origem na resposta.
- Avaliação de geração por **LLM-as-judge** com rubrica (precisão, citação, aderência a guardrail), tratando como grau de qualidade (não pass/fail binário) e reconhecendo o não-determinismo.
- Relatório de `eval` versionado (recall@N, taxa de abstenção correta, violações de guardrail).
- **Relatório de teste das ≥5 perguntas (entregável obrigatório do Ex. 1.3):** para cada pergunta, documentar os chunks recuperados, o score de similaridade e a comparação com o gabarito do Anexo B (chunk correto sim/não).
- **Capturar a evidência de uso de IA (Ex. 1.3):** salvar o prompt montado colado no Claude e a resposta obtida, com a avaliação (correção, citação de fonte, aderência a guardrails).
</requirements>

## Subtarefas

- [x] 6.1 Carregar o gabarito do Anexo B e implementar `RetrievalEvaluator` (recall@N).
- [x] 6.2 Implementar o conjunto de casos-armadilha do `GuardrailSuite`.
- [x] 6.3 Implementar o LLM-as-judge com rubrica (precisão/citação/guardrail).
- [x] 6.4 Documentar o teste das ≥5 perguntas (chunks recuperados + scores + comparação ao gabarito).
- [x] 6.5 Colar o prompt montado no Claude, salvar a resposta e avaliá-la (correção/citação/guardrails).
- [x] 6.6 Gerar relatório de avaliação versionado (JSON + resumo legível).
- [x] 6.7 Identificar ≥2 problemas (chunk errado, tabela cortada, doc irrelevante no topo) e propor correções (Ex. 1.3).

## Detalhes de implementação

Ver techspec **"Abordagem de testes → Testes de integração / Suite de guardrails"** e **"eval/"**; PRD **"Métricas de sucesso"**, **"Critérios de aceitação"** e **Guardrails G-01..G-08**. O LLM-judge pode usar Claude/Ollama; reconhecer a natureza não-determinística (graus, não binário). Não reproduzir rubrica completa — referenciar `techspec-novatech-assistente.md`.

## Critérios de sucesso

- recall@N ≥ 80% nas perguntas do Anexo B.
- Casos-armadilha (Platinum, carga perigosa, PROC-042) corretos em 100% — zero alucinações críticas pré go-live.
- Em 10 perguntas sem resposta na base, abstenção + escalada em ≥9.
- Relatório de avaliação versionado com ≥2 problemas identificados e correções propostas.

## Testes da tarefa

- [x] Testes unitários — cálculo de recall@N com casos sintéticos (acerto/erro); parsing do gabarito do Anexo B; agregação da rubrica do judge.
- [x] Testes de integração — execução da `GuardrailSuite` sobre o pipeline real (Anexo A indexado): asserções determinísticas no retrieval/prompt (ex.: PROC-042 traz ambas as versões; Platinum marca `below_threshold`/abstenção) e avaliação de geração por LLM-judge na camada não-determinística.
- [x] Testes E2E — N/A no MVP (o "E2E funcional" é ingestão→prompt + julgamento da resposta).

## Arquivos relevantes

- `novatech_rag/eval/retrieval_evaluator.py`, `guardrail_suite.py`, `llm_judge.py` (a criar).
- `tests/test_retrieval_evaluator.py`, `tests/integration/test_guardrails.py` (a criar).
- `anexo-b-chunks-referencia-rag.md` — gabarito de recall@N.
- `reports/eval-report.json` (a gerar) — evidências versionadas.
- `resolution/tasks/prd-novatech-assistente/evidencias/1.3-teste-5-perguntas.md` (a criar) — chunks/scores vs gabarito + resposta do Claude avaliada.
