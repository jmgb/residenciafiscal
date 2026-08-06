interface EditorialTurnRecord {
  conversationId: string;
  conversationAccessToken: string;
  userMessageId: string;
  countryPath: string;
  answerId: string;
}

const EDITORIAL_RECORD_TIMEOUT_MS = 3_000;

/**
 * Registra en el servidor que este turno se resolvió con una respuesta editorial,
 * para que el chat pueda recuperarlo como contexto si la conversación continúa.
 *
 * Solo viaja el identificador de la respuesta: el texto lo pone el servidor desde
 * su propia copia del catálogo. Nunca lanza: es telemetría de conversación, no
 * una parte de la respuesta que el usuario está leyendo.
 */
export const recordEditorialTurn = async (
  input: EditorialTurnRecord,
  callerSignal?: AbortSignal
): Promise<void> => {
  const controller = new AbortController();
  const abortFromCaller = () => controller.abort(callerSignal?.reason);
  callerSignal?.addEventListener('abort', abortFromCaller, { once: true });
  if (callerSignal?.aborted) abortFromCaller();
  const timeout = setTimeout(() => controller.abort(), EDITORIAL_RECORD_TIMEOUT_MS);
  try {
    await fetch('/api/chat-editorial', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        conversation_id: input.conversationId,
        conversation_access_token: input.conversationAccessToken,
        user_message_id: input.userMessageId,
        country_path: input.countryPath,
        answer_id: input.answerId,
      }),
      keepalive: true,
      signal: controller.signal,
    });
  } catch {
    // Sin registro, un seguimiento posterior se responderá sin este contexto.
  } finally {
    clearTimeout(timeout);
    callerSignal?.removeEventListener('abort', abortFromCaller);
  }
};
