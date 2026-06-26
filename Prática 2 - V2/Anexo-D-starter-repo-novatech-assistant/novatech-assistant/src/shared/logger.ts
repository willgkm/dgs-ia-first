// Logger estruturado (T-03) — pino.
// Proibido `console.log` no código de produção: use este logger.
// `redact` evita vazamento de segredos/headers sensíveis em logs (ver review Ponto 4).

import pino from "pino";

export const logger = pino({
  name: "novatech-assistant",
  level: process.env.LOG_LEVEL ?? "info",
  redact: {
    paths: [
      "authorization",
      "*.authorization",
      "headers.authorization",
      "apiKey",
      "*.apiKey",
      "api-key",
      "*.api-key",
    ],
    censor: "[REDACTED]",
  },
});

export type Logger = typeof logger;
