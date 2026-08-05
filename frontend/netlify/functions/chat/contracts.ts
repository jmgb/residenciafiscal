import type { ChatDiagnostic } from './chat-diagnostics';

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
  /** `editorial` cuando la cita procede del catálogo revisado, no de una estrategia. */
  strategy: StrategyId | 'editorial';
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
  error_context?: ChatDiagnostic | null;
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

/**
 * Estrategias que pueden aparecer en el historial. `editorial` es contenido
 * revisado del repositorio que el chat muestra sin llamar a ningún modelo: no
 * compite en la comparación, pero sí forma parte de la conversación que el
 * usuario ha leído.
 */
export type HistoryStrategyId = StrategyId | 'editorial';

/** Turno anterior de la conversación, tal y como quedó en el ledger privado. */
export interface ConversationTurn {
  question: string;
  answers: { strategy: HistoryStrategyId; content: string }[];
}

/**
 * El mismo turno visto por UNA estrategia: su propia respuesta anterior, o cadena
 * vacía si en ese turno no llegó a responder. Cada estrategia recibe solo su hilo
 * porque leer las respuestas de la otra destruiría la independencia de la
 * comparación A/B.
 */
export interface StrategyTurn {
  question: string;
  answer: string;
  /** La respuesta mostrada fue editorial, no la escribió esta estrategia. */
  editorial?: boolean;
}

export interface ComparisonReport {
  schema_version: 'residenciafiscal-chat-comparison/1';
  request_id: string;
  experimental: true;
  /** Una o dos respuestas, según las estrategias habilitadas en el runtime. */
  answers: StrategyAnswer[];
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
