/**
 * Punto único de selección del motor de chat.
 *
 * Hoy solo existe el stub. Cuando llegue el backend RAG, aquí se decidirá
 * entre implementaciones y `chatEngineMode` pasará a `'live'`, lo que apaga
 * automáticamente el aviso de contenido simulado en la UI.
 */
import { createStubChatEngine } from '@/lib/chat-engine.stub';
import { loadCorpus } from '@/lib/corpus';
import type { ChatChunk, ChatEngine, ChatMessage } from '@/types/chat';

export type ChatEngineMode = 'stub' | 'live';

export const chatEngineMode: ChatEngineMode = 'stub';

export const chatEngine: ChatEngine = {
  async *askQuestion(messages: ChatMessage[], signal: AbortSignal): AsyncIterable<ChatChunk> {
    const corpus = await loadCorpus();
    yield* createStubChatEngine(corpus).askQuestion(messages, signal);
  },
};
