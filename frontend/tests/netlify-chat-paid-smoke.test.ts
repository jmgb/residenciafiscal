// @vitest-environment node

import { describe, expect, it } from 'vitest';
import { CurrentStructuredStrategy } from '../netlify/functions/chat/current-structured-strategy';
import { GeminiFileSearchStrategy } from '../netlify/functions/chat/file-search-strategy';
import {
  productionCorpus,
  productionVerbatimArtifacts,
} from '../netlify/functions/chat/production-corpus';
import {
  createGeminiInteraction,
  createOpenAIWriter,
} from '../netlify/functions/chat/provider-adapters';

Object.assign(globalThis, {
  document: { head: { innerHTML: '' } },
  window: {},
});

const QUESTION =
  'si una persona se apunta al gym o si usa su teléfono movil en españa, esto la agencia tributaria lo tiene en cuenta para el computo de los 183 días?';
const RUN_PAID_SMOKE =
  process.env.RUN_PAID_CHAT_SMOKE === 'true' && process.env.CONFIRM_PAID === '1';
const context = () => ({
  requestId: 'paid-smoke-gym-phone',
  signal: AbortSignal.timeout(50_000),
  history: [],
});

describe.runIf(RUN_PAID_SMOKE)('smoke pagado A/B para gimnasio y teléfono', () => {
  it('A responde parcialmente y cita el indicio de cuotas de gimnasio', async () => {
    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey) throw new Error('OPENAI_API_KEY ausente');
    const strategy = new CurrentStructuredStrategy(
      productionCorpus,
      createOpenAIWriter(apiKey),
      productionVerbatimArtifacts
    );

    const answer = await strategy.answer(QUESTION, context());

    expect({
      status: answer.status,
      sourceCount: answer.sources.length,
      citationCandidates: answer.diagnostics?.citation_candidates,
      citationVerified: answer.diagnostics?.citation_verified,
      failureCode: answer.diagnostics?.failure_code,
      limits: answer.limits,
    }).toEqual({
      status: 'parcial',
      sourceCount: expect.any(Number),
      citationCandidates: expect.any(Number),
      citationVerified: expect.any(Number),
      failureCode: null,
      limits: expect.any(Array),
    });
    expect(answer.text.toLocaleLowerCase('es')).toContain('gimnas');
    expect(answer.sources.some((source) => source.judgment_id === 'san-2347-2022')).toBe(true);
  }, 55_000);

  it('B devuelve una respuesta parcial con al menos una cita verificable', async () => {
    const apiKey = process.env.GEMINI_API_KEY;
    const storeName = process.env.CHAT_FILE_SEARCH_STORE_NAME;
    if (!apiKey || !storeName) throw new Error('Configuración Gemini ausente');
    const strategy = new GeminiFileSearchStrategy({
      storeName,
      artifacts: productionVerbatimArtifacts,
      interact: createGeminiInteraction(apiKey),
      model: process.env.CHAT_FILE_SEARCH_MODEL || 'gemini-3.5-flash-lite',
    });

    const answer = await strategy.answer(QUESTION, context());

    expect({
      status: answer.status,
      sourceCount: answer.sources.length,
      citationCandidates: answer.diagnostics?.citation_candidates,
      citationVerified: answer.diagnostics?.citation_verified,
      failureCode: answer.diagnostics?.failure_code,
    }).toEqual({
      status: 'parcial',
      sourceCount: expect.any(Number),
      citationCandidates: expect.any(Number),
      citationVerified: expect.any(Number),
      failureCode: null,
    });
    expect(answer.text).not.toBe('');
    expect(answer.sources.length).toBeGreaterThan(0);
  }, 55_000);
});
