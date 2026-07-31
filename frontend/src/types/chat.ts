/**
 * Tipos compartidos por el motor de chat, el store de conversaciones y la UI.
 *
 * `ChatEngine` es el contrato común del stub y del cliente live conectado a
 * Netlify Edge + FastAPI. Sustituir la implementación no debe obligar a tocar
 * la presentación fuera del selector de `src/lib/`.
 */

/** Resultado del fallo, tal y como lo clasifica el pipeline Python. */
export type ResultadoFinal =
  | 'GANA_AEAT'
  | 'GANA_CONTRIBUYENTE'
  | 'PARCIAL'
  | 'RETROACCION'
  | 'INADMISION'
  | 'DESCONOCIDO';

/** Entrada del corpus ligero generado desde `output/analisis_*.jsonl`. */
export interface CorpusEntry {
  archivo: string;
  roj: string;
  ecli: string;
  organo: string;
  fecha: string;
  resultado: ResultadoFinal;
  criterioDecisivo: string[];
  esCasoResidencia: boolean;
}

export type TechnicalReviewStatus = 'GENERATED' | 'VALIDATED' | 'NEEDS_REVIEW' | 'REJECTED';

export type LegalReviewStatus = 'UNREVIEWED' | 'AGENT_REVIEWED' | 'HUMAN_APPROVED' | 'REJECTED';

export interface ChatSourceReviewStatus {
  technical: TechnicalReviewStatus;
  legal: LegalReviewStatus;
}

/**
 * Fuente producida antes del contrato v2.
 *
 * Solo se conserva para el stub y para no perder conversaciones locales
 * antiguas. Su extracto puede ser un resumen y nunca se presenta como cita
 * judicial verificada.
 */
export interface LegacyChatSource extends CorpusEntry {
  extracto: string;
}

/** Cita judicial trazable que puede emitir el protocolo del backend real. */
export interface ChatSourceV2 extends CorpusEntry {
  sourceId: string;
  issueId: string;
  issueLabel: string;
  anchorId: string;
  /** Página física 1-indexada del PDF. */
  pageIndex: number;
  printedPage: string | null;
  /** Texto literal procedente del anclaje verificado, nunca prosa del modelo. */
  extracto: string;
  fidelity: 'exact' | 'exact_with_ellipsis';
  sourceSha256: string;
  reviewStatus: ChatSourceReviewStatus;
}

/** Fuentes que la UI puede representar durante la migración al protocolo v2. */
export type ChatSource = ChatSourceV2 | LegacyChatSource;

export type ChatRole = 'user' | 'assistant';

/** Contexto nacional que debe acompañar cada consulta al motor. */
export interface ChatRequestContext {
  countryPath: string;
  countryName: string;
  /** Identificador aleatorio local; no identifica por sí solo a una persona. */
  conversationId?: string;
}

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  /** ISO 8601. */
  createdAt: string;
  sources?: ChatSource[];
  /** true mientras se están recibiendo tokens. */
  isStreaming?: boolean;
  /** Dos respuestas independientes del experimento A/B. */
  answers?: ChatStrategyAnswer[];
}

export type ChatStrategyId = 'current_structured' | 'gemini_file_search';
export type ChatAnswerStatus = 'completa' | 'parcial' | 'pregunta' | 'abstención' | 'error';

export interface ChatMarginalCost {
  currency: 'USD';
  /** Decimal exacto de seis posiciones, o null si el proveedor no informó uso. */
  amountUsd: string | null;
  costMicrousd: number | null;
  measurement: 'ACTUAL' | 'ESTIMATED' | 'UNAVAILABLE';
  scope: 'REQUEST_MARGINAL';
  pricingVersion: string;
  inputTokens: number | null;
  outputTokens: number | null;
  retrievedDocumentTokens: number | null;
  excludesCorpusPreparation: true;
}

/** Fuente mínima común que devuelve cada estrategia tras el gate local. */
export interface ChatStrategySource {
  strategy: ChatStrategyId;
  judgmentId: string;
  page: number;
  sourceSha256: string;
  quote: string;
  verification: 'EXACT';
}

export interface ChatStrategyAnswer {
  strategy: ChatStrategyId;
  status?: ChatAnswerStatus;
  content: string;
  sources: ChatStrategySource[];
  limits: string[];
  cost?: ChatMarginalCost;
  model?: string;
  latencyMs?: number;
  isStreaming: boolean;
}

/** Unidad de la respuesta en streaming. */
export type ChatChunk =
  | { type: 'answer_start'; strategy: ChatStrategyId }
  | { type: 'token'; text: string; strategy?: ChatStrategyId }
  | { type: 'sources'; sources: ChatSource[] }
  | { type: 'strategy_sources'; strategy: ChatStrategyId; sources: ChatStrategySource[] }
  | {
      type: 'answer_done';
      strategy: ChatStrategyId;
      status: ChatAnswerStatus;
      limits: string[];
      cost: ChatMarginalCost;
      model: string;
      latencyMs: number;
    }
  | { type: 'done' };

export interface ChatEngine {
  askQuestion(
    messages: ChatMessage[],
    signal: AbortSignal,
    context?: ChatRequestContext
  ): AsyncIterable<ChatChunk>;
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
}
