import { afterEach, describe, expect, it, vi } from 'vitest';
import { chatEngine, resolveChatEngineMode } from '@/lib/chat-engine';
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
  it('solo activa el motor real mediante una opción explícita', () => {
    expect(resolveChatEngineMode('live')).toBe('live');
    expect(resolveChatEngineMode(undefined)).toBe('stub');
    expect(resolveChatEngineMode('true')).toBe('stub');
    expect(resolveChatEngineMode('LIVE')).toBe('stub');
  });

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

  it('no consulta el corpus español cuando recibe otro país', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => [],
      }))
    );

    const chunks: ChatChunk[] = [];
    for await (const chunk of chatEngine.askQuestion(messages, new AbortController().signal, {
      countryPath: '/mexico',
      countryName: 'México',
    })) {
      chunks.push(chunk);
    }

    const text = chunks
      .filter((chunk): chunk is Extract<ChatChunk, { type: 'token' }> => chunk.type === 'token')
      .map((chunk) => chunk.text)
      .join('');
    expect(text).toContain('México');
    expect(text).toContain('corpus');
    expect(chunks.some((chunk) => chunk.type === 'sources')).toBe(false);
  });
});
