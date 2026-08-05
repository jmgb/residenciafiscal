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
      userMessageId: 'm1',
      countryPath: '/espana',
      answerId: 'sporadic-absences',
    });

    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe('/api/chat-editorial');
    expect(JSON.parse(String(init?.body))).toEqual({
      conversation_id: 'conversation-1',
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
        userMessageId: 'm1',
        countryPath: '/espana',
        answerId: 'sporadic-absences',
      })
    ).resolves.toBeUndefined();
  });
});
