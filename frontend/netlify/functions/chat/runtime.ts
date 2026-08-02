import {
  type ComparisonReport,
  type StrategyAnswer,
  type StrategyId,
  unknownCost,
} from './contracts';
import { requestedJudicialAuthority } from './judicial-authority';

export type { StrategyAnswer } from './contracts';

export interface StrategyContext {
  requestId: string;
  signal: AbortSignal;
}

export interface NetlifyChatStrategy {
  id: StrategyId;
  answer(question: string, context: StrategyContext): Promise<StrategyAnswer>;
}

interface ComparisonInput {
  question: string;
  requestId: string;
  deadlineMs: number;
  strategies: [NetlifyChatStrategy, NetlifyChatStrategy];
  signal?: AbortSignal;
}

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
  errorName: string | null
): StrategyAnswer => ({
  strategy,
  status: 'error',
  text: '',
  sources: [],
  limits: [timeout ? 'Tiempo de respuesta agotado.' : 'No se ha podido completar esta estrategia.'],
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
      safeErrorName(error)
    );
  }
};

export const compareStrategiesInParallel = async ({
  question,
  requestId,
  deadlineMs,
  strategies,
  signal,
}: ComparisonInput): Promise<ComparisonReport> => {
  const controller = new AbortController();
  const abortFromParent = () => controller.abort(signal?.reason);
  signal?.addEventListener('abort', abortFromParent, { once: true });
  const timer = setTimeout(() => controller.abort(new DeadlineExceeded()), deadlineMs);
  const context = { requestId, signal: controller.signal };

  try {
    const answers = await Promise.all([
      runIsolated(strategies[0], question, context),
      runIsolated(strategies[1], question, context),
    ]);
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
