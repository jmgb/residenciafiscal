/**
 * Historial de conversaciones, persistido en localStorage.
 *
 * No hay cuentas ni backend: el historial es local al navegador. La clave está
 * VERSIONADA para poder cambiar la forma de los datos sin dejar al usuario con
 * un store corrupto.
 */
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import type { ChatMessage, Conversation } from '@/types/chat';

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
    }
  )
);
