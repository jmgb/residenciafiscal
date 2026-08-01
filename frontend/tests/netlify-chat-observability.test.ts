import { afterEach, describe, expect, it, vi } from 'vitest';
import { createChatHandler } from '../netlify/functions/chat/chat';
import {
  ConsoleChatObservability,
  createChatObservability,
  parseSentryDsn,
  SentryChatObservability,
} from '../netlify/functions/chat/observability';

const DSN = 'https://abc123def456@o4507.ingest.sentry.io/4511837035233280';

const costEvent = {
  requestId: 'chat-1',
  actualMicrousd: 4542,
  actualComplete: true,
  strategies: [
    {
      strategy: 'current_structured',
      status: 'completa',
      model: 'gpt-5.6-luna',
      reasoning_effort: 'high',
      latency_ms: 20230,
      cost_microusd: 2491,
      measurement: 'ACTUAL',
      input_tokens: 10,
      output_tokens: 20,
      retrieved_document_tokens: 0,
    },
  ],
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe('parseSentryDsn', () => {
  it('deriva endpoint de envelope y clave pública', () => {
    expect(parseSentryDsn(DSN)).toEqual({
      endpoint: 'https://o4507.ingest.sentry.io/api/4511837035233280/envelope/',
      publicKey: 'abc123def456',
    });
  });

  it('devuelve null ante un DSN inservible', () => {
    expect(parseSentryDsn('no-es-una-url')).toBeNull();
    expect(parseSentryDsn('https://o4507.ingest.sentry.io/')).toBeNull();
    expect(parseSentryDsn('')).toBeNull();
  });
});

describe('ConsoleChatObservability', () => {
  it('conserva el contrato exacto de chat_request_failed', async () => {
    const errorLog = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    await new ConsoleChatObservability().recordFailure({
      requestId: 'chat-1',
      failureCode: 'comparison_error',
      stage: 'compare',
      status: 'failed',
      errorName: 'TypeError',
    });

    expect(errorLog).toHaveBeenCalledWith(
      JSON.stringify({
        event: 'chat_request_failed',
        request_id: 'chat-1',
        failure_code: 'comparison_error',
        stage: 'compare',
        status: 'failed',
      })
    );
  });

  it('omite status cuando el fallo no lo tiene', async () => {
    const errorLog = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    await new ConsoleChatObservability().recordFailure({
      requestId: 'chat-1',
      failureCode: 'record_error',
      stage: 'record',
    });

    expect(errorLog).toHaveBeenCalledWith(
      JSON.stringify({
        event: 'chat_request_failed',
        request_id: 'chat-1',
        failure_code: 'record_error',
        stage: 'record',
      })
    );
  });

  it('conserva el contrato de chat_cost_reconciled', async () => {
    const infoLog = vi.spyOn(console, 'info').mockImplementation(() => undefined);
    await new ConsoleChatObservability().recordCost(costEvent);

    expect(infoLog).toHaveBeenCalledWith(
      JSON.stringify({
        event: 'chat_cost_reconciled',
        request_id: 'chat-1',
        actual_microusd: 4542,
        actual_complete: true,
        strategies: costEvent.strategies,
      })
    );
  });
});

describe('SentryChatObservability', () => {
  const sentryCall = (fetchMock: ReturnType<typeof vi.fn>) => {
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const lines = String(init.body).trim().split('\n');
    return {
      url,
      init,
      envelopeHeader: JSON.parse(lines[0]),
      itemHeader: JSON.parse(lines[1]),
      payload: JSON.parse(lines[2]),
      rawBody: String(init.body),
    };
  };

  it('envía un envelope al endpoint derivado del DSN', async () => {
    const fetchMock = vi.fn(async () => new Response('', { status: 200 }));
    const observability = new SentryChatObservability({
      dsn: DSN,
      environment: 'production',
      fetchImpl: fetchMock as unknown as typeof fetch,
      inner: new ConsoleChatObservability(),
    });
    vi.spyOn(console, 'error').mockImplementation(() => undefined);

    await observability.recordFailure({
      requestId: 'chat-1',
      failureCode: 'comparison_error',
      stage: 'compare',
      status: 'failed',
      errorName: 'TypeError',
    });

    const call = sentryCall(fetchMock);
    expect(call.url).toBe('https://o4507.ingest.sentry.io/api/4511837035233280/envelope/');
    expect(call.init.method).toBe('POST');
    expect(String((call.init.headers as Record<string, string>)['X-Sentry-Auth'])).toContain(
      'sentry_key=abc123def456'
    );
    expect(call.itemHeader).toEqual({ type: 'event' });
    expect(call.payload.tags).toMatchObject({
      failure_code: 'comparison_error',
      stage: 'compare',
      status: 'failed',
      error_name: 'TypeError',
      component: 'netlify-function',
      service: 'residencia-fiscal',
    });
    expect(call.payload.extra).toEqual({ request_id: 'chat-1' });
    expect(call.payload.fingerprint).toEqual([
      'chat_request_failed',
      'comparison_error',
      'compare',
    ]);
    expect(call.payload.environment).toBe('production');
    expect(call.envelopeHeader.event_id).toMatch(/^[0-9a-f]{32}$/);
  });

  it('no emite ninguna estructura capaz de transportar datos de la petición', async () => {
    const fetchMock = vi.fn(async () => new Response('', { status: 200 }));
    const observability = new SentryChatObservability({
      dsn: DSN,
      environment: 'production',
      fetchImpl: fetchMock as unknown as typeof fetch,
      inner: new ConsoleChatObservability(),
    });
    vi.spyOn(console, 'error').mockImplementation(() => undefined);

    await observability.recordFailure({
      requestId: 'chat-1',
      failureCode: 'comparison_error',
      stage: 'compare',
    });

    const { payload } = sentryCall(fetchMock);
    for (const forbidden of [
      'request',
      'user',
      'breadcrumbs',
      'contexts',
      'exception',
      'modules',
    ]) {
      expect(payload).not.toHaveProperty(forbidden);
    }
  });

  it('sanea error_name para que solo viaje un identificador de clase', async () => {
    const fetchMock = vi.fn(async () => new Response('', { status: 200 }));
    const observability = new SentryChatObservability({
      dsn: DSN,
      environment: 'production',
      fetchImpl: fetchMock as unknown as typeof fetch,
      inner: new ConsoleChatObservability(),
    });
    vi.spyOn(console, 'error').mockImplementation(() => undefined);

    await observability.recordFailure({
      requestId: 'chat-1',
      failureCode: 'comparison_error',
      stage: 'compare',
      errorName: 'Error: la pregunta del contribuyente era 183 días en Andorra',
    });

    const { payload, rawBody } = sentryCall(fetchMock);
    expect(payload.tags.error_name).toBe('unknown');
    expect(rawBody).not.toContain('Andorra');
  });

  it('no manda el coste a Sentry: no es un error', async () => {
    const fetchMock = vi.fn(async () => new Response('', { status: 200 }));
    const observability = new SentryChatObservability({
      dsn: DSN,
      environment: 'production',
      fetchImpl: fetchMock as unknown as typeof fetch,
      inner: new ConsoleChatObservability(),
    });
    const infoLog = vi.spyOn(console, 'info').mockImplementation(() => undefined);

    await observability.recordCost(costEvent);

    expect(fetchMock).not.toHaveBeenCalled();
    expect(infoLog).toHaveBeenCalledOnce();
  });

  it('nunca propaga un fallo de Sentry al chat', async () => {
    const fetchMock = vi.fn(async () => {
      throw new Error('sentry caído');
    });
    const observability = new SentryChatObservability({
      dsn: DSN,
      environment: 'production',
      fetchImpl: fetchMock as unknown as typeof fetch,
      inner: new ConsoleChatObservability(),
    });
    const errorLog = vi.spyOn(console, 'error').mockImplementation(() => undefined);

    await expect(
      observability.recordFailure({
        requestId: 'chat-1',
        failureCode: 'comparison_error',
        stage: 'compare',
      })
    ).resolves.toBeUndefined();
    expect(errorLog).toHaveBeenCalledOnce();
  });
});

describe('handler real conectado a Sentry', () => {
  it('no filtra la pregunta ni el mensaje del proveedor al fallar la comparación', async () => {
    const fetchMock = vi.fn(
      async (_url: string, _init: RequestInit) => new Response('', { status: 200 })
    );
    const observability = new SentryChatObservability({
      dsn: DSN,
      environment: 'production',
      fetchImpl: fetchMock as unknown as typeof fetch,
      inner: new ConsoleChatObservability(),
    });
    vi.spyOn(console, 'error').mockImplementation(() => undefined);

    const response = await createChatHandler({
      enabled: true,
      observability,
      recordRequest: async ({ requestId }) => ({ requestId }),
      compare: async () => {
        throw new Error(
          'upstream 500 al resolver "¿183 días en Andorra cuentan?" con postgresql://u:secreto@host'
        );
      },
      failRequest: async () => undefined,
      completeRequest: async () => undefined,
    })(
      new Request('https://residenciafiscal.org/api/chat', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          messages: [{ role: 'user', content: '¿183 días en Andorra cuentan?' }],
        }),
      })
    );

    expect(response.status).toBe(503);
    expect(fetchMock).toHaveBeenCalledOnce();
    const body = String(fetchMock.mock.calls[0][1].body);
    // Términos no hexadecimales a propósito: el event_id es hex aleatorio y una
    // subcadena como «183» colisionaría por azar, volviendo el test inestable.
    for (const secret of ['Andorra', 'días', 'secreto', 'postgresql', 'upstream']) {
      expect(body).not.toContain(secret);
    }
    expect(JSON.parse(body.trim().split('\n')[2]).tags).toMatchObject({
      failure_code: 'comparison_error',
      stage: 'compare',
      status: 'failed',
      error_name: 'Error',
    });
  });
});

describe('createChatObservability', () => {
  it('sin activación explícita devuelve solo el sink de consola', () => {
    expect(createChatObservability({ CHAT_SENTRY_DSN: DSN })).toBeInstanceOf(
      ConsoleChatObservability
    );
    expect(
      createChatObservability({ CHAT_SENTRY_ENABLED: 'true', CHAT_SENTRY_DSN: '' })
    ).toBeInstanceOf(ConsoleChatObservability);
    expect(
      createChatObservability({ CHAT_SENTRY_ENABLED: 'true', CHAT_SENTRY_DSN: 'roto' })
    ).toBeInstanceOf(ConsoleChatObservability);
  });

  it('con bandera y DSN válidos envuelve el sink de consola en el de Sentry', () => {
    expect(
      createChatObservability({ CHAT_SENTRY_ENABLED: 'true', CHAT_SENTRY_DSN: DSN })
    ).toBeInstanceOf(SentryChatObservability);
  });
});
