import { describe, expect, it } from 'vitest';
import {
  compareStrategiesInParallel,
  type NetlifyChatStrategy,
  type StrategyAnswer,
} from '../netlify/functions/chat/runtime';

const zeroCost = {
  currency: 'USD' as const,
  amount_usd: '0.000000',
  cost_microusd: 0,
  measurement: 'ACTUAL' as const,
  scope: 'REQUEST_MARGINAL' as const,
  pricing_version: 'test',
  input_tokens: 0,
  output_tokens: 0,
  retrieved_document_tokens: 0,
  excludes_corpus_preparation: true as const,
};

const answer = (strategy: StrategyAnswer['strategy'], text: string = strategy): StrategyAnswer => ({
  strategy,
  status: 'completa',
  text,
  sources: [],
  limits: [],
  cost: zeroCost,
  model: 'test-model',
  reasoning_effort: null,
  latency_ms: 1,
});

describe('runtime comparativo Netlify V1', () => {
  it('inicia A y B en paralelo y conserva el orden estable A → B', async () => {
    const started: string[] = [];
    let release: (() => void) | undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const strategy = (id: StrategyAnswer['strategy']): NetlifyChatStrategy => ({
      id,
      async answer() {
        started.push(id);
        await gate;
        return answer(id);
      },
    });

    const comparison = compareStrategiesInParallel({
      question: '¿Qué tiene en cuenta Hacienda?',
      requestId: 'request-1',
      deadlineMs: 1_000,
      strategies: [strategy('current_structured'), strategy('gemini_file_search')],
    });
    await Promise.resolve();

    expect(started).toEqual(['current_structured', 'gemini_file_search']);
    release?.();
    await expect(comparison).resolves.toMatchObject({
      request_id: 'request-1',
      answers: [{ strategy: 'current_structured' }, { strategy: 'gemini_file_search' }],
    });
  });

  it('aísla el fallo de una estrategia y conserva la otra', async () => {
    const failing: NetlifyChatStrategy = {
      id: 'current_structured',
      async answer() {
        throw new Error('Authorization: Bearer secreto');
      },
    };
    const working: NetlifyChatStrategy = {
      id: 'gemini_file_search',
      async answer() {
        return answer('gemini_file_search', 'respuesta disponible');
      },
    };

    const report = await compareStrategiesInParallel({
      question: 'pregunta',
      requestId: 'request-2',
      deadlineMs: 1_000,
      strategies: [failing, working],
    });

    expect(report.answers[0]).toMatchObject({
      strategy: 'current_structured',
      status: 'error',
      text: '',
      limits: ['No se ha podido completar esta estrategia.'],
      cost: {
        amount_usd: null,
        cost_microusd: null,
        measurement: 'UNAVAILABLE',
      },
    });
    expect(JSON.stringify(report)).not.toContain('secreto');
    expect(report.answers[1].text).toBe('respuesta disponible');
  });

  it('cancela ambas estrategias al alcanzar el deadline interno', async () => {
    const hanging = (id: StrategyAnswer['strategy']): NetlifyChatStrategy => ({
      id,
      answer(_question, context) {
        return new Promise((_resolve, reject) => {
          context.signal.addEventListener('abort', () => reject(context.signal.reason), {
            once: true,
          });
        });
      },
    });
    const startedAt = performance.now();

    const report = await compareStrategiesInParallel({
      question: 'pregunta',
      requestId: 'request-3',
      deadlineMs: 20,
      strategies: [hanging('current_structured'), hanging('gemini_file_search')],
    });

    expect(performance.now() - startedAt).toBeLessThan(250);
    expect(report.answers.map((item) => item.status)).toEqual(['error', 'error']);
    expect(report.answers.every((item) => item.limits[0] === 'Tiempo de respuesta agotado.')).toBe(
      true
    );
    expect(report.answers.every((item) => item.latency_ms > 0)).toBe(true);
  });
});
