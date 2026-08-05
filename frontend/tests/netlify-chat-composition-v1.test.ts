import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

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

import {
  createProductionDependencies,
  resolveEnabledStrategyIds,
} from '../netlify/functions/chat/composition';
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

afterEach(() => {
  vi.restoreAllMocks();
});

describe('composition root de la Function con Supabase', () => {
  it('resuelve A y B de forma independiente bajo el interruptor maestro', () => {
    expect(
      resolveEnabledStrategyIds({
        CHAT_COMPARISON_ENABLED: 'true',
        CHAT_STRATEGY_A_ENABLED: 'true',
        CHAT_STRATEGY_B_ENABLED: 'false',
      })
    ).toEqual(['current_structured']);
    expect(
      resolveEnabledStrategyIds({
        CHAT_COMPARISON_ENABLED: 'true',
        CHAT_STRATEGY_A_ENABLED: 'false',
        CHAT_STRATEGY_B_ENABLED: 'true',
      })
    ).toEqual(['gemini_file_search']);
  });

  it('permite activar solo A sin exigir la configuración de B', () => {
    const dependencies = createProductionDependencies({
      ...environment,
      CHAT_STRATEGY_A_ENABLED: 'true',
      CHAT_STRATEGY_B_ENABLED: 'false',
      GEMINI_API_KEY: undefined,
      CHAT_FILE_SEARCH_STORE_NAME: undefined,
    });

    expect(dependencies.enabled).toBe(true);
  });

  it('permite activar solo B sin exigir la configuración de A', () => {
    const dependencies = createProductionDependencies({
      ...environment,
      CHAT_STRATEGY_A_ENABLED: 'false',
      CHAT_STRATEGY_B_ENABLED: 'true',
      OPENAI_API_KEY: undefined,
    });

    expect(dependencies.enabled).toBe(true);
  });

  it('permanece cerrado si A y B están desactivadas', () => {
    const dependencies = createProductionDependencies({
      ...environment,
      CHAT_STRATEGY_A_ENABLED: 'false',
      CHAT_STRATEGY_B_ENABLED: 'false',
    });

    expect(dependencies.enabled).toBe(false);
  });

  it('permanece cerrado si falta la clave secreta de Supabase', () => {
    const dependencies = createProductionDependencies({
      ...environment,
      SUPABASE_SECRET_KEY: undefined,
    });

    expect(dependencies.enabled).toBe(false);
    expect(createClient).not.toHaveBeenCalled();
  });

  it('explica qué comprobaciones de configuración fallaron sin incluir secretos', () => {
    const dependencies = createProductionDependencies({
      ...environment,
      CHAT_COMPARISON_ENABLED: 'false',
      GEMINI_API_KEY: undefined,
      CHAT_FILE_SEARCH_STORE_NAME: 'invalid-store',
    });

    expect(dependencies.enabled).toBe(false);
    expect(dependencies.disabledDiagnostic).toMatchObject({
      dependency: 'configuration',
      operation: 'createProductionDependencies',
      kind: 'chat_disabled',
      missing: ['CHAT_COMPARISON_ENABLED', 'GEMINI_API_KEY', 'CHAT_FILE_SEARCH_STORE_NAME'],
    });
    expect(JSON.stringify(dependencies.disabledDiagnostic)).not.toContain('openai-test');
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
    expect(rpc).toHaveBeenCalledWith(
      'create_chat_request',
      expect.objectContaining({
        p_experiment: expect.objectContaining({
          experiment_version: 'ab-2026-08-04-v5',
          structured_prompt_version: 'structured-claims-v6',
          file_search_prompt_version: 'file-search-authority-v9',
        }),
      })
    );
  });

  it('registra coste y tokens de A/B sin registrar el contenido fiscal', async () => {
    rpc.mockResolvedValueOnce({ data: true, error: null });
    const log = vi.spyOn(console, 'info').mockImplementation(() => undefined);
    const errorLog = vi.spyOn(console, 'error').mockImplementation(() => undefined);
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
          reasoning_effort: 'high',
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
          status: 'error',
          text: 'Otra respuesta privada',
          sources: [],
          limits: [],
          model: 'gemini-3.5-flash-lite',
          reasoning_effort: null,
          latency_ms: 900,
          diagnostics: {
            authority_intent: 'tribunal_supremo',
            authority_match: 'missing',
            retrieval_filter: 'authority="tribunal_supremo"',
            retrieved_judgment_ids: [],
            citation_candidates: 1,
            citation_verified: 0,
            failure_code: 'citation_verification',
            error_name: 'TypeError',
          },
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
      authorityIntent: 'tribunal_supremo',
      timingsMs: { record: 10, compare: 1_500, beforePersistence: 1_520 },
    });

    const serialized = String(log.mock.calls[0]?.[0]);
    expect(JSON.parse(serialized)).toMatchObject({
      schema_version: 'residenciafiscal-chat-observability/1',
      event: 'chat_cost_reconciled',
      request_id: 'chat-request-1',
      request_status: 'completed',
      actual_microusd: 2_000,
      cost_measurement_complete: false,
      authority_intent: 'tribunal_supremo',
      timings_ms: {
        record: 10,
        compare: 1_500,
        persistence: expect.any(Number),
        total: expect.any(Number),
      },
      strategies: [
        {
          strategy: 'current_structured',
          cost_microusd: 1_200,
          input_tokens: 100,
          source_count: 0,
          document_token_accounting: 'not_applicable',
        },
        {
          strategy: 'gemini_file_search',
          cost_microusd: 800,
          input_tokens: 80,
          source_count: 0,
          document_token_accounting: 'reported',
        },
      ],
    });
    expect(serialized).not.toContain('Dato fiscal');
    expect(serialized).not.toContain('Otra respuesta');
    expect(errorLog).toHaveBeenCalledOnce();
    expect(JSON.parse(String(errorLog.mock.calls[0]?.[0]))).toMatchObject({
      schema_version: 'residenciafiscal-chat-observability/1',
      event: 'chat_strategy_failed',
      request_id: 'chat-request-1',
      strategy: 'gemini_file_search',
      failure_code: 'citation_verification',
      error_name: 'TypeError',
      latency_ms: 900,
    });
  });
});
