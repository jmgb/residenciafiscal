import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  type ChatFunctionDependencies,
  config,
  createChatHandler,
  serializeComparison,
} from '../netlify/functions/chat/chat';
import { ChatDiagnosticError } from '../netlify/functions/chat/chat-diagnostics';
import type { ComparisonReport, ConversationTurn } from '../netlify/functions/chat/contracts';
import { ConsoleChatObservability } from '../netlify/functions/chat/observability';
import { parseChatEventStream } from '../src/lib/chat-sse-protocol';

const report: ComparisonReport = {
  schema_version: 'residenciafiscal-chat-comparison/1' as const,
  request_id: 'chat-test',
  experimental: true as const,
  answers: [
    {
      strategy: 'current_structured' as const,
      status: 'completa' as const,
      text: 'Respuesta A',
      claims: [{ text: 'Respuesta A', source_indexes: [] }],
      sources: [],
      limits: [],
      cost: {
        currency: 'USD' as const,
        amount_usd: '0.000001',
        cost_microusd: 1,
        measurement: 'ACTUAL' as const,
        scope: 'REQUEST_MARGINAL' as const,
        pricing_version: 'test',
        input_tokens: 1,
        output_tokens: 1,
        retrieved_document_tokens: 0,
        excludes_corpus_preparation: true as const,
      },
      model: 'gpt-5.6-luna',
      reasoning_effort: 'high',
      latency_ms: 10,
    },
    {
      strategy: 'gemini_file_search' as const,
      status: 'completa' as const,
      text: 'Respuesta B',
      sources: [],
      limits: [],
      cost: {
        currency: 'USD' as const,
        amount_usd: '0.000002',
        cost_microusd: 2,
        measurement: 'ACTUAL' as const,
        scope: 'REQUEST_MARGINAL' as const,
        pricing_version: 'test',
        input_tokens: 1,
        output_tokens: 1,
        retrieved_document_tokens: 0,
        excludes_corpus_preparation: true as const,
      },
      model: 'gemini-test',
      reasoning_effort: null,
      latency_ms: 12,
    },
  ],
};

const CONVERSATION_ACCESS_TOKEN = 'a'.repeat(64);

const request = (body: unknown, includeAccessToken = true) =>
  new Request('https://residenciafiscal.org/api/chat', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(
      includeAccessToken && body && typeof body === 'object'
        ? { ...body, conversation_access_token: CONVERSATION_ACCESS_TOKEN }
        : body
    ),
  });

