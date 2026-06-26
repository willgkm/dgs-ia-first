// Fixtures de perguntas para testes — domínio de logística (NovaTech).
// Reutilizáveis entre testes de validação e de RAG (ver Testing Standards / QA).

import type { QueryRequest } from "../../src/shared/types.js";
import { MAX_QUESTION_LENGTH } from "../../src/functions/query/validator.js";

/** Pergunta válida típica (cai no contexto "Gestão de Devolução"). */
export const validQuery: QueryRequest = {
  question: "Posso devolver carga perigosa?",
};

/** Pergunta válida com tier de cliente informado. */
export const validQueryWithTier: QueryRequest = {
  question: "Qual o SLA de resolução do cliente Gold?",
  customerTier: "Gold",
};

/** Pergunta que excede o limite de tamanho permitido. */
export const tooLongQuestion = "a".repeat(MAX_QUESTION_LENGTH + 1);

/** Corpos inválidos (tipados como unknown — vêm de fora, não confiáveis). */
export const missingQuestionBody: unknown = {};
export const emptyQuestionBody: unknown = { question: "   " };
export const unknownFieldBody: unknown = { question: "Frete para 600kg?", foo: "bar" };
export const invalidTierBody: unknown = { question: "Qual meu SLA?", customerTier: "Platinum" };
