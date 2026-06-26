# Revisão crítica — 1ª task do Query Endpoint (Ex. 2.2)

> Revisão do código gerado para **T-05 (validator)** + **T-06 (handler)** e fundamentos
> de apoio (T-01/T-03/T-04). Objetivo: apontar problemas **reais** que precisariam de
> ajuste antes de um code review/merge de verdade. Itens marcados **[BLOQUEIA]** deveriam
> travar o merge; **[DISCUTIR]** são decisões de design a alinhar com TL/PS.

## Verificação executada
- ✅ Sem `console.*` no código de produção (logging via `pino`).
- ✅ Imports/exports coerentes entre `handler → validator → errors/logger/types`.
- ✅ **`npx tsc --noEmit` → exit 0** (compila sob `strict`). _(P1: deps instaladas)_
- ✅ **`npx vitest run` → 8/8 testes passando** (`tests/integration/query-endpoint.test.ts`).

> **Atualização (P1):** o modo offline foi encerrado — `@azure/functions`, `pino`, `zod`
> (movido para `dependencies`) e `@types/node` instalados; shim removido; código compila e
> testa de verdade. Pontos **1** e **4** abaixo foram **resolvidos**.

---

## Ponto 1 — ✅ RESOLVIDO (P1) — JSON malformado é mascarado como "question obrigatória"
No `handler.ts`, uma falha em `request.json()` cai no `catch` e define `rawBody = undefined`.
A validação então retorna **400 dizendo que `question` é obrigatória** — mesmo quando o
problema real foi um **corpo JSON inválido**. Isso confunde o cliente (atendente/bot) e
dificulta o suporte.

**Ajuste proposto:** distinguir os dois casos — em erro de parse, retornar 400 com
`code: "INVALID_JSON"` e mensagem específica ("Corpo da requisição não é um JSON válido"),
antes de chamar `parseQueryRequest`.

> ✅ **Feito:** `handler.ts` agora retorna `400 INVALID_JSON` em falha de parse, separado do
> `400 VALIDATION_ERROR`. Coberto pelo teste "should return 400 INVALID_JSON…".

## Ponto 2 — [DISCUTIR] `MAX_QUESTION_LENGTH = 1000` é número mágico desacoplado da ADR-0002
O limite de tamanho protege contra custo/abuso (bom), mas **1000 caracteres é arbitrário** e
não está ligado ao *context budget* da ADR-0002 (~4K system + ~8K chunks). Deveria ser
**derivado do orçamento de tokens** e **configurável via env** (T-02), não hardcoded no
validator.

**Ajuste proposto:** mover o limite para `config.ts` (T-02), documentar a relação com o
budget de tokens, e referenciar a ADR-0002 no comentário.

## Ponto 3 — [DISCUTIR] `.strict()` pode quebrar evolução do contrato
`.strict()` rejeita qualquer campo desconhecido. Hoje protege contra typos, mas os outros
módulos (feedback-api, teams-bot) podem passar a enviar metadados adicionais (ex.: `locale`,
`channel`). Com `.strict()`, adicionar um campo no cliente **quebra** a request até o schema
ser atualizado em lockstep.

**Ajuste proposto:** decidir com TL/PS entre `.strict()` (contrato fechado, versionado) e
`.strip()` (ignora desconhecidos). Se mantiver `.strict()`, versionar o contrato e registrar
em ADR.

## Ponto 4 — ✅ RESOLVIDO (P1) — Logger era um shim sobre `console`, agora é `pino`
O `logger.ts` imita a API do pino mas escreve via `console`. Faltam garantias que o pino dá e
que importam aqui: **redaction de campos sensíveis** e níveis/serializers configuráveis. Em
T-09 (completion) há risco concreto de **vazar segredos/prompt** em logs se alguém logar
headers ou o prompt completo.

**Ajuste proposto:** antes de produção, `npm i pino` e configurar `redact` para chaves
sensíveis (authorization, api-key). Hoje é aceitável como stand-in da fase offline, mas deve
ficar rastreado como dívida técnica.

> ✅ **Feito:** `logger.ts` agora usa `pino` real com `redact` de `authorization`/`api-key`.

## Outros pontos (menores)
- **Auth:** `authLevel: "function"` exige function key distribuída ao bot e ao painel web.
  Confirmar com o TL se o modelo de auth é esse ou Entra ID/APIM. *(DISCUTIR)*
- **`errors.ts`:** o `cause` é setado manualmente; com `target: ES2022` dá para usar
  `super(message, { cause })` nativo e simplificar. *(nit)*
- **Contrato de saída:** o handler ainda retorna 501 no happy path (esperado nesta task);
  a garantia de `source_document` em toda resposta (guardrail de produto) só será exercitada
  e testada em T-10/T-11/T-12.

---

## Conclusão
A 1ª task cumpre o escopo (trigger + validação + 400 estruturado, nos padrões do plan).
Os bloqueantes **Pontos 1 e 4 foram resolvidos (P1)**; o código **compila** (`tsc` exit 0) e
**passa nos testes** (8/8). Pontos **2** (limite mágico) e **3** (`.strict()`) seguem como
decisões de design para o gate Tasks→Implement com o Tech Lead — não bloqueiam o merge desta
task, mas devem ser registrados.
