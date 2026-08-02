export const CHAT_OBSERVABILITY_SCHEMA_VERSION = 'residenciafiscal-chat-observability/1' as const;

export type ChatFailureStage = 'record' | 'compare' | 'complete';

export interface ChatFailureEvent {
  requestId: string;
  failureCode: string;
  stage: ChatFailureStage;
  status?: 'failed' | 'timed_out';
  /** Nombre de la clase del error. Se sanea antes de salir del proceso. */
  errorName?: string;
  latencyMs?: number;
}

export interface ChatStrategyFailureEvent {
  requestId: string;
  strategy: 'current_structured' | 'gemini_file_search';
  failureCode: string;
  errorName?: string;
  latencyMs: number;
}

export interface ChatCostStrategy {
  strategy: string;
  status: string;
  model: string | null;
  reasoning_effort: string | null;
  latency_ms: number;
  cost_microusd: number | null;
  measurement: string;
  input_tokens: number | null;
  output_tokens: number | null;
  retrieved_document_tokens: number | null;
  source_count: number;
  limit_count: number;
  judgment_ids: string[];
  authority_counts: {
    tribunal_supremo: number;
    audiencia_nacional: number;
    other: number;
  };
  authority_match: 'direct' | 'missing' | 'not_requested';
  retrieval_filter: string | null;
  citation_candidates: number;
  citation_verified: number;
  document_token_accounting: 'reported' | 'unavailable' | 'not_applicable';
  failure_code: string | null;
  error_name: string | null;
}

export interface ChatCostEvent {
  requestId: string;
  actualMicrousd: number;
  actualComplete: boolean;
  authorityIntent: 'tribunal_supremo' | 'audiencia_nacional' | null;
  timingsMs: {
    record: number;
    compare: number;
    persistence: number;
    total: number;
  };
  strategies: readonly ChatCostStrategy[];
}

export interface ChatObservability {
  recordFailure(event: ChatFailureEvent): Promise<void>;
  recordStrategyFailure(event: ChatStrategyFailureEvent): Promise<void>;
  recordCost(event: ChatCostEvent): Promise<void>;
}

export const sanitizeErrorName = (value: string | undefined): string =>
  value && /^[A-Za-z][A-Za-z0-9_]{0,39}$/.test(value) ? value : 'unknown';
