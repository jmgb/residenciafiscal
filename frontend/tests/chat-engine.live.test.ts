import { afterEach, describe, expect, it, vi } from 'vitest';
import { createLiveChatEngine } from '@/lib/chat-engine.live';
import { ChatEngineError } from '@/lib/chat-sse-protocol';
import type { ChatChunk, ChatMessage } from '@/types/chat';
import { makeChatSourceV2 } from './chat-source-fixture';

const messages: ChatMessage[] = [
  {
    id: 'm1',
    role: 'user',
    content: '¿Qué ocurre con los 183 días?',
    createdAt: '2026-07-31T10:00:00.000Z',
  },
];

function sseEvent(name: string, data: unknown): string {
  return `event: ${name}\ndata: ${JSON.stringify(data)}\n\n`;
}

function sseResponse(
  parts: string[],
  options: { status?: number; headers?: Record<string, string> } = {}
): Response {
  const encoder = new TextEncoder();
  const body = new ReadableStream({
    start(controller) {
      for (const part of parts) controller.enqueue(encoder.encode(part));
      controller.close();
    },
  });
  return new Response(body, {
    status: options.status ?? 200,
    headers: {
      'content-type': 'text/event-stream; charset=utf-8',
      'x-chat-protocol': '2',
      ...options.headers,
    },
  });
}

const requestContext = {
  countryPath: '/espana',
  countryName: 'España',
  conversationId: 'conversation-1',
  conversationAccessToken: 'a'.repeat(64),
};

async function collect(engine = createLiveChatEngine()): Promise<ChatChunk[]> {
  const chunks: ChatChunk[] = [];
  for await (const chunk of engine.askQuestion(
    messages,
    new AbortController().signal,
    requestContext
  )) {
    chunks.push(chunk);
  }
  return chunks;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('createLiveChatEngine', () => {
  it('convierte una respuesta SSE v2 en chunks del chat', async () => {
    const source = makeChatSourceV2();
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        sseResponse([
          sseEvent('token', { text: 'Respuesta.' }),
          sseEvent('sources', { sources: [source] }),
          sseEvent('done', {}),
        ])
      )
    );

    await expect(collect()).resolves.toEqual([
      { type: 'token', text: 'Respuesta.' },
      { type: 'sources', sources: [source] },
      { type: 'done' },
    ]);
  });

  it('envía la última pregunta con identificadores pseudónimos y jurisdicción', async () => {
    const fetchSpy = vi.fn(async () => sseResponse([sseEvent('done', {})]));
    vi.stubGlobal('fetch', fetchSpy);

    await collect();

    expect(fetchSpy).toHaveBeenCalledOnce();
    const [url, init] = fetchSpy.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe('/api/chat');
    expect(init.method).toBe('POST');
    expect(init.headers).toEqual({ 'content-type': 'application/json' });
    expect(JSON.parse(init.body as string)).toEqual({
      conversation_id: 'conversation-1',
      conversation_access_token: 'a'.repeat(64),
      country_path: '/espana',
      messages: [{ id: 'm1', role: 'user', content: '¿Qué ocurre con los 183 días?' }],
    });
    expect(init.signal).toBeInstanceOf(AbortSignal);
  });

  it('envía solo la última pregunta y no el contenido vacío de respuestas A/B', async () => {
    const fetchSpy = vi.fn(async () => sseResponse([sseEvent('done', {})]));
    vi.stubGlobal('fetch', fetchSpy);
    const history: ChatMessage[] = [
      messages[0],
      {
        id: 'a1',
        role: 'assistant',
        content: '',
        createdAt: '2026-07-31T10:00:01.000Z',
        answers: [],
      },
      {
        id: 'm2',
        role: 'user',
        content: '¿Y qué ocurre con el centro de intereses?',
        createdAt: '2026-07-31T10:00:02.000Z',
      },
    ];
    const engine = createLiveChatEngine();

    for await (const _chunk of engine.askQuestion(
      history,
      new AbortController().signal,
      requestContext
    )) {
      // Consumir.
    }

    const [, init] = fetchSpy.mock.calls[0] as unknown as [string, RequestInit];
    expect(JSON.parse(init.body as string)).toEqual({
      conversation_id: 'conversation-1',
      conversation_access_token: 'a'.repeat(64),
      country_path: '/espana',
      messages: [{ id: 'm2', role: 'user', content: '¿Y qué ocurre con el centro de intereses?' }],
    });
  });

  it.each([
    [429, 'rate_limited', true],
    [503, 'unavailable', true],
    [400, 'invalid_request', false],
    [413, 'invalid_request', false],
    [500, 'http_error', true],
  ])('convierte HTTP %i en un error tipado', async (status, code, retryable) => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        sseResponse(['esto no debe parsearse'], {
          status,
          headers: { 'content-type': 'text/html', 'x-chat-protocol': 'ausente' },
        })
      )
    );

    await expect(collect()).rejects.toMatchObject({ code, retryable });
  });

  it('rechaza un 200 que no sea SSE', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response('{"ok":true}', {
            status: 200,
            headers: { 'content-type': 'application/json', 'x-chat-protocol': '2' },
          })
      )
    );

    await expect(collect()).rejects.toMatchObject({ code: 'bad_content_type' });
  });

  it('rechaza una versión de protocolo distinta de 2', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        sseResponse([sseEvent('done', {})], {
          headers: { 'x-chat-protocol': '99' },
        })
      )
    );

    await expect(collect()).rejects.toMatchObject({ code: 'protocol_mismatch' });
  });

  it('rechaza una respuesta SSE sin cuerpo', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(null, {
            status: 200,
            headers: {
              'content-type': 'text/event-stream; charset=utf-8',
              'x-chat-protocol': '2',
            },
          })
      )
    );

    await expect(collect()).rejects.toMatchObject({ code: 'empty_body' });
  });

  it('convierte un fallo de red en un error reintentable', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new TypeError('Failed to fetch');
      })
    );

    await expect(collect()).rejects.toMatchObject({
      code: 'network_error',
      retryable: true,
    });
  });

  it('no oculta la cancelación solicitada por el usuario', async () => {
    const controller = new AbortController();
    controller.abort();
    const abortError = new DOMException('Aborted', 'AbortError');
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw abortError;
      })
    );
    const engine = createLiveChatEngine();

    const consume = async () => {
      for await (const _chunk of engine.askQuestion(messages, controller.signal)) {
        // Consumir.
      }
    };

    await expect(consume()).rejects.toBe(abortError);
    expect(abortError).not.toBeInstanceOf(ChatEngineError);
  });
});
