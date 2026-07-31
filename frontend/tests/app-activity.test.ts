/**
 * Qué cuenta como «trabajo en curso» antes de recargar por versión nueva.
 *
 * Una recarga automática no puede llevarse por delante una respuesta que está
 * llegando ni una pregunta a medio escribir. Estas dos situaciones son las que
 * convierten la recarga silenciosa en un aviso.
 */
import { beforeEach, describe, expect, it } from 'vitest';
import { hasWorkInProgress } from '@/lib/app-activity';
import { useConversations } from '@/stores/useConversations';
import type { ChatMessage, ChatStrategyAnswer, Conversation } from '@/types/chat';

function conversationWith(messages: ChatMessage[]): Conversation {
  return {
    id: 'c1',
    title: 'Consulta',
    createdAt: '2026-07-31T10:00:00.000Z',
    updatedAt: '2026-07-31T10:00:00.000Z',
    messages,
  };
}

const assistantMessage = (overrides: Partial<ChatMessage> = {}): ChatMessage => ({
  id: 'm1',
  role: 'assistant',
  content: 'Respuesta',
  createdAt: '2026-07-31T10:00:00.000Z',
  ...overrides,
});

const answer = (overrides: Partial<ChatStrategyAnswer>): ChatStrategyAnswer =>
  ({
    strategy: 'current_structured',
    content: 'Respuesta',
    ...overrides,
  }) as ChatStrategyAnswer;

beforeEach(() => {
  useConversations.setState({ conversations: [] });
  document.body.replaceChildren();
});

describe('hasWorkInProgress', () => {
  it('no ve nada en curso en una pestaña en reposo', () => {
    useConversations.setState({ conversations: [conversationWith([assistantMessage()])] });

    expect(hasWorkInProgress()).toBe(false);
  });

  it('ve la respuesta que todavía está llegando', () => {
    useConversations.setState({
      conversations: [conversationWith([assistantMessage({ isStreaming: true })])],
    });

    expect(hasWorkInProgress()).toBe(true);
  });

  it('ve una de las dos respuestas comparadas todavía en curso', () => {
    useConversations.setState({
      conversations: [
        conversationWith([
          assistantMessage({
            answers: [
              answer({ strategy: 'current_structured', isStreaming: false }),
              answer({ strategy: 'gemini_file_search', isStreaming: true }),
            ],
          }),
        ]),
      ],
    });

    expect(hasWorkInProgress()).toBe(true);
  });

  it('ve al usuario escribiendo en el composer', () => {
    const textarea = document.createElement('textarea');
    document.body.append(textarea);
    textarea.focus();

    expect(hasWorkInProgress()).toBe(true);
  });

  it('no confunde un botón enfocado con estar escribiendo', () => {
    const button = document.createElement('button');
    document.body.append(button);
    button.focus();

    expect(hasWorkInProgress()).toBe(false);
  });
});
