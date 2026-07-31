import { afterEach, describe, expect, it, vi } from 'vitest';
import chatProxy, { config } from '../netlify/edge-functions/chat';

function request(body = '{"messages":[]}'): Request {
  return new Request('https://residenciafiscal.org/api/chat', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body,
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function stubEnvironment(values: Record<string, string | undefined>) {
  vi.stubGlobal('Netlify', {
    env: { get: (name: string) => values[name] },
  });
}

describe('Netlify /api/chat proxy', () => {
  it('declara ruta y rate limit por IP', () => {
    expect(config).toMatchObject({
      path: '/api/chat',
      rateLimit: { aggregateBy: ['ip', 'domain'], windowSize: 60, windowLimit: 5 },
    });
  });

  it('no envía el secreto a un backend sin HTTPS', async () => {
    stubEnvironment({
      CHAT_BACKEND_URL: 'http://api.residenciafiscal.org',
      CHAT_PROXY_SECRET: 'secreto-largo-de-prueba',
    });
    const fetchSpy = vi.fn();
    vi.stubGlobal('fetch', fetchSpy);

    const response = await chatProxy(request());

    expect(response.status).toBe(503);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('rechaza el cuerpo excesivo antes de contactar con el backend', async () => {
    stubEnvironment({
      CHAT_BACKEND_URL: 'https://api.residenciafiscal.org',
      CHAT_PROXY_SECRET: 'secreto-largo-de-prueba',
    });
    const fetchSpy = vi.fn();
    vi.stubGlobal('fetch', fetchSpy);

    const response = await chatProxy(request('x'.repeat(200_001)));

    expect(response.status).toBe(413);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('permanece cerrado si faltan backend o secreto', async () => {
    stubEnvironment({});
    const fetchSpy = vi.fn();
    vi.stubGlobal('fetch', fetchSpy);

    const response = await chatProxy(request());

    expect(response.status).toBe(503);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('rechaza métodos distintos de POST', async () => {
    stubEnvironment({});
    const response = await chatProxy(
      new Request('https://residenciafiscal.org/api/chat', { method: 'GET' })
    );

    expect(response.status).toBe(405);
    expect(response.headers.get('allow')).toBe('POST');
  });

  it('reenvía el cuerpo al backend autenticado y conserva el stream SSE', async () => {
    stubEnvironment({
      CHAT_BACKEND_URL: 'https://api.residenciafiscal.org',
      CHAT_PROXY_SECRET: 'secreto-largo-de-prueba',
    });
    const encoder = new TextEncoder();
    const upstreamBody = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(encoder.encode('event: done\ndata: {}\n\n'));
        controller.close();
      },
    });
    const fetchSpy = vi.fn(
      async () =>
        new Response(upstreamBody, {
          status: 200,
          headers: {
            'content-type': 'text/event-stream; charset=utf-8',
            'x-chat-protocol': '2',
          },
        })
    );
    vi.stubGlobal('fetch', fetchSpy);
    const body = '{"messages":[{"role":"user","content":"pregunta"}]}';

    const response = await chatProxy(request(body));

    expect(response.status).toBe(200);
    expect(response.headers.get('content-type')).toContain('text/event-stream');
    expect(response.headers.get('x-chat-protocol')).toBe('2');
    expect(response.headers.get('cache-control')).toBe('no-store');
    expect(await response.text()).toBe('event: done\ndata: {}\n\n');
    expect(fetchSpy).toHaveBeenCalledOnce();
    const [url, init] = fetchSpy.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe('https://api.residenciafiscal.org/chat');
    expect(init).toMatchObject({
      method: 'POST',
      redirect: 'error',
      headers: {
        accept: 'text/event-stream',
        'content-type': 'application/json',
        'x-chat-proxy-secret': 'secreto-largo-de-prueba',
      },
      body,
    });
  });
});
