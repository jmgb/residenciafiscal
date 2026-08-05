import { type ChatDiagnostic, diagnosticFromError } from './chat-diagnostics';
import {
  type ComparisonReport,
  type ConversationTurn,
  type StrategyAnswer,
  type StrategyId,
  type StrategyTurn,
  unknownCost,
} from './contracts';
import { requestedJudicialAuthority } from './judicial-authority';

export type { StrategyAnswer } from './contracts';

export interface StrategyContext {
  requestId: string;
  signal: AbortSignal;
  /** Turnos anteriores de ESTA estrategia, en orden cronológico. */
  history: StrategyTurn[];
}

export interface NetlifyChatStrategy {
  id: StrategyId;
  answer(question: string, context: StrategyContext): Promise<StrategyAnswer>;
}

interface ComparisonInput {
  question: string;
  requestId: string;
  deadlineMs: number;
  strategies: readonly NetlifyChatStrategy[];
  signal?: AbortSignal;
  history?: readonly ConversationTurn[];
}

/**
 * Proyecta la conversación sobre una estrategia. Conserva los turnos en los que
 * esa estrategia no respondió: la pregunta del usuario es contexto legítimo
 * aunque su respuesta fallara o se abstuviera.
 */
const historyFor = (history: readonly ConversationTurn[], strategy: StrategyId): StrategyTurn[] =>
  history.map((turn) => {
    const own = turn.answers.find((answer) => answer.strategy === strategy)?.content;
    if (own) return { question: turn.question, answer: own };
    // El contenido editorial no lo escribió ninguna estrategia, pero es lo que el
    // usuario tiene delante: las dos lo ven, marcado para que ninguna lo tome por
    // doctrina propia.
    const editorial = turn.answers.find((answer) => answer.strategy === 'editorial')?.content;
    if (editorial) return { question: turn.question, answer: editorial, editorial: true };
    return { question: turn.question, answer: '' };
  });

class DeadlineExceeded extends Error {
  constructor() {
    super('deadline exceeded');
    this.name = 'DeadlineExceeded';
  }
}

const errorAnswer = (
  strategy: StrategyId,
  timeout: boolean,
  latencyMs: number,
  question: string,
  failureCode: 'timeout' | 'exception' | 'strategy_contract',
  errorName: string | null,
  errorContext: ChatDiagnostic | null
): StrategyAnswer => ({
  strategy,
  status: 'error',
  text: '',
  sources: [],
  limits: [
    timeout
      ? 'Tiempo de respuesta agotado.'
      : errorContext?.kind === 'provider_error'
        ? 'El proveedor de esta opción ha fallado; la otra respuesta se conserva de forma independiente.'
        : 'No se ha podido completar esta estrategia.',
  ],
  cost: unknownCost(),
  model: 'unavailable',
  reasoning_effort: null,
  latency_ms: latencyMs,
  diagnostics: {
    authority_intent: requestedJudicialAuthority(question),
    authority_match: 'not_requested',
    retrieval_filter: null,
    retrieved_judgment_ids: [],
    citation_candidates: 0,
    citation_verified: 0,
    failure_code: failureCode,
    error_name: errorName,
    error_context: errorContext,
  },
});

const safeErrorName = (error: unknown): string | null => {
  if (!(error instanceof Error)) return null;
  return /^[A-Za-z][A-Za-z0-9_]{0,39}$/.test(error.name) ? error.name : 'unknown';
};

const abortable = async <T>(operation: Promise<T>, signal: AbortSignal): Promise<T> => {
  if (signal.aborted) throw signal.reason;
  return await Promise.race([
    operation,
    new Promise<never>((_resolve, reject) => {
      signal.addEventListener('abort', () => reject(signal.reason), { once: true });
    }),
  ]);
};

const runIsolated = async (
  strategy: NetlifyChatStrategy,
  question: string,
  context: StrategyContext
): Promise<StrategyAnswer> => {
  const started = performance.now();
  try {
    const answer = await abortable(strategy.answer(question, context), context.signal);
    if (answer.strategy !== strategy.id) {
      return errorAnswer(
        strategy.id,
        false,
        Math.round(performance.now() - started),
        question,
        'strategy_contract',
        null,
        null
      );
    }
    return answer;
  } catch (error) {
    const timeout = error instanceof DeadlineExceeded;
    return errorAnswer(
      strategy.id,
      timeout,
      Math.round(performance.now() - started),
      question,
      timeout ? 'timeout' : 'exception',
      safeErrorName(error),
      timeout
        ? {
            dependency: 'internal',
            operation: 'compareStrategiesInParallel',
            kind: 'deadline_exceeded',
            retryable: true,
          }
        : diagnosticFromError(error)
    );
  }
};

export const compareStrategiesInParallel = async ({
  question,
  requestId,
  deadlineMs,
  strategies,
  signal,
  history = [],
}: ComparisonInput): Promise<ComparisonReport> => {
  if (strategies.length === 0) throw new Error('No hay estrategias de chat habilitadas');
  const controller = new AbortController();
  const abortFromParent = () => controller.abort(signal?.reason);
  signal?.addEventListener('abort', abortFromParent, { once: true });
  const timer = setTimeout(() => controller.abort(new DeadlineExceeded()), deadlineMs);

  try {
    const answers = await Promise.all(
      strategies.map((strategy) =>
        runIsolated(strategy, question, {
          requestId,
          signal: controller.signal,
          history: historyFor(history, strategy.id),
        })
      )
    );
    return {
      schema_version: 'residenciafiscal-chat-comparison/1',
      request_id: requestId,
      experimental: true,
      answers,
    };
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', abortFromParent);
  }
};
