import type { StrategyTurn } from './contracts';

/**
 * El historial viaja en el prompt de CADA petición: sin tope, una conversación
 * larga encarece todos los turnos siguientes. Seis turnos cubren un seguimiento
 * real sin convertir el contexto en el grueso de la entrada.
 */
export const MAX_HISTORY_TURNS = 6;

/**
 * Las respuestas anteriores se recortan porque solo sirven para saber de qué se
 * venía hablando. No es texto legal: las citas literales nunca salen de aquí,
 * sino del contexto estructurado o de File Search en el turno actual.
 */
export const MAX_HISTORY_ANSWER_CHARS = 1_500;

const recentTurns = (history: readonly StrategyTurn[]) => history.slice(-MAX_HISTORY_TURNS);

const shorten = (text: string) =>
  text.length <= MAX_HISTORY_ANSWER_CHARS ? text : `${text.slice(0, MAX_HISTORY_ANSWER_CHARS)} […]`;

/**
 * Bloque de contexto para el prompt. Va marcado como conversación previa y no
 * como evidencia: una respuesta anterior es texto redactado por el modelo, y
 * tratarla como fuente permitiría citar algo que ninguna sentencia respalda.
 */
export const conversationContextBlock = (history: readonly StrategyTurn[]): string => {
  const turns = recentTurns(history);
  if (turns.length === 0) return '';
  const transcript = turns
    .map((turn, index) => {
      const lines = [`[${index + 1}] Usuario: ${turn.question}`];
      if (turn.answer) {
        const speaker = turn.editorial
          ? 'Respuesta editorial mostrada al usuario (no la escribiste tú)'
          : 'Tú';
        lines.push(`[${index + 1}] ${speaker}: ${shorten(turn.answer)}`);
      }
      return lines.join('\n');
    })
    .join('\n');
  return [
    'Turnos anteriores de esta misma conversación, del más antiguo al más reciente.',
    'Sirven para interpretar a qué se refiere la pregunta actual cuando depende de lo ya dicho.',
    'El historial no es evidencia: toda cita debe salir de la evidencia recuperada en este turno.',
    transcript,
  ].join('\n');
};

/**
 * Consulta con la que buscar en el corpus cuando la pregunta no se sostiene sola
 * («dame un ejemplo de lo anterior»). Solo suma las preguntas del usuario: las
 * respuestas anteriores están escritas con el vocabulario del modelo y arrastran
 * la recuperación hacia lo que ya se dijo.
 */
export const contextualRetrievalQuery = (
  history: readonly StrategyTurn[],
  question: string
): string => {
  const previous = recentTurns(history)
    .map((turn) => turn.question.trim())
    .filter(Boolean);
  if (previous.length === 0) return question;
  return [...previous, question].join('\n');
};
