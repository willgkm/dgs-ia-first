# Tarefa 5.0: Camada de prompt — system prompt versionado (v1→v2) + PromptAssembler

## Visão geral

Entrega combinada do Ex. 1.2 e do fechamento do pipeline da PoC:
(a) escrever e versionar o **system prompt** (identidade, regras/guardrails, formato de resposta, instruções de uso de chunks), com mapeamento de partes estáticas vs dinâmicas e estimativa de tokens, iterando de v1 para v2 com análise crítica;
(b) implementar o **`PromptAssembler`** que compõe system prompt estático + chunks dinâmicos (maior score nas extremidades) + pergunta, respeitando o orçamento de tokens e injetando o alerta de conflito quando o `ConflictDetector` apontar divergência.

<skills>
### Conformidade com skills

- `code-standards-en` — `PromptAssembler.assemble`, `AssembledPrompt`; CQS, early return ao exceder orçamento, métodos curtos. **Identificadores em inglês; conteúdo do system prompt em português formal** (política de produto, G-04).
- `repo-folder-structure` — módulo `prompt/` (camada services); system prompt versionado como artefato de código.
- `context7`, `express-rest-http`, `skill-best-practices` — N/A.
</skills>

<requirements>
- System prompt v1 com seções: identidade, regras de comportamento (guardrails G-01..G-08), formato de resposta e instruções de uso dos chunks; em português formal (G-04).
- **Definir explicitamente a ordem de prioridade entre fontes em caso de conflito** (exigência do Ex. 1.2): documento oficial (`is_official=true`) tem precedência sobre o FAQ não-validado; versões divergentes do mesmo documento (ex.: PROC-042 v1 vs v2) não são resolvidas pelo modelo — ambas são apresentadas com alerta (G-07/G-08). Registrar essa regra como seção própria do system prompt.
- Mapear partes **estáticas** (system prompt/guardrails) vs **dinâmicas** (chunks, pergunta, histórico) e estimar tokens de cada parte (RF-12).
- Testar v1 com as 3 perguntas do Ex. 1.2 (devolução de carga perigosa; SLA do cliente Gold; frete de 600kg para Manaus); analisar correção, citação e aderência a guardrails; iterar para v2 e documentar as diferenças.
- **Capturar a evidência de uso de IA (entregável obrigatório do Ex. 1.2):** salvar as respostas da 1ª rodada (v1) e da 2ª rodada (v2) obtidas no Claude, com a análise crítica de cada uma.
- `PromptAssembler.assemble(question, bundle, token_budget)`: ordena chunks (maior score nas bordas), respeita `token_budget` (≤128K) descartando menor score (`dropped_chunks`), e injeta alerta de conflito quando há `ConflictGroup` (RF-04, RF-05, RF-08, RNF-06, G-01/G-07/G-08).
- Quando `bundle.below_threshold`, o prompt instrui resposta de "não encontrado" + escalada (G-03).
- Versionar v1 e v2 no repositório com registro de motivação das mudanças.
</requirements>

## Subtarefas

- [x] 5.1 Escrever system prompt v1 (seções + guardrails em português formal).
- [x] 5.2 Definir a seção de ordem de prioridade entre fontes (oficial > FAQ; versões divergentes → ambas + alerta).
- [x] 5.3 Mapear partes estáticas/dinâmicas e estimar tokens de cada parte.
- [x] 5.4 Testar v1 com as 3 perguntas e registrar a análise crítica.
- [x] 5.5 Iterar para v2, documentando diferenças e motivação; versionar v1 e v2.
- [x] 5.6 Salvar as respostas das duas rodadas (v1/v2) como evidência de uso de IA.
- [x] 5.7 Implementar `PromptAssembler` (ordenação nas extremidades + orçamento + `dropped_chunks`).
- [x] 5.8 Injetar alerta de conflito (G-07/G-08) e instrução de abstenção (G-03) no prompt montado.

## Detalhes de implementação

Ver techspec **"Visão dos componentes → prompt/"**, **"Modelos de dados (AssembledPrompt)"** e **"Principais decisões → Prompt estático vs dinâmico + ordenação nas extremidades"**; PRD **UC-05** e **Guardrails G-01..G-08**. Não reproduzir o conteúdo completo — referenciar `techspec-novatech-assistente.md`.

## Critérios de sucesso

- Repositório contém system prompt v1 e v2 com mapeamento estático/dinâmico e estimativa de tokens documentados (RF-12).
- System prompt contém seção explícita de ordem de prioridade entre fontes (oficial > FAQ; conflito de versões → ambas + alerta).
- Evidência das duas rodadas de teste no Claude (respostas v1 e v2 + análise) salva no repositório.
- Prompt montado nunca excede o `token_budget`; chunks descartados são os de menor score e ficam registrados em `dropped_chunks` (RF-04).
- Maiores scores posicionados no início e no fim do contexto.
- Bundle com `ConflictGroup` (PROC-042) gera prompt com alerta de divergência; bundle `below_threshold` gera prompt com instrução de abstenção/escalada.

## Testes da tarefa

- [x] Testes unitários — `PromptAssembler`: respeita `token_budget` (descarta menor score), posiciona maiores scores nas extremidades, injeta alerta de conflito quando há `ConflictGroup`, e instrução de abstenção quando `below_threshold`. Sem mock de LLM (o MVP não chama LLM); mock apenas de `EmbeddingProvider` quando necessário.
- [x] Testes de integração — pipeline ingestão→retrieval→prompt sobre o Anexo A: o prompt montado para PROC-042 contém as duas versões + alerta; o prompt para pergunta fora da base contém a instrução de "não encontrado".
- [x] Testes E2E — N/A no MVP (geração é manual/Ollama, fora do pipeline automatizado).

## Arquivos relevantes

- `novatech_rag/prompt/assembler.py` (a criar).
- `novatech_rag/prompt/system_prompt_v1.md`, `system_prompt_v2.md` (a criar) + `prompt/CHANGELOG.md` com análise v1→v2.
- `resolution/tasks/prd-novatech-assistente/evidencias/1.2-respostas-v1-v2.md` (a criar) — respostas das duas rodadas no Claude + análise.
- `tests/test_prompt_assembler.py`, `tests/integration/test_pipeline_prompt.py` (a criar).