const dependencies = (
  overrides: Partial<ChatFunctionDependencies> = {}
): ChatFunctionDependencies => ({
  enabled: true,
  observability: new ConsoleChatObservability(),
  recordRequest: vi.fn(async ({ requestId }) => ({ requestId })),
  loadHistory: vi.fn(async () => []),
  compare: vi.fn(async () => report),
  completeRequest: vi.fn(async () => undefined),
  failRequest: vi.fn(async () => undefined),
  ...overrides,
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('Netlify Function /api/chat V1', () => {
  it('declara POST, ruta y rate limit', () => {
    expect(config).toMatchObject({
      path: '/api/chat',
      method: 'POST',
      rateLimit: { aggregateBy: ['ip', 'domain'], windowSize: 60, windowLimit: 5 },
    });
  });

  it('permanece cerrada sin activación server-side', async () => {
    const errorLog = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const deps = dependencies({ enabled: false });
    const response = await createChatHandler(deps)(request({ messages: [] }));

    expect(response.status).toBe(503);
    expect(deps.compare).not.toHaveBeenCalled();
    expect(JSON.parse(String(errorLog.mock.calls[0]?.[0]))).toMatchObject({
      event: 'chat_request_failed',
      failure_code: 'configuration_error',
      stage: 'record',
      error_context: {
        dependency: 'configuration',
        operation: 'chat_handler',
        kind: 'chat_disabled',
      },
    });
  });

  it('falla cerrado si no puede registrar la consulta', async () => {
    let attemptedRequestId = '';
    const errorLog = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const deps = dependencies({
      recordRequest: vi.fn(async ({ requestId }) => {
        attemptedRequestId = requestId;
        throw new Error('ledger unavailable');
      }),
    });
    const response = await createChatHandler(deps)(
      request({ messages: [{ role: 'user', content: 'pregunta' }] })
    );

    expect(response.status).toBe(503);
    expect(deps.compare).not.toHaveBeenCalled();
    expect(JSON.parse(String(errorLog.mock.calls[0]?.[0]))).toMatchObject({
      event: 'chat_request_failed',
      request_id: attemptedRequestId,
      failure_code: 'record_error',
      stage: 'record',
      error_name: 'Error',
      latency_ms: expect.any(Number),
    });
  });

  it('aísla a un cliente anterior al despliegue en un hilo efímero protegido', async () => {
    const deps = dependencies();

    const response = await createChatHandler(deps)(
      request(
        {
          conversation_id: 'conversation-visible-en-la-url',
          messages: [{ role: 'user', content: 'repite lo anterior' }],
        },
        false
      )
    );

    expect(response.status).toBe(200);
    const recorded = vi.mocked(deps.recordRequest).mock.calls[0]?.[0];
    expect(recorded?.conversationId).toMatch(/^conversation-/);
    expect(recorded?.conversationId).not.toBe('conversation-visible-en-la-url');
    expect(recorded?.conversationAccessHash).toMatch(/^[0-9a-f]{64}$/);
    expect(deps.loadHistory).toHaveBeenCalledWith(
      recorded?.conversationId,
      recorded?.conversationAccessHash
    );
  });

  it('rechaza un secreto de posesión presente pero mal formado', async () => {
    const deps = dependencies();
    const response = await createChatHandler(deps)(
      request(
        {
          conversation_access_token: 'no-es-un-secreto',
          messages: [{ role: 'user', content: 'pregunta' }],
        },
        false
      )
    );

    expect(response.status).toBe(400);
    expect(deps.recordRequest).not.toHaveBeenCalled();
  });

  // El historial sale del ledger por conversación, no del cuerpo de la petición.
  it('recupera el hilo de la conversación y se lo entrega al comparador', async () => {
    const history = [
      {
        question: '¿Cuántos días exige el artículo 9?',
        answers: [{ strategy: 'current_structured' as const, content: 'Más de 183 días.' }],
      },
    ];
    const deps = dependencies({ loadHistory: vi.fn(async () => history) });

    const response = await createChatHandler(deps)(
      request({
        messages: [{ role: 'user', content: 'dame un ejemplo de lo anterior' }],
        conversation_id: 'conversation-1',
      })
    );

    expect(response.status).toBe(200);
    expect(deps.loadHistory).toHaveBeenCalledWith(
      'conversation-1',
      expect.stringMatching(/^[0-9a-f]{64}$/)
    );
    expect(deps.loadHistory).not.toHaveBeenCalledWith('conversation-1', CONVERSATION_ACCESS_TOKEN);
    expect(deps.compare).toHaveBeenCalledWith(
      'dame un ejemplo de lo anterior',
      expect.stringMatching(/^chat-/),
      expect.anything(),
      history
    );
  });

  // Sin historial se responde igual que siempre: es contexto, no un requisito.
  it('responde aunque el historial no se pueda leer', async () => {
    const deps = dependencies({
      loadHistory: vi.fn(async () => {
        throw new Error('ledger caído');
      }),
    });

    const response = await createChatHandler(deps)(
      request({ messages: [{ role: 'user', content: 'pregunta autosuficiente' }] })
    );

    expect(response.status).toBe(200);
    expect(deps.compare).toHaveBeenCalledWith(
      'pregunta autosuficiente',
      expect.stringMatching(/^chat-/),
      expect.anything(),
      []
    );
  });

  it('no deja que una lectura de historial bloqueada consuma el deadline de los proveedores', async () => {
    vi.useFakeTimers();
    let notifyHistoryStarted: (() => void) | undefined;
    const historyStarted = new Promise<void>((resolve) => {
      notifyHistoryStarted = resolve;
    });
    const deps = dependencies({
      loadHistory: vi.fn(() => {
        notifyHistoryStarted?.();
        return new Promise<ConversationTurn[]>(() => undefined);
      }),
    });

    try {
      const responsePromise = createChatHandler(deps)(
        request({ messages: [{ role: 'user', content: 'pregunta autosuficiente' }] })
      );
      // WebCrypto termina antes de iniciar la lectura. Esperar a la llamada hace
      // que el test avance exactamente el temporizador que quiere verificar.
      await historyStarted;
      await vi.advanceTimersByTimeAsync(1_000);
      const response = await responsePromise;

      expect(response).toBeInstanceOf(Response);
      expect(deps.compare).toHaveBeenCalledWith(
        'pregunta autosuficiente',
        expect.stringMatching(/^chat-/),
        expect.anything(),
        []
      );
    } finally {
      vi.useRealTimers();
    }
  });

  it('falla cerrado si el ledger no está disponible y no filtra el error', async () => {
    const deps = dependencies({
      recordRequest: vi.fn(async () => {
        throw new Error('postgresql://usuario:secreto@host/base');
      }),
    });
    const response = await createChatHandler(deps)(
      request({ messages: [{ role: 'user', content: 'pregunta' }] })
    );

    expect(response.status).toBe(503);
    expect(await response.text()).not.toContain('secreto');
    expect(deps.compare).not.toHaveBeenCalled();
  });

  it('aísla un fallo inesperado del comparador y registra el fallo técnico', async () => {
    const failRequest = vi.fn<ChatFunctionDependencies['failRequest']>(async () => undefined);
    const errorLog = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const deps = dependencies({
      compare: vi.fn(async () => {
        throw new Error('Authorization: Bearer secreto');
      }),
      failRequest,
    });

    const response = await createChatHandler(deps)(
      request({ messages: [{ role: 'user', content: 'pregunta' }] })
    );

    expect(response.status).toBe(503);
    expect(await response.text()).not.toContain('secreto');
    expect(deps.completeRequest).not.toHaveBeenCalled();
    expect(failRequest).toHaveBeenCalledWith(
      expect.objectContaining({ status: 'failed', failureCode: 'comparison_error' })
    );
    const failedEvent = errorLog.mock.calls
      .map(([entry]) => JSON.parse(String(entry)) as Record<string, unknown>)
      .find((entry) => entry.event === 'chat_request_failed');
    expect(failedEvent).toMatchObject({
      event: 'chat_request_failed',
      request_id: expect.stringMatching(/^chat-/),
      failure_code: 'comparison_error',
      stage: 'compare',
      status: 'failed',
    });
    expect(JSON.stringify(errorLog.mock.calls)).not.toContain('Authorization: Bearer secreto');
    const failRequestCall = failRequest.mock.calls[0];
    if (!failRequestCall) throw new Error('missing fail request call');
    expect(failedEvent?.request_id).toBe((failRequestCall[0] as { requestId: string }).requestId);
  });

  it('registra un fallo de persistencia de coste con request_id y failure_code', async () => {
    const errorLog = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const deps = dependencies({
      completeRequest: vi.fn(async () => {
        throw new Error('database unavailable');
      }),
    });

    const response = await createChatHandler(deps)(
      request({ messages: [{ role: 'user', content: 'pregunta autosuficiente' }] })
    );

    expect(response.status).toBe(503);
    expect(response.headers.get('x-chat-request-id')).toMatch(/^chat-/);
    const failedEvent = errorLog.mock.calls
      .map(([entry]) => JSON.parse(String(entry)) as Record<string, unknown>)
      .find((entry) => entry.event === 'chat_request_failed');
    expect(failedEvent).toMatchObject({
      event: 'chat_request_failed',
      request_id: expect.stringMatching(/^chat-/),
      failure_code: 'completion_error',
      stage: 'complete',
    });
  });

  // Sin esto la consulta se queda en `processing` para siempre: el `catch` de `compare`
  // sí cierra el estado, pero el de `complete` no lo hacía. El ledger solo admite
  // `unknown` para un fallo que no es del comparador.
  it('cierra la consulta cuando falla la persistencia de coste', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const failRequest = vi.fn<ChatFunctionDependencies['failRequest']>(async () => undefined);
    const deps = dependencies({
      completeRequest: vi.fn(async () => {
        throw new Error('database unavailable');
      }),
      failRequest,
    });

    const response = await createChatHandler(deps)(
      request({ messages: [{ role: 'user', content: 'pregunta autosuficiente' }] })
    );

    expect(response.status).toBe(503);
    expect(failRequest).toHaveBeenCalledWith(
      expect.objectContaining({ status: 'failed', failureCode: 'unknown' })
    );
  });

  it('registra la RPC y el código cuando falla la persistencia de coste', async () => {
    const errorLog = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const deps = dependencies({
      completeRequest: vi.fn(async () => {
        throw new ChatDiagnosticError('Supabase no disponible', {
          dependency: 'supabase',
          operation: 'complete_chat_request',
          kind: 'rpc_not_found',
          code: 'PGRST202',
        });
      }),
    });

    const response = await createChatHandler(deps)(
      request({ messages: [{ role: 'user', content: 'pregunta autosuficiente' }] })
    );

    expect(response.status).toBe(503);
    const failedEvent = errorLog.mock.calls
      .map(([entry]) => JSON.parse(String(entry)) as Record<string, unknown>)
      .find((entry) => entry.event === 'chat_request_failed');
    expect(failedEvent).toMatchObject({
      failure_code: 'completion_error',
      stage: 'complete',
      error_context: {
        dependency: 'supabase',
        operation: 'complete_chat_request',
        kind: 'rpc_not_found',
        code: 'PGRST202',
      },
    });
  });

  it('devuelve el protocolo comparativo bufferizado y registra el coste', async () => {
    const deps = dependencies();
    const response = await createChatHandler(deps)(
      request({ messages: [{ role: 'user', content: 'pregunta autosuficiente' }] })
    );

    expect(response.status).toBe(200);
    expect(response.headers.get('content-type')).toContain('text/event-stream');
    expect(response.headers.get('x-chat-protocol')).toBe('2');
    const body = await response.text();
    expect(body.indexOf('"strategy":"current_structured"')).toBeLessThan(
      body.indexOf('"strategy":"gemini_file_search"')
    );
    expect(body).toContain('event: done');
    expect(body).toContain('data: {"request_id":"chat-test"}');
    expect(body).toContain('"claims":[{"text":"Respuesta A","source_indexes":[]}]');
    expect(deps.completeRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        actualMicrousd: 3,
        actualComplete: true,
        authorityIntent: null,
        timingsMs: {
          record: expect.any(Number),
          compare: expect.any(Number),
          beforePersistence: expect.any(Number),
        },
      })
    );
  });

  it('propaga la autoridad judicial solicitada sin registrar la pregunta en telemetría', async () => {
    const deps = dependencies();

    await createChatHandler(deps)(
      request({
        messages: [
          {
            role: 'user',
            content: '¿Qué pruebas acepta el Tribunal Supremo para desvirtuar los 183 días?',
          },
        ],
      })
    );

    expect(deps.completeRequest).toHaveBeenCalledWith(
      expect.objectContaining({ authorityIntent: 'tribunal_supremo' })
    );
  });

  it('entrega al ledger la pregunta y los identificadores pseudónimos', async () => {
    const deps = dependencies();

    const response = await createChatHandler(deps)(
      request({
        conversation_id: 'conversation-1',
        country_path: '/espana',
        messages: [
          {
            id: 'message-1',
            role: 'user',
            content: '¿Qué pruebas tiene en cuenta Hacienda?',
          },
        ],
      })
    );

    expect(response.status).toBe(200);
    expect(deps.recordRequest).toHaveBeenCalledWith({
      requestId: expect.stringMatching(/^chat-/),
      conversationId: 'conversation-1',
      userMessageId: 'message-1',
      countryPath: '/espana',
      question: '¿Qué pruebas tiene en cuenta Hacienda?',
      conversationAccessHash: expect.stringMatching(/^[0-9a-f]{64}$/),
    });
  });

  it('su respuesta completa atraviesa el parser real del frontend', async () => {
    const response = await createChatHandler(dependencies())(
      request({ messages: [{ role: 'user', content: 'pregunta autosuficiente' }] })
    );
    const chunks = [];
    if (!response.body) throw new Error('respuesta sin body');

    for await (const chunk of parseChatEventStream(response.body)) chunks.push(chunk);

    expect(chunks.map((chunk) => chunk.type)).toEqual([
      'answer_start',
      'token',
      'strategy_sources',
      'answer_done',
      'answer_start',
      'token',
      'strategy_sources',
      'answer_done',
      'done',
    ]);
  });

  it('serializa el código seguro del fallo aislado de una estrategia', () => {
    const serialized = serializeComparison({
      ...report,
      answers: [
        report.answers[0],
        {
          ...report.answers[1],
          status: 'error',
          text: '',
          diagnostics: {
            authority_intent: null,
            authority_match: 'not_requested',
            retrieval_filter: null,
            retrieved_judgment_ids: [],
            citation_candidates: 1,
            citation_verified: 0,
            failure_code: 'citation_verification',
            error_name: null,
          },
        },
      ],
    });

    expect(serialized).toContain('"failure_code":"citation_verification"');
  });

  it('rechaza entradas inválidas antes de registrar la consulta', async () => {
    const deps = dependencies();
    const response = await createChatHandler(deps)(request({ messages: [] }));

    expect(response.status).toBe(400);
    expect(deps.recordRequest).not.toHaveBeenCalled();
  });

  it('rechaza preguntas de más de 500 caracteres antes de registrar la consulta', async () => {
    const deps = dependencies();
    const response = await createChatHandler(deps)(
      request({ messages: [{ role: 'user', content: 'a'.repeat(501) }] })
    );

    expect(response.status).toBe(400);
    expect(deps.recordRequest).not.toHaveBeenCalled();
  });
});
