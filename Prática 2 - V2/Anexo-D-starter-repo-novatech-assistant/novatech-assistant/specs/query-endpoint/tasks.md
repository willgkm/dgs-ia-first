# Tasks — Query Endpoint

> Decomposição do `plan.md` em tasks atômicas (SDD). Cada task é implementável e
> testável de forma independente. Estimativa: **P** (pequena, < ½ dia), **M** (média,
> ~1 dia), **G** (grande, > 1 dia). Rastreabilidade: cada task aponta o passo do plan
> e/ou a ADR de origem.
>
> **Gate (AGENTS.md / Ex. DM 2.1):** Tasks → Implement exige aprovação do Tech Lead
> antes do início. Este `tasks.md` é o artefato submetido a esse gate.

---

## Mapa de dependências

```
T-01 ─┬─> T-05 ─┬─> T-06 ──┐
T-04 ─┘         │          │
T-01 ──────────┴> T-08 ──┐ │
T-02 ─┬─> T-07 ──────────┼─┼─> T-11 ──> T-12
T-04 ─┤   T-09 ──────────┘ │
T-02 ─┘                    │
T-01 ──> T-10 ─────────────┘
T-03 (logger) é dependência transversal de T-06..T-11
```

---

## T-01 — Tipos de domínio e contrato de I/O
- **Descrição:** Definir em `src/shared/types.ts` os tipos do domínio e o contrato do
  endpoint: `QueryRequest` (pergunta + metadados opcionais), `RetrievedChunk`
  (id, texto, `source_document`, seção, vigência), `QueryResponse` (resposta, lista de
  `sources` com `source_document`, flag `low_confidence`).
- **Critérios de aceite:**
  - [ ] `QueryResponse` **obriga** o campo `source_document` em cada item de `sources`.
  - [ ] Tipos exportados e usados por validator/response-builder (sem `any`).
  - [ ] `RetrievedChunk` inclui metadado de vigência (ADR-0003).
- **Dependências:** nenhuma · **Estimativa:** P · **Origem:** plan §5, ADR-0003

## T-02 — Configuração de ambiente validada
- **Descrição:** `src/shared/config.ts` lê e **valida com Zod** as variáveis de ambiente
  (endpoints/keys do Azure OpenAI e Azure AI Search, deployment do GPT-4o, top-K). Falha
  rápida (fail-fast) com mensagem clara se faltar config.
- **Critérios de aceite:**
  - [ ] Variáveis ausentes/ inválidas produzem erro tipado no startup, não em runtime tardio.
  - [ ] Nenhum segredo é logado.
  - [ ] `topK` default = 5 (plan §3).
- **Dependências:** nenhuma · **Estimativa:** P · **Origem:** plan §3, Technical Decisions

## T-03 — Logger estruturado
- **Descrição:** `src/shared/logger.ts` expõe um logger estruturado (pino). Proibido
  `console.log`. Inclui `requestId` por invocação.
- **Critérios de aceite:**
  - [ ] API `logger.info/warn/error(obj, msg)` com saída estruturada.
  - [ ] Nenhuma ocorrência de `console.log` no código de produção.
- **Dependências:** nenhuma · **Estimativa:** P · **Origem:** Technical Decisions (pino)

## T-04 — Custom errors
- **Descrição:** `src/shared/errors.ts` com hierarquia: `AppError` (base, com `statusCode`
  e `code`), `ValidationError` (400), `UpstreamError` (502, para falhas Azure),
  `NotFoundError` (para "sem match"). Mensagem segura para o cliente separada do detalhe interno.
- **Critérios de aceite:**
  - [ ] Cada erro carrega `statusCode` HTTP e `code` estável (string).
  - [ ] Detalhe interno (stack, causa) **não** vaza no corpo da resposta.
- **Dependências:** nenhuma · **Estimativa:** P · **Origem:** plan Technical Decisions

## T-05 — Schema de validação de input (Zod)  ⭐ 1ª task
- **Descrição:** `src/functions/query/validator.ts` define o schema Zod da request
  (`POST /api/query`) e uma função `parseQueryRequest(body): QueryRequest` que lança
  `ValidationError` em entrada inválida.
- **Critérios de aceite:**
  - [ ] `question` obrigatória, string não-vazia após trim.
  - [ ] `question` tem **limite máximo** de caracteres (proteção de custo/anti-injection).
  - [ ] Campos extras desconhecidos são rejeitados (`.strict()`).
  - [ ] Erro de validação mapeia para `ValidationError` (400) com lista de issues legível.
- **Dependências:** T-01 · **Estimativa:** P · **Origem:** plan §1

## T-06 — HTTP trigger + wiring do endpoint  ⭐ 1ª task
- **Descrição:** `src/functions/query/handler.ts` registra o trigger HTTP (Azure Functions
  v4, `app.http`), gera `requestId`, valida o input via T-05, e retorna **400 estruturado**
  em erro de validação. Orquestração de RAG fica para T-11 (aqui retorna 501/stub no happy path).
- **Critérios de aceite:**
  - [ ] `POST /api/query` com body válido passa pela validação sem lançar.
  - [ ] Body inválido retorna **400** com `{ code, message, issues }`, sem stack/segredos.
  - [ ] Usa `logger` (T-03), nunca `console.log`.
  - [ ] Método != POST retorna 405.
