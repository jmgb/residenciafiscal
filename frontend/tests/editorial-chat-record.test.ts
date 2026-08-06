import { afterEach, describe, expect, it, vi } from 'vitest';
import { recordEditorialTurn } from '@/lib/editorial-chat-record';

afterEach(() => {
  vi.restoreAllMocks();
});

describe('registro del turno editorial', () => {
  // Solo viaja el identificador: el texto lo pone el servidor desde su catálogo.
  it('manda el identificador de la respuesta y no su contenido', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(new Response(null, { status: 204 }));

    await recordEditorialTurn({
      conversationId: 'conversation-1',
      conversationAccessToken: 'a'.repeat(64),
      userMessageId: 'm1',
      countryPath: '/espana',
      answerId: 'sporadic-absences',
    });

    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe('/api/chat-editorial');
    expect(JSON.parse(String(init?.body))).toEqual({
      conversation_id: 'conversation-1',
      conversation_access_token: 'a'.repeat(64),
      user_message_id: 'm1',
      country_path: '/espana',
      answer_id: 'sporadic-absences',
    });
  });

  // La respuesta ya está en pantalla: un fallo de registro no puede romperla.
  it('no propaga el fallo de red', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('sin red'));

    await expect(
      recordEditorialTurn({
        conversationId: 'conversation-1',
        conversationAccessToken: 'a'.repeat(64),
        userMessageId: 'm1',
        countryPath: '/espana',
        answerId: 'sporadic-absences',
      })
    ).resolves.toBeUndefined();
  });

  it('abandona un registro bloqueado para no congelar el composer', async () => {
    vi.useFakeTimers();
    vi.spyOn(globalThis, 'fetch').mockImplementation(
      (_url, init) =>
        new Promise((_resolve, reject) => {
          init?.signal?.addEventListener('abort', () => reject(init.signal?.reason), {
            once: true,
          });
        })
    );

    const recording = recordEditorialTurn({
      conversationId: 'conversation-1',
      conversationAccessToken: 'a'.repeat(64),
      userMessageId: 'm1',
      countryPath: '/espana',
      answerId: 'sporadic-absences',
    });
    await vi.advanceTimersByTimeAsync(3_000);

    await expect(recording).resolves.toBeUndefined();
    vi.useRealTimers();
  });

  it('propaga la cancelación del usuario a un registro que sigue pendiente', async () => {
    const caller = new AbortController();
    let fetchSignal: AbortSignal | undefined;
    vi.spyOn(globalThis, 'fetch').mockImplementation(
      (_url, init) =>
        new Promise((_resolve, reject) => {
          fetchSignal = init?.signal ?? undefined;
          init?.signal?.addEventListener('abort', () => reject(init.signal?.reason), {
            once: true,
          });
        })
    );

    const recording = recordEditorialTurn(
      {
        conversationId: 'conversation-1',
        conversationAccessToken: 'a'.repeat(64),
        userMessageId: 'm1',
        countryPath: '/espana',
        answerId: 'sporadic-absences',
      },
      caller.signal
    );
    caller.abort();

    await expect(recording).resolves.toBeUndefined();
    expect(fetchSignal?.aborted).toBe(true);
  });
});
