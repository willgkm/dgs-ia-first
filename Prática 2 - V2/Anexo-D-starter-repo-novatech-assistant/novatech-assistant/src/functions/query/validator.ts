// Validação de input do query endpoint (T-05).
// Usa Zod (já em devDependencies). Rejeita corpo malformado e mapeia falhas para
// ValidationError (400). Limite de tamanho em `question` protege contra custo
// excessivo e payloads abusivos (anti prompt-injection trivial).

import { z } from "zod";
import type { QueryRequest } from "../../shared/types.js";
import { ValidationError } from "../../shared/errors.js";

/** Limite máximo de caracteres da pergunta (proteção de custo / abuso). */
export const MAX_QUESTION_LENGTH = 1000;

const queryRequestSchema = z
  .object({
    question: z
      .string({ required_error: "O campo 'question' é obrigatório." })
      .trim()
      .min(1, "A pergunta não pode ser vazia.")
      .max(MAX_QUESTION_LENGTH, `A pergunta excede ${MAX_QUESTION_LENGTH} caracteres.`),
    customerTier: z.enum(["Gold", "Silver", "Standard"]).optional(),
    conversationId: z.string().trim().min(1).max(200).optional(),
  })
  .strict(); // rejeita campos desconhecidos

/**
 * Valida e normaliza o corpo da request. Lança ValidationError (400) em entrada inválida.
 */
export function parseQueryRequest(body: unknown): QueryRequest {
  const result = queryRequestSchema.safeParse(body);
  if (!result.success) {
    const issues = result.error.issues.map((i) => ({
      path: i.path.join(".") || "(root)",
      message: i.message,
    }));
    throw new ValidationError("Falha na validação da requisição.", issues);
  }
  return result.data;
}
