// Testes de integração do query endpoint (T-12) — Vitest.
// Cobrem a 1ª task: validação de input e respostas de erro estruturadas.
// Sem serviços reais; o happy path ainda retorna 501 (RAG é T-11).

import { describe, it, expect } from "vitest";
import type { HttpRequest, HttpResponseInit, InvocationContext } from "@azure/functions";
import { queryHandler } from "../../src/functions/query/handler.js";
import {
  validQuery,
  validQueryWithTier,
  tooLongQuestion,
  missingQuestionBody,
  emptyQuestionBody,
  unknownFieldBody,
  invalidTierBody,
} from "../fixtures/queries.js";

/** Monta um HttpRequest fake cujo .json() resolve com `body`. */
function makeRequest(body: unknown): HttpRequest {
  return {
    method: "POST",
    url: "http://localhost/api/query",
    headers: { get: () => null },
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as unknown as HttpRequest;
}

/** HttpRequest cujo .json() lança (corpo não-JSON). */
function makeMalformedRequest(): HttpRequest {
  return {
    method: "POST",
    url: "http://localhost/api/query",
    headers: { get: () => null },
    json: async () => {
      throw new SyntaxError("Unexpected token");
    },
    text: async () => "{ not json",
  } as unknown as HttpRequest;
}

const ctx = { invocationId: "test-invocation" } as unknown as InvocationContext;

const bodyOf = (res: HttpResponseInit) => res.jsonBody as { code: string; message: string };

describe("queryHandler", () => {
  it("should pass validation and return 501 (RAG ainda não implementado) when input is valid", async () => {
    const res = await queryHandler(makeRequest(validQuery), ctx);
    expect(res.status).toBe(501);
    expect(bodyOf(res).code).toBe("NOT_IMPLEMENTED");
  });

  it("should accept a valid question with a known customerTier", async () => {
    const res = await queryHandler(makeRequest(validQueryWithTier), ctx);
    expect(res.status).toBe(501);
  });

  it("should return 400 INVALID_JSON when the body is not valid JSON", async () => {
    const res = await queryHandler(makeMalformedRequest(), ctx);
    expect(res.status).toBe(400);
    expect(bodyOf(res).code).toBe("INVALID_JSON");
  });

  it("should return 400 VALIDATION_ERROR when 'question' is missing", async () => {
    const res = await queryHandler(makeRequest(missingQuestionBody), ctx);
    expect(res.status).toBe(400);
    expect(bodyOf(res).code).toBe("VALIDATION_ERROR");
  });

  it("should return 400 VALIDATION_ERROR when 'question' is only whitespace", async () => {
    const res = await queryHandler(makeRequest(emptyQuestionBody), ctx);
    expect(res.status).toBe(400);
    expect(bodyOf(res).code).toBe("VALIDATION_ERROR");
  });

  it("should reject unknown fields (.strict) with 400 VALIDATION_ERROR", async () => {
    const res = await queryHandler(makeRequest(unknownFieldBody), ctx);
    expect(res.status).toBe(400);
    expect(bodyOf(res).code).toBe("VALIDATION_ERROR");
  });

  it("should reject an invented customer tier with 400 VALIDATION_ERROR", async () => {
    const res = await queryHandler(makeRequest(invalidTierBody), ctx);
    expect(res.status).toBe(400);
    expect(bodyOf(res).code).toBe("VALIDATION_ERROR");
  });

  it("should return 400 VALIDATION_ERROR when 'question' exceeds the max length", async () => {
    const res = await queryHandler(makeRequest({ question: tooLongQuestion }), ctx);
    expect(res.status).toBe(400);
    expect(bodyOf(res).code).toBe("VALIDATION_ERROR");
  });
});
