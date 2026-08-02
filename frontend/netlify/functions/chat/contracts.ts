export type StrategyId = 'current_structured' | 'gemini_file_search';
export type AnswerStatus = 'completa' | 'parcial' | 'pregunta' | 'abstención' | 'error';

interface MarginalCostBase {
  currency: 'USD';
  scope: 'REQUEST_MARGINAL';
  pricing_version: string;
  excludes_corpus_preparation: true;
}

export interface AvailableMarginalCost extends MarginalCostBase {
  amount_usd: string;
  cost_microusd: number;
  measurement: 'ACTUAL' | 'ESTIMATED';
  input_tokens: number;
  output_tokens: number;
  retrieved_document_tokens: number;
}

export interface UnavailableMarginalCost extends MarginalCostBase {
  amount_usd: null;
  cost_microusd: null;
  measurement: 'UNAVAILABLE';
  input_tokens: null;
  output_tokens: null;
  retrieved_document_tokens: null;
}

export type MarginalCost = AvailableMarginalCost | UnavailableMarginalCost;

export interface StrategySource {
  strategy: StrategyId;
  judgment_id: string;
  page: number;
  source_sha256: string;
  quote: string;
  verification: 'EXACT';
}

export interface StrategyDiagnostics {
  authority_intent: 'tribunal_supremo' | 'audiencia_nacional' | null;
  authority_match: 'direct' | 'missing' | 'not_requested';
  retrieval_filter: string | null;
  retrieved_judgment_ids: string[];
  citation_candidates: number;
  citation_verified: number;
  failure_code:
    | 'timeout'
    | 'exception'
    | 'strategy_contract'
    | 'citation_verification'
    | 'evidence_validation'
    | null;
  error_name: string | null;
}

export interface StrategyClaim {
  text: string;
  /** Índices 1-based sobre `sources`, estables dentro de esta respuesta. */
  source_indexes: number[];
}

export interface StrategyAnswer {
  strategy: StrategyId;
  status: AnswerStatus;
  text: string;
  sources: StrategySource[];
  limits: string[];
  cost: MarginalCost;
  model: string;
  reasoning_effort: string | null;
  latency_ms: number;
  claims?: StrategyClaim[];
  diagnostics?: StrategyDiagnostics;
}

export interface ComparisonReport {
  schema_version: 'residenciafiscal-chat-comparison/1';
  request_id: string;
  experimental: true;
  answers: [StrategyAnswer, StrategyAnswer];
}

export const unknownCost = (): MarginalCost => ({
  currency: 'USD',
  amount_usd: null,
  cost_microusd: null,
  measurement: 'UNAVAILABLE',
  scope: 'REQUEST_MARGINAL',
  pricing_version: 'unavailable',
  input_tokens: null,
  output_tokens: null,
  retrieved_document_tokens: null,
  excludes_corpus_preparation: true,
});
