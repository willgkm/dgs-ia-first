// Hierarquia de erros da aplicação (T-04).
// Cada erro carrega o status HTTP e um `code` estável. O detalhe interno
// (causa/stack) NUNCA deve ir para o corpo da resposta ao cliente — use
// `toClientBody()` para a serialização segura.

export interface ClientErrorBody {
  code: string;
  message: string;
  issues?: unknown;
}

export abstract class AppError extends Error {
  abstract readonly statusCode: number;
  abstract readonly code: string;
  /** Detalhe estruturado seguro para o cliente (ex.: issues de validação). */
  readonly issues?: unknown;

  protected constructor(message: string, issues?: unknown, options?: { cause?: unknown }) {
    super(message);
    this.name = new.target.name;
    this.issues = issues;
    if (options?.cause !== undefined) {
      (this as { cause?: unknown }).cause = options.cause;
    }
  }

  /** Corpo seguro para resposta HTTP — sem stack, sem causa interna. */
  toClientBody(): ClientErrorBody {
    return { code: this.code, message: this.message, issues: this.issues };
  }
}

/** 400 — input malformado ou que viola o schema. */
export class ValidationError extends AppError {
  readonly statusCode = 400;
  readonly code = "VALIDATION_ERROR";
  constructor(message: string, issues?: unknown) {
    super(message, issues);
  }
}

/** 502 — falha em dependência externa (Azure AI Search / Azure OpenAI). */
export class UpstreamError extends AppError {
  readonly statusCode = 502;
  readonly code = "UPSTREAM_ERROR";
  constructor(message: string, options?: { cause?: unknown }) {
    super(message, undefined, options);
  }
}

/** 404 — nenhuma informação encontrada para a pergunta. */
export class NotFoundError extends AppError {
  readonly statusCode = 404;
  readonly code = "NOT_FOUND";
  constructor(message: string) {
    super(message);
  }
}

/** Type guard para erros conhecidos da aplicação. */
export function isAppError(err: unknown): err is AppError {
  return err instanceof AppError;
}
