# Skill: typescript-conventions (Foundation)

> **Nível:** Foundation · **Base de todas as outras skills.** Toda skill Domain e Artifact
> que gera código TypeScript DEVE seguir estas convenções. Se houver conflito, esta skill
> é a fonte da verdade para estilo/tipagem; as skills de nível superior só *adicionam* regras.

## Quando usar (frase-ativação)
"Vou gerar ou editar qualquer arquivo `.ts`/`.d.ts` no projeto NovaTech Assistant" —
endpoints, services, componentes, testes, tipos compartilhados. Leia esta skill **antes**
de escrever a primeira linha.

## Contexto do projeto
- `tsconfig.json`: `strict: true`, `target: ES2022`, `module: ESNext`,
  `moduleResolution: Bundler`. Projeto é **ESM** (`"type": "module"` no `package.json`).
- Stack: Azure Functions v4 (backend/bot), React (painel), Zod (validação), Vitest (testes),
  pino (logging).
- Consequência prática: **imports relativos terminam em `.js`** (ESM), `any` é proibido por
  `strict`, e o código roda em Node moderno (ES2022).

---

## Regras prescritivas (DEVE / NÃO DEVE)

### DEVE
1. **`strict` é inegociável.** Nada de `any`. Para valor desconhecido use `unknown` e estreite
   com type guard ou Zod.
2. **Imports relativos com extensão `.js`** (mesmo importando de um `.ts`) — exigência do ESM
   com `moduleResolution: Bundler`/Node ESM.
3. **`import type { … }`** para imports que são só de tipo (evita ciclos e custo de runtime).
4. **Tipos explícitos** em assinaturas públicas (parâmetros e retorno de funções exportadas).
5. **`interface` para contratos de objeto** do domínio; `type` para uniões/aliases.
6. **Validar dados externos com Zod** na fronteira (input HTTP, env vars) — nunca confiar em
   cast (`as`) para dados que vêm de fora.
7. **`logger` estruturado** (`src/shared/logger.ts`) para qualquer saída — **nunca**
   `console.log` no código de produção.
8. **Erros tipados** da hierarquia `AppError` (`src/shared/errors.ts`); não lançar `string`
   nem `Error` cru para fluxos previsíveis.
9. **`const` por padrão**; `let` só quando há reatribuição. Nunca `var`.
10. **Nomes:** `camelCase` (vars/funções), `PascalCase` (tipos/classes/componentes),
    `UPPER_SNAKE_CASE` (constantes de módulo). Arquivos em `kebab-case.ts`.

### NÃO DEVE
- ❌ `any`, `as any`, `@ts-ignore` (use `@ts-expect-error` com justificativa só se inevitável).
- ❌ `console.log`/`console.error` direto (use o `logger`).
- ❌ Import relativo sem `.js` (`from "./validator"` → quebra em runtime ESM).
- ❌ `require()`/`module.exports` (projeto é ESM).
- ❌ `export default` (preferir named exports — melhor refactor/tree-shaking).
- ❌ Cast (`as Tipo`) para validar input externo — use Zod.

---

## Exemplos concretos (DO / DON'T)

### Imports ESM e type-only
```ts
// ✅ DO — extensão .js + import type
import { z } from "zod";
import type { QueryRequest } from "../../shared/types.js";
import { ValidationError } from "../../shared/errors.js";

// ❌ DON'T — sem extensão, tipo importado como valor, default import
import { QueryRequest } from "../../shared/types";   // quebra em ESM
import errors from "../../shared/errors";            // default export proibido
```

### Dados externos: Zod, não cast
```ts
// ✅ DO — valida e estreita unknown → tipo seguro
export function parseQueryRequest(body: unknown): QueryRequest {
  const result = queryRequestSchema.safeParse(body);
  if (!result.success) {
    throw new ValidationError("Falha na validação da requisição.", result.error.issues);
  }
  return result.data;
}

// ❌ DON'T — cast cego: TS "confia", runtime explode
export function parseQueryRequest(body: unknown): QueryRequest {
  return body as QueryRequest; // mente para o compilador; nenhum dado é validado
}
```

### `unknown` em catch + erro tipado
```ts
// ✅ DO
try {
  /* ... */
} catch (err: unknown) {
  if (isAppError(err)) return { status: err.statusCode, jsonBody: err.toClientBody() };
  logger.error({ err: String(err) }, "erro inesperado");
  return { status: 500, jsonBody: { code: "INTERNAL_ERROR", message: "Erro interno." } };
}

// ❌ DON'T — `any` no catch e vazamento de stack para o cliente
} catch (err: any) {
  return { status: 500, jsonBody: { error: err.stack } }; // expõe interno + any
}
```

### Logging estruturado
```ts
// ✅ DO
logger.info({ questionLength: parsed.question.length }, "input válido recebido");

// ❌ DON'T
console.log("input recebido: " + JSON.stringify(parsed)); // proibido; pode vazar dados
```

---

## Anti-padrões (o que o Copilot tende a gerar sem esta skill)
1. **Import sem `.js`** — o autocomplete do Copilot quase sempre omite a extensão; em ESM
   isso resulta em `ERR_MODULE_NOT_FOUND` em runtime, **passando** no editor.
2. **`catch (err: any)`** — padrão default do Copilot; viola `strict` na intenção e costuma
   vir junto com vazamento de `err.message`/`err.stack` na resposta HTTP.
3. **`body as RequestType`** em vez de validar — Copilot "resolve" o tipo com cast e pula o
   Zod, criando buracos de validação na fronteira.
4. **`console.log` para debug** — vem por reflexo; tem que ser `logger`.
5. **`export default`** numa função utilitária — dificulta refactor e tree-shaking; preferir
   named export.
6. **`enum` de TypeScript** para constantes simples — preferir union de string literais
   (`type Tier = "Gold" | "Silver" | "Standard"`), mais leve e ESM-friendly.

---

## Dependências
- **Nenhuma** (é a base). As demais skills assumem estas regras:
  - `error-handling` (Foundation) → estende as regras de erro daqui.
  - `project-structure` (Foundation) → onde cada tipo de arquivo mora.
  - `azure-functions-endpoint`, `testing-patterns`, `react-components` (Domain) → herdam tudo.
  - `create-rag-endpoint`, `create-integration-test`, `create-react-card` (Artifact) → idem.

## Critério de "skill madura"
Pronta para o time quando: (a) um endpoint gerado pelo Copilot com esta skill no contexto
compila sob `strict` sem ajuste de imports, e (b) não introduz `any`/`console.log`/cast de
input em 3 gerações consecutivas de teste.
