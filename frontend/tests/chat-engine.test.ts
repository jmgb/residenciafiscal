import { afterEach, describe, expect, it, vi } from 'vitest';
import { chatEngine } from '@/lib/chat-engine';
import { resetCorpusCache } from '@/lib/corpus';
import type { ChatChunk, ChatMessage } from '@/types/chat';

const messages: ChatMessage[] = [
  {
    id: 'm1',
    role: 'user',
    content: '¿Qué ocurre con los 183 días?',
    createdAt: '2026-07-29T10:00:00.000Z',
  },
];

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  resetCorpusCache();
});

describe('chatEngine', () => {
  it('avisa dentro de la respuesta cuando no puede cargar las sentencias', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new TypeError('Failed to fetch');
      })
    );

    const chunks: ChatChunk[] = [];
    for await (const chunk of chatEngine.askQuestion(messages, new AbortController().signal)) {
      chunks.push(chunk);
      if (chunk.type === 'token' && chunk.text.includes('No se han podido cargar')) break;
    }

    const text = chunks
      .filter((chunk): chunk is Extract<ChatChunk, { type: 'token' }> => chunk.type === 'token')
      .map((chunk) => chunk.text)
      .join('');
    expect(text).toContain('No se han podido cargar las sentencias');
  });
});
