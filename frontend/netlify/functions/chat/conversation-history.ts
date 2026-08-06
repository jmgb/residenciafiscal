import type { StrategyTurn } from './contracts';

/**
 * El historial viaja en el prompt de CADA petición: sin tope, una conversación
 * larga encarece todos los turnos siguientes. Seis turnos cubren un seguimiento
 * real sin convertir el contexto en el grueso de la entrada.
 */
export const MAX_HISTORY_TURNS = 6;
export const MAX_HISTORY_CONTEXT_BYTES = 12 * 1024;
export const MAX_HISTORY_QUESTION_CHARS = 500;

/**
 * Las respuestas anteriores se recortan porque solo sirven para saber de qué se
 * venía hablando. No es texto legal: las citas literales nunca salen de aquí,
 * sino del contexto estructurado o de File Search en el turno actual.
 */
export const MAX_HISTORY_ANSWER_CHARS = 1_500;

const recentTurns = (history: readonly StrategyTurn[]) => history.slice(-MAX_HISTORY_TURNS);
const byteLength = (text: string) => new TextEncoder().encode(text).byteLength;

const shorten = (text: string, maxChars: number) =>
  text.length <= maxChars ? text : `${text.slice(0, maxChars)} […]`;

const renderContext = (turns: readonly StrategyTurn[]) => {
  const transcript = turns
    .map((turn, index) => {
      const lines = [
        `[${index + 1}] Usuario: ${shorten(turn.question, MAX_HISTORY_QUESTION_CHARS)}`,
      ];
      if (turn.answer) {
        const speaker = turn.editorial
          ? 'Respuesta editorial mostrada al usuario (no la escribiste tú)'
          : 'Tú';
        lines.push(`[${index + 1}] ${speaker}: ${shorten(turn.answer, MAX_HISTORY_ANSWER_CHARS)}`);
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
 * Bloque de contexto para el prompt. Va marcado como conversación previa y no
 * como evidencia: una respuesta anterior es texto redactado por el modelo, y
 * tratarla como fuente permitiría citar algo que ninguna sentencia respalda.
 */
export const conversationContextBlock = (history: readonly StrategyTurn[]): string => {
  const turns = recentTurns(history);
  if (turns.length === 0) return '';
  let selected: StrategyTurn[] = [];
  for (let index = turns.length - 1; index >= 0; index -= 1) {
    const candidate = [turns[index] as StrategyTurn, ...selected];
    if (byteLength(renderContext(candidate)) > MAX_HISTORY_CONTEXT_BYTES) break;
    selected = candidate;
  }
  return renderContext(selected);
};

export const questionReferencesHistory = (question: string): boolean =>
  /\b(?:ese|esa|eso|esos|esas)\b|\b(?:lo|el caso|la respuesta|la pregunta|la sentencia|el criterio|la resolucion|el asunto|los casos|las respuestas|las preguntas|las sentencias|los criterios|las resoluciones|los asuntos) anterior(?:es)?\b/.test(
    question.toLocaleLowerCase('es').normalize('NFKD').replace(/\p{M}/gu, '')
  );

export const contextualReferenceQuery = (
  history: readonly StrategyTurn[],
  question: string
): string => {
  const previous = [...recentTurns(history)]
    .reverse()
    .map((turn) => shorten(turn.question.trim(), MAX_HISTORY_QUESTION_CHARS))
    .find(Boolean);
  return previous ? `${previous}\n${question}` : question;
};

/**
 * Una referencia explícita depende del turno anterior aunque el router encuentre
 * en la pregunta actual palabras del dominio (por ejemplo, «Tribunal Supremo»).
 * La pregunta previa más cercana aporta el asunto; la actual conserva el filtro
 * o la autoridad que el usuario acaba de pedir.
 */
export const retrievalQueryForFollowUp = (
  history: readonly StrategyTurn[],
  question: string
): string =>
  history.length > 0 && questionReferencesHistory(question)
    ? contextualReferenceQuery(history, question)
    : question;

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
    .map((turn) => shorten(turn.question.trim(), MAX_HISTORY_QUESTION_CHARS))
    .filter(Boolean);
  if (previous.length === 0) return question;
  return [...previous, question].join('\n');
};
