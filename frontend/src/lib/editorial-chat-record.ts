interface EditorialTurnRecord {
  conversationId: string;
  userMessageId: string;
  countryPath: string;
  answerId: string;
}

/**
 * Registra en el servidor que este turno se resolvió con una respuesta editorial,
 * para que el chat pueda recuperarlo como contexto si la conversación continúa.
 *
 * Solo viaja el identificador de la respuesta: el texto lo pone el servidor desde
 * su propia copia del catálogo. Nunca lanza: es telemetría de conversación, no
 * una parte de la respuesta que el usuario está leyendo.
 */
export const recordEditorialTurn = async (input: EditorialTurnRecord): Promise<void> => {
  try {
    await fetch('/api/chat-editorial', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        conversation_id: input.conversationId,
        user_message_id: input.userMessageId,
        country_path: input.countryPath,
        answer_id: input.answerId,
      }),
      keepalive: true,
    });
  } catch {
    // Sin registro, un seguimiento posterior se responderá sin este contexto.
  }
};
