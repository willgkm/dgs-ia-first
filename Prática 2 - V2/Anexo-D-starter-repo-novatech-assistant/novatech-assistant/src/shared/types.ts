// Tipos de domínio e contrato de I/O do assistente NovaTech (T-01, parcial).
// Nesta entrega (Ex. 2.2) só os tipos necessários à 1ª task estão definidos;
// os demais (busca/completion) serão completados em T-07..T-11.

/** Tier de cliente reconhecido pelo domínio (SLA-2024). Não existem outros. */
export type CustomerTier = "Gold" | "Silver" | "Standard";

/** Request do endpoint POST /api/query. */
export interface QueryRequest {
  /** Pergunta do atendente. Obrigatória, não-vazia, com limite de tamanho. */
  question: string;
  /** Tier do cliente em contexto, quando conhecido (opcional). */
  customerTier?: CustomerTier;
  /** Correlação opcional fornecida pelo chamador (ex.: id do ticket). */
  conversationId?: string;
}

/** Chunk recuperado do corpus (Azure AI Search / corpus local). */
export interface RetrievedChunk {
  id: string;
  text: string;
  /** Identificador do documento-fonte (ex.: "POL-001", "SLA-2024"). */
  source_document: string;
  section?: string;
  /** Metadado de vigência (ADR-0003): documentos mais recentes têm prioridade. */
  effectiveDate?: string;
  isObsolete?: boolean;
}

/** Fonte citada na resposta. `source_document` é obrigatório (guardrail de produto). */
export interface ResponseSource {
  source_document: string;
  section?: string;
}

/** Response do endpoint. */
export interface QueryResponse {
  answer: string;
  sources: ResponseSource[];
  /** True quando a confiança é baixa (prefixar aviso ao usuário). */
  low_confidence: boolean;
}
