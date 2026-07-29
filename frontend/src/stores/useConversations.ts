/**
 * Historial de conversaciones, persistido en localStorage.
 *
 * No hay cuentas ni backend: el historial es local al navegador. La clave está
 * VERSIONADA para poder cambiar la forma de los datos sin dejar al usuario con
 * un store corrupto.
 */
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import type { ChatMessage, ChatSource, Conversation } from '@/types/chat';

export const CONVERSATIONS_STORAGE_KEY = 'rf.conversations.v1';

const TITLE_MAX_LENGTH = 60;
const DEFAULT_TITLE = 'Consulta sin título';

export function deriveTitle(content: string): string {
  const flat = content.replace(/\s+/g, ' ').trim();
  if (!flat) return DEFAULT_TITLE;
  if (flat.length <= TITLE_MAX_LENGTH) return flat;
  return `${flat.slice(0, TITLE_MAX_LENGTH)}…`;
}

function newId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return crypto.randomUUID();
  return `id-${Math.random().toString(36).slice(2)}-${Date.now()}`;
}

function byUpdatedDesc(a: Conversation, b: Conversation): number {
  return b.updatedAt.localeCompare(a.updatedAt);
}

const VALID_RESULTS = new Set([
  'GANA_AEAT',
  'GANA_CONTRIBUYENTE',
  'PARCIAL',
  'RETROACCION',
  'INADMISION',
  'DESCONOCIDO',
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isStoredSource(value: unknown): value is ChatSource {
  if (!isRecord(value)) return false;
  return (
    typeof value.archivo === 'string' &&
    typeof value.roj === 'string' &&
    typeof value.ecli === 'string' &&
    typeof value.organo === 'string' &&
    typeof value.fecha === 'string' &&
    typeof value.resultado === 'string' &&
    VALID_RESULTS.has(value.resultado) &&
    Array.isArray(value.criterioDecisivo) &&
    value.criterioDecisivo.every((criterio) => typeof criterio === 'string') &&
    typeof value.esCasoResidencia === 'boolean' &&
    typeof value.extracto === 'string'
  );
}

function isStoredMessage(value: unknown): value is ChatMessage {
  if (!isRecord(value)) return false;
  return (
    typeof value.id === 'string' &&
    (value.role === 'user' || value.role === 'assistant') &&
    typeof value.content === 'string' &&
    typeof value.createdAt === 'string' &&
    (value.isStreaming === undefined || typeof value.isStreaming === 'boolean') &&
    (value.sources === undefined ||
      (Array.isArray(value.sources) && value.sources.every(isStoredSource)))
  );
}

function isStoredConversation(value: unknown): value is Conversation {
  if (!isRecord(value)) return false;
  if (
    typeof value.id !== 'string' ||
    typeof value.title !== 'string' ||
    typeof value.createdAt !== 'string' ||
    typeof value.updatedAt !== 'string' ||
    !Array.isArray(value.messages)
  ) {
    return false;
  }
  return value.messages.every(isStoredMessage);
}

/**
 * Apaga el flag de streaming de todos los mensajes.
 *
 * Un mensaje solo está en streaming mientras vive el generador que lo alimenta, y ese
 * generador no sobrevive a una recarga. Rehidratar `isStreaming: true` deja un cursor
 * parpadeando para siempre y sin forma de recuperarse; el texto que alcanzó a llegar se
 * conserva tal cual. Devuelve el mismo array si no había nada que sanear, para no
 * invalidar referencias sin motivo.
 */
export function clearStreamingFlags(conversations: unknown): Conversation[] {
  if (!Array.isArray(conversations)) return [];

  const valid = conversations.filter(isStoredConversation);
  let changed = valid.length !== conversations.length;

  const sanitized = valid.map((conversation) => {
    if (!conversation.messages.some((message) => message.isStreaming)) return conversation;
    changed = true;
    return {
      ...conversation,
      messages: conversation.messages.map((message) =>
        message.isStreaming ? { ...message, isStreaming: false } : message
      ),
    };
  });

  return changed ? sanitized : valid;
}

interface ConversationsState {
  conversations: Conversation[];
  createConversation: () => string;
  deleteConversation: (id: string) => void;
  getConversation: (id: string) => Conversation | undefined;
  appendMessage: (conversationId: string, message: ChatMessage) => void;
  updateMessage: (conversationId: string, messageId: string, patch: Partial<ChatMessage>) => void;
}

export const useConversations = create<ConversationsState>()(
  persist(
    (set, get) => ({
      conversations: [],

      createConversation: () => {
        const now = new Date().toISOString();
        const conversation: Conversation = {
          id: newId(),
          title: DEFAULT_TITLE,
          createdAt: now,
          updatedAt: now,
          messages: [],
        };
        set((state) => ({ conversations: [conversation, ...state.conversations] }));
        return conversation.id;
      },

      deleteConversation: (id) => {
        set((state) => ({ conversations: state.conversations.filter((c) => c.id !== id) }));
      },

      getConversation: (id) => get().conversations.find((c) => c.id === id),

      appendMessage: (conversationId, message) => {
        set((state) => {
          const conversations = state.conversations.map((conversation) => {
            if (conversation.id !== conversationId) return conversation;

            const isFirstUserMessage =
              message.role === 'user' && !conversation.messages.some((m) => m.role === 'user');

            return {
              ...conversation,
              title: isFirstUserMessage ? deriveTitle(message.content) : conversation.title,
              updatedAt: new Date().toISOString(),
              messages: [...conversation.messages, message],
            };
          });
          return { conversations: [...conversations].sort(byUpdatedDesc) };
        });
      },

      updateMessage: (conversationId, messageId, patch) => {
        set((state) => ({
          conversations: state.conversations.map((conversation) => {
            if (conversation.id !== conversationId) return conversation;
            return {
              ...conversation,
              messages: conversation.messages.map((message) =>
                message.id === messageId ? { ...message, ...patch } : message
              ),
            };
          }),
        }));
      },
    }),
    {
      name: CONVERSATIONS_STORAGE_KEY,
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ conversations: state.conversations }),

      // El saneado va en la LECTURA, no en la escritura: `partialize` solo limpiaría lo
      // que se guarde a partir de ahora y dejaría rotos para siempre a los usuarios que
      // ya tienen un `isStreaming: true` en su localStorage de una recarga a media
      // respuesta. Aquí se arregla también ese historial.
      //
      // La mutación in situ es el idiom del middleware: para `localStorage` (síncrono) la
      // hidratación termina dentro de `create()`, antes de que ningún componente se haya
      // suscrito, así que no hay render que invalidar.
      onRehydrateStorage: () => (state) => {
        if (!state) return;
        state.conversations = clearStreamingFlags(state.conversations);
      },
    }
  )
);
