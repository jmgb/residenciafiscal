import type { Context } from '@netlify/edge-functions';
import { afterEach, describe, expect, it, vi } from 'vitest';
import chatProxy, { config } from '../netlify/prototypes/chat-fastapi-edge-v2';

const body = JSON.stringify({
  conversation_id: 'conversation-1',
  country_path: '/espana',
  messages: [{ id: 'message-1', role: 'user', content: 'pregunta' }],
});

const request = (value = body) =>
  new Request('https://residenciafiscal.org/api/chat', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: value,
  });

const contextWith = (next: () => Promise<Response>) => ({ next }) as unknown as Context;

const legacyContext = () =>
  contextWith(async () => new Response('event: done\ndata: {}\n\n', { status: 200 }));

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function stubEnvironment(values: Record<string, string | undefined>) {
  vi.stubGlobal('Netlify', { env: { get: (name: string) => values[name] } });
}

describe('fachada firmada Edge → FastAPI', () => {
  it('firma timestamp, request-id y hash del body sin enviar el secreto estático', async () => {
    stubEnvironment({
      CHAT_BACKEND_URL: 'https://backend.example.invalid',
      CHAT_HMAC_SECRET: 'secret-for-test',
      CHAT_BACKEND_PERCENT: '100',
    });
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response('event: done\ndata: {"request_id":"chat-1"}\n\n', {
            headers: { 'content-type': 'text/event-stream', 'x-chat-protocol': '2' },
          })
      )
    );

    const response = await chatProxy(request(), legacyContext());
    expect(response.status).toBe(200);
    const [, init] = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0] as [
      string,
      RequestInit,
    ];
    const headers = new Headers(init.headers);
    expect(headers.get('x-chat-timestamp')).toMatch(/^\d+$/);
    expect(headers.get('x-chat-request-id')).toMatch(/^chat-[0-9a-f-]{36}$/);
    expect(headers.get('x-chat-body-sha256')).toMatch(/^[0-9a-f]{64}$/);
    expect(headers.get('x-chat-signature')).toMatch(/^v1=[0-9a-f]{64}$/);
    expect(headers.get('x-chat-proxy-secret')).toBeNull();
  });

  it('devuelve el tráfico al runtime anterior con CHAT_BACKEND_PERCENT=0', async () => {
    stubEnvironment({
      CHAT_BACKEND_URL: 'https://backend.example.invalid',
      CHAT_HMAC_SECRET: 'secret-for-test',
      CHAT_BACKEND_PERCENT: '0',
    });
    const upstream = vi.fn();
    vi.stubGlobal('fetch', upstream);
    const next = vi.fn(async () => new Response('legacy', { status: 200 }));

    const response = await chatProxy(request(), contextWith(next));

    expect(await response.text()).toBe('legacy');
    expect(next).toHaveBeenCalledTimes(1);
    expect(upstream).not.toHaveBeenCalled();
  });

  it('mantiene una misma conversación en el mismo runtime', async () => {
    stubEnvironment({
      CHAT_BACKEND_URL: 'https://backend.example.invalid',
      CHAT_HMAC_SECRET: 'secret-for-test',
      CHAT_BACKEND_PERCENT: '50',
    });
    const upstream = vi.fn(async () => new Response('', { status: 200 }));
    vi.stubGlobal('fetch', upstream);
    const next = vi.fn(async () => new Response('legacy', { status: 200 }));

    const first = await chatProxy(request(), contextWith(next));
    const second = await chatProxy(request(), contextWith(next));

    expect(await first.text()).toBe(await second.text());
  });

  it('delega el descarte de abuso en la cuota de plataforma, no en Blobs', () => {
    expect(config.path).toBe('/api/chat');
    expect(config.rateLimit).toEqual({
      aggregateBy: ['ip', 'domain'],
      windowSize: 60,
      windowLimit: 5,
    });
  });
});
