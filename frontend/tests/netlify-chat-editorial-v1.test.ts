import { describe, expect, it, vi } from 'vitest';
import { editorialTurn } from '../netlify/functions/chat/editorial-answers';
import {
  type ChatEditorialDependencies,
  config,
  createChatEditorialHandler,
} from '../netlify/functions/chat-editorial';
import catalogue from '../src/data/editorialChatAnswers.json';

const request = (body: unknown) =>
  new Request('https://residenciafiscal.org/api/chat-editorial', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });

const dependencies = (
  overrides: Partial<ChatEditorialDependencies> = {}
): ChatEditorialDependencies => ({
  enabled: true,
  recordEditorial: vi.fn(async () => undefined),
  ...overrides,
});

const body = {
  conversation_id: 'conversation-1',
  conversation_access_token: 'a'.repeat(64),
  user_message_id: 'm1',
  country_path: '/espana',
  answer_id: 'sporadic-absences',
};

describe('Netlify Function /api/chat-editorial', () => {
  it('declara POST, ruta y rate limit', () => {
    expect(config).toMatchObject({ path: '/api/chat-editorial', method: 'POST' });
    expect(config.rateLimit.windowLimit).toBeGreaterThan(0);
  });

  // El servidor materializa el texto desde su propia copia del catálogo: el
  // navegador solo dice QUÉ respuesta se mostró, nunca qué decía.
  it('registra el turno con el texto canónico del catálogo, no con el del cliente', async () => {
    const deps = dependencies();

    const response = await createChatEditorialHandler(deps)(
      request({ ...body, content: 'texto inventado por el cliente' })
    );

    expect(response.status).toBe(204);
    const recorded = vi.mocked(deps.recordEditorial).mock.calls[0]?.[0];
    if (!recorded) throw new Error('no se registró el turno');
    expect(recorded.conversationId).toBe('conversation-1');
    expect(recorded.conversationAccessHash).toMatch(/^[0-9a-f]{64}$/);
    expect(recorded.conversationAccessHash).not.toBe(body.conversation_access_token);
    expect(recorded.question).toContain('ausencias esporádicas');
    expect(recorded.content).toContain('esporádicas');
    expect(recorded.content).not.toContain('inventado');
    expect(recorded.model).toContain('editorial-');
    expect(recorded.sources[0]).toMatchObject({ strategy: 'editorial', verification: 'EXACT' });
  });

  // `create_chat_request` rechaza una pregunta de más de 500 caracteres. Sin este
  // gate, una entrada editorial más larga fallaría solo en producción.
  it('mantiene todas las preguntas del catálogo dentro del límite del ledger', () => {
    for (const entry of catalogue) {
      expect(entry.question.trim().length).toBeGreaterThanOrEqual(1);
      expect(entry.question.trim().length).toBeLessThanOrEqual(500);
      expect(editorialTurn(entry.id)).not.toBeNull();
    }
  });

  it('rechaza un identificador editorial que no está en el catálogo', async () => {
    const deps = dependencies();

    const response = await createChatEditorialHandler(deps)(
      request({ ...body, answer_id: 'no-existe' })
    );

    expect(response.status).toBe(400);
    expect(deps.recordEditorial).not.toHaveBeenCalled();
  });

  it('rechaza identificadores con forma inválida', async () => {
    const deps = dependencies();

    const response = await createChatEditorialHandler(deps)(
      request({ ...body, conversation_id: 'no válido' })
    );

    expect(response.status).toBe(400);
    expect(deps.recordEditorial).not.toHaveBeenCalled();
  });

  it('rechaza registrar el turno sin el secreto de posesión de la conversación', async () => {
    const deps = dependencies();
    const { conversation_access_token: _omitted, ...withoutAccessToken } = body;

    const response = await createChatEditorialHandler(deps)(request(withoutAccessToken));

    expect(response.status).toBe(400);
    expect(deps.recordEditorial).not.toHaveBeenCalled();
  });

  it('no responde error al usuario cuando el ledger falla', async () => {
    const deps = dependencies({
      recordEditorial: vi.fn(async () => {
        throw new Error('postgresql://usuario:secreto@host/base');
      }),
    });

    const response = await createChatEditorialHandler(deps)(request(body));

    expect(response.status).toBe(503);
    expect(await response.text()).not.toContain('secreto');
  });

  it('falla cerrado si el chat no está configurado', async () => {
    const deps = dependencies({ enabled: false });

    const response = await createChatEditorialHandler(deps)(request(body));

    expect(response.status).toBe(503);
    expect(deps.recordEditorial).not.toHaveBeenCalled();
  });
});