- **Dependências:** T-04, T-05 (e T-03) · **Estimativa:** M · **Origem:** plan §1

## T-07 — Service de busca (Azure AI Search, top-5)
- **Descrição:** `src/services/search.ts` — interface `searchChunks(query, topK)` que
  consulta o Azure AI Search e retorna `RetrievedChunk[]`. Inclui **retry com exponential
  backoff**. Implementação isolável por interface (testável com mock).
- **Critérios de aceite:**
  - [ ] Retorna no máx. `topK` chunks (default 5).
  - [ ] Falha de upstream após N retries vira `UpstreamError`.
  - [ ] Mapeia metadado de vigência para `RetrievedChunk` (ADR-0003).
- **Dependências:** T-02, T-04 · **Estimativa:** M · **Origem:** plan §2-3, ADR-0003

## T-08 — Prompt builder com context budget
- **Descrição:** `src/services/prompt-builder.ts` monta o prompt final = system prompt +
  chunks + pergunta, **respeitando o context budget da ADR-0002** (~4K tokens system +
  ~8K chunks). Trunca/seleciona chunks se exceder o orçamento.
- **Critérios de aceite:**
  - [ ] Soma estimada de tokens dos chunks ≤ ~8K; system ≤ ~4K.
  - [ ] Quando há contradição de vigência, prioriza a versão mais recente (ADR-0003).
  - [ ] System prompt é carregado de `/prompts/system-prompt.md` (não hardcoded).
- **Dependências:** T-01 · **Estimativa:** M · **Origem:** plan §4, ADR-0002, ADR-0003

## T-09 — Service de completion (GPT-4o)
- **Descrição:** `src/services/completion.ts` — `complete(prompt): string` via Azure OpenAI
  GPT-4o, com **retry/backoff** e timeout.
- **Critérios de aceite:**
  - [ ] Timeout configurável; falha vira `UpstreamError`.
  - [ ] Não loga conteúdo sensível do prompt em nível info.
- **Dependências:** T-02, T-04 · **Estimativa:** M · **Origem:** plan §5

## T-10 — Response builder com source_document
- **Descrição:** `src/functions/query/response-builder.ts` monta o `QueryResponse`,
  garantindo `source_document` para cada fonte e a flag `low_confidence` quando aplicável.
- **Critérios de aceite:**
  - [ ] 100% das respostas incluem `source_document` por fonte (guardrail de produto).
  - [ ] Sem match → resposta padrão "não encontrado" (não inventa).
- **Dependências:** T-01 · **Estimativa:** P · **Origem:** plan §5

## T-11 — Orquestração no handler
- **Descrição:** Conectar no `handler.ts` o fluxo completo: validar → `searchChunks` →
  `buildPrompt` → `complete` → `buildResponse`. Tratar erros por tipo (400/502/timeout).
- **Critérios de aceite:**
  - [ ] Happy path retorna 200 com `QueryResponse` válido (com `source_document`).
  - [ ] Erros de upstream retornam 502; validação 400; sem match resposta padrão.
- **Dependências:** T-06, T-07, T-08, T-09, T-10 · **Estimativa:** M · **Origem:** plan §1-5

## T-12 — Testes de integração do endpoint
- **Descrição:** `tests/integration/query-endpoint.test.ts` (Vitest) com mocks de Search e
  OpenAI (sem serviços reais). Casos: input válido (happy path), input inválido (400),
  sem match (resposta padrão), upstream falha (502).
- **Critérios de aceite:**
  - [ ] ≥1 caso happy path e ≥1 edge case por comportamento crítico.
  - [ ] Nenhum acesso a serviço real; dados de teste do domínio de logística (fixtures).
- **Dependências:** T-06 (mín.), idealmente T-11 · **Estimativa:** M · **Origem:** plan, VC do requirements

---

## Escopo desta entrega (Ex. 2.2 + P1)
Implementadas: **T-01, T-03, T-04, T-05, T-06** (1ª task — setup do endpoint com validação de
input) e **T-12** (testes de integração da 1ª task). As tasks **T-07…T-11** ficam para
iterações seguintes (dependem de Azure real / pipeline de ingestão).

| Task | Status |
|------|--------|
| T-01, T-03, T-04, T-05, T-06 | ✅ implementadas |
| T-12 | ✅ testes da 1ª task (8 casos) — `tsc` exit 0, `vitest` 8/8 |
| T-07, T-08, T-09, T-10, T-11 | ⬜ pendentes (Azure/pipeline) |

## Nota de dependências de build (P1 — modo offline encerrado)
`@azure/functions` (v4), `pino` e `zod` (movido de devDependencies → **dependencies**) estão
instalados; `@types/node` em devDependencies. O type-shim offline foi **removido** e o trigger
foi separado da lógica (`index.ts` registra `app.http`; `handler.ts` exporta `queryHandler`)
para manter o handler testável. Dívida residual conhecida: vulnerabilidades **dev-only** em
`esbuild`/`vite` (transitivas do Vitest) — correção exige Vitest 4 (breaking).
