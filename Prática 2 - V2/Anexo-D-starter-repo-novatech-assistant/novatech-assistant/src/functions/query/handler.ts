// HTTP trigger do query endpoint (T-06) — lógica do handler (sem registro).
// O registro do trigger fica em ./index.ts para manter este módulo testável
// (importar este arquivo não dispara app.http no load).
// Padrões (plan / ADRs): Azure Functions v4, Zod, logger estruturado, sem console.log.
// Escopo desta task: validar input e responder 400 estruturado em erro. A orquestração
// RAG (busca → prompt → completion → resposta) é a T-11; o happy path retorna 501.

import type { HttpRequest, HttpResponseInit, InvocationContext } from "@azure/functions";
import { parseQueryRequest } from "./validator.js";
import { isAppError } from "../../shared/errors.js";
import { logger } from "../../shared/logger.js";

export async function queryHandler(
  request: HttpRequest,
  context: InvocationContext,
): Promise<HttpResponseInit> {
  const log = logger.child({ requestId: context.invocationId, route: "query" });

  // 1) Parse do corpo. JSON malformado é um erro distinto de "campo ausente".
  let rawBody: unknown;
  try {
    rawBody = await request.json();
  } catch {
    log.warn({ code: "INVALID_JSON" }, "corpo da requisição não é JSON válido");
    return {
      status: 400,
      jsonBody: { code: "INVALID_JSON", message: "O corpo da requisição não é um JSON válido." },
    };
  }

  // 2) Validação de schema + fluxo principal.
  try {
    const parsed = parseQueryRequest(rawBody);
    log.info({ questionLength: parsed.question.length }, "input válido recebido");

    // TODO (T-11): searchChunks → buildPrompt → complete → buildResponse.
    return {
      status: 501,
      jsonBody: {
        code: "NOT_IMPLEMENTED",
        message: "Pipeline de RAG ainda não implementado (ver T-11).",
      },
    };
  } catch (err: unknown) {
    if (isAppError(err)) {
      log.warn({ code: err.code, status: err.statusCode }, "requisição rejeitada");
      return { status: err.statusCode, jsonBody: err.toClientBody() };
    }
    // Erro inesperado: loga o detalhe internamente, responde genérico (sem vazar stack).
    log.error({ err: String(err) }, "erro inesperado no handler");
    return {
      status: 500,
      jsonBody: { code: "INTERNAL_ERROR", message: "Erro interno ao processar a requisição." },
    };
  }
}
