/**
 * Tipos compartidos por el motor de chat, el store de conversaciones y la UI.
 *
 * `ChatEngine` es el contrato que hoy cumple el stub y que mañana cumplirá el
 * backend RAG real (Netlify Function, Supabase o VPS). Sustituir la
 * implementación no debe obligar a tocar nada fuera de `src/lib/`.
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
}

/** Unidad de la respuesta en streaming. */
export type ChatChunk =
  | { type: 'token'; text: string }
  | { type: 'sources'; sources: ChatSource[] }
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
