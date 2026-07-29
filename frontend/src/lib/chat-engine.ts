/**
 * Punto único de selección del motor de chat.
 *
 * Hoy solo existe el stub. Cuando llegue el backend RAG, aquí se decidirá
 * entre implementaciones y `chatEngineMode` pasará a `'live'`, lo que apaga
 * automáticamente el aviso de contenido simulado en la UI.
 */

import { SPAIN_ROUTE } from '@/data/countryRoutes';
import { createStubChatEngine } from '@/lib/chat-engine.stub';
import { corpusLoadFailed, loadCorpus } from '@/lib/corpus';
import type { ChatChunk, ChatEngine, ChatMessage, ChatRequestContext } from '@/types/chat';

export type ChatEngineMode = 'stub' | 'live';

export const chatEngineMode: ChatEngineMode = 'stub';

const DEFAULT_CONTEXT: ChatRequestContext = {
  countryPath: SPAIN_ROUTE.path,
  countryName: SPAIN_ROUTE.name,
};

const UNSUPPORTED_COUNTRY_MESSAGE = (countryName: string) =>
  `> **Todavía no hay un corpus de jurisprudencia disponible para ${countryName}.** ` +
  'La consulta se activará cuando incorporemos la documentación nacional correspondiente.\n\n';

export const chatEngine: ChatEngine = {
  async *askQuestion(
    messages: ChatMessage[],
    signal: AbortSignal,
    context = DEFAULT_CONTEXT
  ): AsyncIterable<ChatChunk> {
    if (context.countryPath !== SPAIN_ROUTE.path) {
      if (signal.aborted) return;
      yield { type: 'token', text: UNSUPPORTED_COUNTRY_MESSAGE(context.countryName) };
      yield { type: 'done' };
      return;
    }

    const corpus = await loadCorpus();
    if (corpusLoadFailed() && !signal.aborted) {
      yield {
        type: 'token',
        text:
          '> **Aviso:** No se han podido cargar las sentencias. ' +
          'La respuesta simulada se muestra sin fuentes verificables.\n\n',
      };
    }
    yield* createStubChatEngine(corpus).askQuestion(messages, signal);
  },
};
