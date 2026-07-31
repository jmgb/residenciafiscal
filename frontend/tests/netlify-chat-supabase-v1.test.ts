import { describe, expect, it, vi } from 'vitest';
import type { ComparisonReport } from '../netlify/functions/chat/contracts';
import { SupabaseChatStore } from '../netlify/functions/chat/supabase-chat-store';

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
      latency_ms: 1_500,
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
      latency_ms: 900,
    },
  ],
};

describe('persistencia privada del chat en Supabase', () => {
  it('reserva presupuesto y guarda la pregunta con identificadores pseudónimos', async () => {
    const rpc = vi.fn(async () => ({
      data: { allowed: true, reservation_microusd: 50_000 },
      error: null,
    }));
    const store = new SupabaseChatStore(
      { rpc },
      {
        dailyLimitMicrousd: 1_000_000,
        reservationMicrousd: 50_000,
      }
    );

    await expect(
      store.reserve({
        requestId: 'chat-request-1',
        conversationId: 'conversation-1',
        userMessageId: 'message-1',
        countryPath: '/espana',
        question: '¿Qué pruebas tiene en cuenta Hacienda?',
      })
    ).resolves.toEqual({ allowed: true, reservationMicrousd: 50_000 });

    expect(rpc).toHaveBeenCalledWith('reserve_chat_request', {
      p_request_id: 'chat-request-1',
      p_conversation_id: 'conversation-1',
      p_user_message_id: 'message-1',
      p_country_path: '/espana',
      p_question: '¿Qué pruebas tiene en cuenta Hacienda?',
      p_daily_limit_microusd: 1_000_000,
      p_reservation_microusd: 50_000,
    });
  });

  it('reconcilia el presupuesto y persiste separadamente las respuestas A y B', async () => {
    const rpc = vi.fn(async () => ({ data: true, error: null }));
    const store = new SupabaseChatStore(
      { rpc },
      {
        dailyLimitMicrousd: 1_000_000,
        reservationMicrousd: 50_000,
      }
    );

    await store.reconcile({
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
          sources: report.answers[0].sources,
        }),
        expect.objectContaining({
          strategy: 'gemini_file_search',
          content: 'Respuesta B',
          cost_microusd: 800,
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
    const store = new SupabaseChatStore(
      { rpc },
      {
        dailyLimitMicrousd: 1_000_000,
        reservationMicrousd: 50_000,
      }
    );

    await expect(
      store.reserve({
        requestId: 'chat-request-1',
        conversationId: 'conversation-1',
        userMessageId: 'message-1',
        countryPath: '/espana',
        question: 'Pregunta',
      })
    ).rejects.toThrow('Supabase no disponible');
  });
});
