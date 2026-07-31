/**
 * Transporte del motor real contra `POST /api/chat`.
 *
 * Comprueba HTTP y cabeceras antes de entregar el body al parser puro. Esto es
 * necesario porque el 429 nativo de Netlify no pertenece al protocolo SSE.
 */
import { ChatEngineError, parseChatEventStream } from '@/lib/chat-sse-protocol';
import type { ChatEngine, ChatMessage, ChatRequestContext } from '@/types/chat';

const CHAT_ENDPOINT = '/api/chat';
const CHAT_PROTOCOL_VERSION = '2';

function errorForStatus(status: number): ChatEngineError {
  if (status === 429) {
    return new ChatEngineError(
      'Demasiadas consultas seguidas. Espera un momento.',
      'rate_limited',
      true
    );
  }
  if (status === 503) {
    return new ChatEngineError('El servicio no está disponible ahora mismo.', 'unavailable', true);
  }
  if (status === 400 || status === 413) {
    return new ChatEngineError('La consulta no es válida.', 'invalid_request');
  }
  return new ChatEngineError('No se ha podido completar la consulta.', 'http_error', true);
}

async function requestChat(
  messages: ChatMessage[],
  signal: AbortSignal,
  context?: ChatRequestContext
): Promise<Response> {
  let latestUserMessage: ChatMessage | undefined;
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (message?.role === 'user' && message.content.trim().length > 0) {
      latestUserMessage = message;
      break;
    }
  }
  if (!latestUserMessage) {
    throw new ChatEngineError('Falta una pregunta de usuario.', 'invalid_request');
  }
  try {
    return await fetch(CHAT_ENDPOINT, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        // El comparador vigente es single-turn. No reenviar respuestas A/B ni
        // hechos fiscales anteriores reduce exposición y evita ambigüedad.
        conversation_id: context?.conversationId ?? latestUserMessage.id,
        country_path: context?.countryPath ?? '/espana',
        messages: [{ id: latestUserMessage.id, role: 'user', content: latestUserMessage.content }],
      }),
      signal,
    });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new ChatEngineError('No se ha podido conectar con el servidor.', 'network_error', true);
  }
}

function validateResponse(response: Response): ReadableStream<Uint8Array> {
  if (!response.ok) throw errorForStatus(response.status);
  if (!response.headers.get('content-type')?.toLowerCase().includes('text/event-stream')) {
    throw new ChatEngineError('Respuesta inesperada del servidor.', 'bad_content_type');
  }
  if (response.headers.get('x-chat-protocol') !== CHAT_PROTOCOL_VERSION) {
    throw new ChatEngineError(
      'Versión de protocolo no soportada. Recarga la página.',
      'protocol_mismatch'
    );
  }
  if (!response.body) {
    throw new ChatEngineError('El servidor devolvió una respuesta vacía.', 'empty_body');
  }
  return response.body;
}

export function createLiveChatEngine(): ChatEngine {
  return {
    async *askQuestion(messages, signal, context) {
      const response = await requestChat(messages, signal, context);
      yield* parseChatEventStream(validateResponse(response));
    },
  };
}
