/**
 * Parser puro del protocolo SSE del chat.
 *
 * No conoce `fetch` ni el endpoint. Su única responsabilidad es convertir un
 * stream de bytes ya aceptado por el transporte en `ChatChunk` verificados.
 */
import { areChatSourcesV2 } from '@/lib/chat-source';
import type { ChatChunk } from '@/types/chat';

export class ChatEngineError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly retryable = false
  ) {
    super(message);
    this.name = 'ChatEngineError';
  }
}

interface ParsedSseEvent {
  name: string;
  data: unknown;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function parseEventBlock(block: string): ParsedSseEvent | null {
  let name = 'message';
  const dataLines: string[] = [];

  for (const line of block.split('\n')) {
    if (!line || line.startsWith(':')) continue;
    if (line.startsWith('event:')) {
      name = line.slice('event:'.length).trim();
      continue;
    }
    if (line.startsWith('data:')) dataLines.push(line.slice('data:'.length).trimStart());
  }

  if (dataLines.length === 0) return null;

  try {
    return { name, data: JSON.parse(dataLines.join('\n')) };
  } catch {
    throw new ChatEngineError('El servidor envió un evento JSON inválido.', 'invalid_event');
  }
}

function parseToken(data: unknown): ChatChunk {
  if (!isRecord(data) || typeof data.text !== 'string') {
    throw new ChatEngineError('El servidor envió un token inválido.', 'invalid_event');
  }
  return { type: 'token', text: data.text };
}

function parseSources(data: unknown): ChatChunk {
  if (!isRecord(data) || !areChatSourcesV2(data.sources)) {
    throw new ChatEngineError(
      'El servidor envió fuentes sin trazabilidad válida.',
      'invalid_sources'
    );
  }
  return { type: 'sources', sources: data.sources };
}

function parseServerError(data: unknown): ChatEngineError {
  if (
    !isRecord(data) ||
    typeof data.code !== 'string' ||
    !data.code ||
    typeof data.message !== 'string' ||
    !data.message ||
    (data.retryable !== undefined && typeof data.retryable !== 'boolean')
  ) {
    return new ChatEngineError('El servidor envió un error inválido.', 'invalid_event');
  }
  return new ChatEngineError(data.message, data.code, data.retryable ?? false);
}

function parseDone(data: unknown): ChatChunk {
  if (!isRecord(data) || Array.isArray(data) || Object.keys(data).length > 0) {
    throw new ChatEngineError('El servidor envió un terminal inválido.', 'invalid_event');
  }
  return { type: 'done' };
}

function normalizeLineEndings(value: string): string {
  return value.replace(/\r\n/g, '\n');
}

export async function* parseChatEventStream(
  stream: ReadableStream<Uint8Array>
): AsyncGenerator<ChatChunk> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let pending = '';
  let terminalSeen = false;

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) {
        pending += decoder.decode();
        break;
      }
      pending = normalizeLineEndings(pending + decoder.decode(value, { stream: true }));

      let boundary = pending.indexOf('\n\n');
      while (boundary !== -1) {
        const block = pending.slice(0, boundary);
        pending = pending.slice(boundary + 2);
        boundary = pending.indexOf('\n\n');

        const event = parseEventBlock(block);
        if (!event) continue;
        if (terminalSeen) {
          throw new ChatEngineError(
            'El servidor envió datos después del terminal.',
            'event_after_terminal'
          );
        }

        if (event.name === 'token') {
          yield parseToken(event.data);
          continue;
        }
        if (event.name === 'sources') {
          yield parseSources(event.data);
          continue;
        }
        if (event.name === 'done') {
          terminalSeen = true;
          yield parseDone(event.data);
          continue;
        }
        if (event.name === 'error') {
          terminalSeen = true;
          throw parseServerError(event.data);
        }
        throw new ChatEngineError(
          `El servidor envió un evento desconocido: ${event.name}.`,
          'unexpected_event'
        );
      }
    }
  } catch (error) {
    if (error instanceof ChatEngineError) throw error;
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ChatEngineError(
      'La conexión se interrumpió antes de completar la respuesta.',
      'stream_interrupted',
      true
    );
  } finally {
    reader.releaseLock();
  }

  if (pending.trim() || !terminalSeen) {
    throw new ChatEngineError('La respuesta llegó incompleta.', 'stream_truncated', true);
  }
}
