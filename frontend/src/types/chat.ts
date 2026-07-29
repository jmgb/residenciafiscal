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

/** Sentencia citada por una respuesta del asistente. */
export interface ChatSource extends CorpusEntry {
  /** Extracto mostrado al desplegar la fuente. */
  extracto: string;
}

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
