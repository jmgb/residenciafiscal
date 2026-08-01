import { beforeEach, describe, expect, it, vi } from 'vitest';

const { createClient, rpc } = vi.hoisted(() => ({
  createClient: vi.fn(),
  rpc: vi.fn(),
}));

vi.mock('@supabase/supabase-js', () => ({ createClient }));
vi.mock('@google/genai', () => ({
  GoogleGenAI: class GoogleGenAI {
    interactions = { create: vi.fn() };
  },
}));
vi.mock('openai', () => ({
  default: class OpenAI {
    responses = { create: vi.fn() };
  },
}));

import { createProductionDependencies } from '../netlify/functions/chat/composition';
import type { ComparisonReport } from '../netlify/functions/chat/contracts';

const environment = {
  CHAT_COMPARISON_ENABLED: 'true',
  OPENAI_API_KEY: 'openai-test',
  GEMINI_API_KEY: 'gemini-test',
  CHAT_FILE_SEARCH_STORE_NAME: 'fileSearchStores/test',
  CHAT_FILE_SEARCH_MODEL: 'gemini-3.5-flash-lite',
  CHAT_DEADLINE_MS: '52000',
  SUPABASE_URL: 'https://project.supabase.co',
  SUPABASE_SECRET_KEY: 'sb_secret_test',
} as NodeJS.ProcessEnv;

beforeEach(() => {
  createClient.mockReset();
  rpc.mockReset();
  createClient.mockReturnValue({ rpc });
});

describe('composition root de la Function con Supabase', () => {
  it('permanece cerrado si falta la clave secreta de Supabase', () => {
    const dependencies = createProductionDependencies({
      ...environment,
      SUPABASE_SECRET_KEY: undefined,
    });

    expect(dependencies.enabled).toBe(false);
    expect(createClient).not.toHaveBeenCalled();
  });

  it('crea un cliente exclusivamente server-side y conecta el registro privado', async () => {
    rpc.mockResolvedValueOnce({
      data: { request_id: 'chat-request-1', created: true },
      error: null,
    });
    const dependencies = createProductionDependencies(environment);

    expect(dependencies.enabled).toBe(true);
    expect(createClient).toHaveBeenCalledWith(
      'https://project.supabase.co',
      'sb_secret_test',
      expect.objectContaining({
        auth: expect.objectContaining({ persistSession: false, autoRefreshToken: false }),
      })
    );
    await expect(
      dependencies.recordRequest({
        requestId: 'chat-request-1',
        conversationId: 'conversation-1',
        userMessageId: 'message-1',
        countryPath: '/espana',
        question: 'Pregunta',
      })
    ).resolves.toEqual({ requestId: 'chat-request-1' });
  });

  it('registra coste y tokens de A/B sin registrar el contenido fiscal', async () => {
    rpc.mockResolvedValueOnce({ data: true, error: null });
    const log = vi.spyOn(console, 'info').mockImplementation(() => undefined);
    const dependencies = createProductionDependencies(environment);
    const report: ComparisonReport = {
      schema_version: 'residenciafiscal-chat-comparison/1',
      request_id: 'chat-request-1',
      experimental: true,
      answers: [
        {
          strategy: 'current_structured',
          status: 'completa',
          text: 'Dato fiscal que no debe aparecer en logs',
          sources: [],
          limits: [],
          model: 'gpt-5.6-luna',
          latency_ms: 1_500,
          cost: {
            currency: 'USD',
            amount_usd: '0.001200',
            cost_microusd: 1_200,
            measurement: 'ACTUAL',
            scope: 'REQUEST_MARGINAL',
            pricing_version: 'test',
            input_tokens: 100,
            output_tokens: 20,
            retrieved_document_tokens: 0,
            excludes_corpus_preparation: true,
          },
        },
        {
          strategy: 'gemini_file_search',
          status: 'parcial',
          text: 'Otra respuesta privada',
          sources: [],
          limits: [],
          model: 'gemini-3.5-flash-lite',
          latency_ms: 900,
          cost: {
            currency: 'USD',
            amount_usd: '0.000800',
            cost_microusd: 800,
            measurement: 'ESTIMATED',
            scope: 'REQUEST_MARGINAL',
            pricing_version: 'test',
            input_tokens: 80,
            output_tokens: 15,
            retrieved_document_tokens: 500,
            excludes_corpus_preparation: true,
          },
        },
      ],
    };

    await dependencies.completeRequest({
      requestId: 'chat-request-1',
      actualMicrousd: 2_000,
      actualComplete: false,
      report,
    });

    const serialized = String(log.mock.calls[0]?.[0]);
    expect(JSON.parse(serialized)).toMatchObject({
      event: 'chat_cost_reconciled',
      request_id: 'chat-request-1',
      actual_microusd: 2_000,
      strategies: [
        { strategy: 'current_structured', cost_microusd: 1_200, input_tokens: 100 },
        { strategy: 'gemini_file_search', cost_microusd: 800, input_tokens: 80 },
      ],
    });
    expect(serialized).not.toContain('Dato fiscal');
    expect(serialized).not.toContain('Otra respuesta');
  });
});
