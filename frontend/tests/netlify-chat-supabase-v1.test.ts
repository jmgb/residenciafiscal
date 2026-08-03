import { describe, expect, it, vi } from 'vitest';
import { ChatDiagnosticError } from '../netlify/functions/chat/chat-diagnostics';
import type { ComparisonReport } from '../netlify/functions/chat/contracts';
import { SupabaseChatStore } from '../netlify/functions/chat/supabase-chat-store';

const experiment = {
  experiment_version: 'ab-2026-08-03-v3',
  deployed_commit: 'abc1234',
  comparison_schema_version: 'residenciafiscal-chat-comparison/1',
  structured_corpus_version: 'rollout-106',
  structured_prompt_version: 'structured-claims-v3',
  file_search_store: 'fileSearchStores/rollout-106-v2',
  file_search_prompt_version: 'file-search-authority-v6',
} as const;

const report: ComparisonReport = {
  schema_version: 'residenciafiscal-chat-comparison/1',
  request_id: 'chat-request-1',
  experimental: true,
  answers: [
    {
      strategy: 'current_structured',
      status: 'completa',
      text: 'Respuesta A',
      sources: [
        {
          strategy: 'current_structured',
          judgment_id: 'san-1210-2023',
          page: 4,
          source_sha256: 'a'.repeat(64),
          quote: 'Cita literal A',
          verification: 'EXACT',
        },
      ],
      limits: ['Muestra de cinco sentencias.'],
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
      model: 'gpt-5.6-luna',
      reasoning_effort: 'high',
      latency_ms: 1_500,
      claims: [{ text: 'Respuesta A', source_indexes: [1] }],
      diagnostics: {
        authority_intent: null,
        authority_match: 'not_requested',
        retrieval_filter: null,
        retrieved_judgment_ids: ['san-1210-2023'],
        citation_candidates: 1,
        citation_verified: 1,
        failure_code: null,
        error_name: null,
      },
    },
    {
      strategy: 'gemini_file_search',
      status: 'parcial',
      text: 'Respuesta B',
      sources: [],
      limits: [],
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
      model: 'gemini-3.5-flash-lite',
      reasoning_effort: null,
      latency_ms: 900,
    },
  ],
};

describe('persistencia privada del chat en Supabase', () => {
  it('registra la pregunta con identificadores pseudónimos sin reservar dinero', async () => {
    const rpc = vi.fn(async () => ({
      data: { request_id: 'chat-request-1', created: true },
      error: null,
    }));
    const store = new SupabaseChatStore({ rpc }, experiment);

    await expect(
      store.record({
        requestId: 'chat-request-1',
        conversationId: 'conversation-1',
        userMessageId: 'message-1',
        countryPath: '/espana',
        question: '¿Qué pruebas tiene en cuenta Hacienda?',
      })
    ).resolves.toEqual({ requestId: 'chat-request-1' });

    expect(rpc).toHaveBeenCalledWith('create_chat_request', {
      p_request_id: 'chat-request-1',
      p_conversation_id: 'conversation-1',
      p_user_message_id: 'message-1',
      p_country_path: '/espana',
      p_question: '¿Qué pruebas tiene en cuenta Hacienda?',
      p_experiment: experiment,
    });
  });

  it('registra el coste y persiste separadamente las respuestas A y B', async () => {
    const rpc = vi.fn(async () => ({ data: true, error: null }));
    const store = new SupabaseChatStore({ rpc }, experiment);

    await store.complete({
      requestId: 'chat-request-1',
      actualMicrousd: 2_000,
      actualComplete: false,
      report,
    });

    expect(rpc).toHaveBeenCalledWith('complete_chat_request', {
      p_request_id: 'chat-request-1',
      p_actual_microusd: 2_000,
      p_actual_complete: false,
      p_answers: [
        expect.objectContaining({
          strategy: 'current_structured',
          content: 'Respuesta A',
          cost_microusd: 1_200,
          reasoning_effort: 'high',
          sources: report.answers[0].sources,
          claims: report.answers[0].claims,
          diagnostics: report.answers[0].diagnostics,
        }),
        expect.objectContaining({
          strategy: 'gemini_file_search',
          content: 'Respuesta B',
          cost_microusd: 800,
          reasoning_effort: null,
          retrieved_document_tokens: 500,
        }),
      ],
    });
  });

  it('falla cerrado sin filtrar el diagnóstico de Supabase', async () => {
    const rpc = vi.fn(async () => ({
      data: null,
      error: { message: 'Authorization sb_secret_no_debe_salir' },
    }));
    const store = new SupabaseChatStore({ rpc }, experiment);

    await expect(
      store.record({
        requestId: 'chat-request-1',
        conversationId: 'conversation-1',
        userMessageId: 'message-1',
        countryPath: '/espana',
        question: 'Pregunta',
      })
    ).rejects.toThrow('Supabase no disponible');
  });

  it('expone un diagnóstico técnico seguro cuando falla una RPC', async () => {
    const rpc = vi.fn(async () => ({
      data: null,
      error: {
        code: 'PGRST202',
        message: 'Could not find the function public.complete_chat_request with secret prompt',
      },
    }));
    const store = new SupabaseChatStore({ rpc }, experiment);

    await expect(
      store.complete({
        requestId: 'chat-request-1',
        actualMicrousd: 2_000,
        actualComplete: false,
        report,
      })
    ).rejects.toMatchObject({
      constructor: ChatDiagnosticError,
      diagnostic: {
        dependency: 'supabase',
        operation: 'complete_chat_request',
        kind: 'rpc_not_found',
        code: 'PGRST202',
      },
    });
  });

  it('registra un fallo técnico de la consulta', async () => {
    const rpc = vi.fn(async () => ({ data: true, error: null }));
    const store = new SupabaseChatStore({ rpc }, experiment);

    await store.fail({
      requestId: 'chat-request-1',
      status: 'failed',
      failureCode: 'comparison_error',
    });

    expect(rpc).toHaveBeenCalledWith('fail_chat_request', {
      p_request_id: 'chat-request-1',
      p_status: 'failed',
      p_failure_code: 'comparison_error',
    });
  });

  it('registra un único voto ciego con motivo cerrado', async () => {
    const rpc = vi.fn(async () => ({ data: true, error: null }));
    const store = new SupabaseChatStore({ rpc }, experiment);

    await expect(
      store.vote({
        requestId: 'chat-request-1',
        verdict: 'a',
        reason: 'better_grounding',
      })
    ).resolves.toBe(true);

    expect(rpc).toHaveBeenCalledWith('record_chat_vote', {
      p_request_id: 'chat-request-1',
      p_verdict: 'a',
      p_reason: 'better_grounding',
    });
  });
});
