/**
 * Historial de conversaciones, persistido en localStorage.
 *
 * La copia que permite reabrir conversaciones sigue siendo local al navegador.
 * El backend persiste por separado cada turno aceptado y sus respuestas A/B,
 * pero no reconstruye ni sincroniza este historial de Zustand. La versión vive
 * en el payload; la clave histórica se mantiene estable para poder migrar sin
 * perder conversaciones existentes.
 */
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import { isChatSourceV2, isLegacyChatSource } from '@/lib/chat-source';
import type {
  ChatMarginalCost,
  ChatMessage,
  ChatSource,
  ChatStrategyAnswer,
  ChatStrategyFailureCode,
  ChatStrategySource,
  Conversation,
  EditorialChatAttribution,
  EditorialChatSource,
} from '@/types/chat';

export const CONVERSATIONS_STORAGE_KEY = 'rf.conversations.v1';
const CONVERSATIONS_STORAGE_VERSION = 5;

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

const validAccessToken = (value: unknown): value is string =>
  typeof value === 'string' && /^[0-9a-f]{64}$/.test(value);

const newAccessToken = (): string => {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  return [...bytes].map((value) => value.toString(16).padStart(2, '0')).join('');
};

function byUpdatedDesc(a: Conversation, b: Conversation): number {
  return b.updatedAt.localeCompare(a.updatedAt);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isStoredSource(value: unknown): value is ChatSource {
  return isChatSourceV2(value) || isLegacyChatSource(value);
}

function isStoredStrategySource(value: unknown): value is ChatStrategySource {
  if (!isRecord(value)) return false;
  return (
    (value.strategy === 'current_structured' || value.strategy === 'gemini_file_search') &&
    typeof value.judgmentId === 'string' &&
    Number.isSafeInteger(value.page) &&
    (value.page as number) > 0 &&
    typeof value.sourceSha256 === 'string' &&
    /^[0-9a-f]{64}$/i.test(value.sourceSha256) &&
    typeof value.quote === 'string' &&
    value.quote.trim().length > 0 &&
    value.verification === 'EXACT'
  );
}

function isStoredFailureCode(value: unknown): value is ChatStrategyFailureCode {
  return (
    value === 'timeout' ||
    value === 'exception' ||
    value === 'strategy_contract' ||
    value === 'citation_verification' ||
    value === 'evidence_validation'
  );
}

function isStoredEditorialSource(value: unknown): value is EditorialChatSource {
  if (!isRecord(value)) return false;
  return (
    typeof value.judgmentId === 'string' &&
    /^[a-z0-9-]+$/.test(value.judgmentId) &&
    typeof value.roj === 'string' &&
    value.roj.trim().length > 0 &&
    typeof value.ecli === 'string' &&
    value.ecli.startsWith('ECLI:') &&
    Number.isSafeInteger(value.page) &&
    (value.page as number) > 0 &&
    typeof value.sourceSha256 === 'string' &&
    /^[0-9a-f]{64}$/i.test(value.sourceSha256) &&
    typeof value.quote === 'string' &&
    value.quote.trim().length > 0 &&
    value.verification === 'EXACT'
  );
}

function isStoredEditorial(value: unknown): value is EditorialChatAttribution {
  if (!isRecord(value)) return false;
  return (
    typeof value.answerId === 'string' &&
    /^[a-z0-9-]+$/.test(value.answerId) &&
    typeof value.version === 'string' &&
    /^home-editorial-\d{4}-\d{2}-\d{2}-v\d+$/.test(value.version) &&
    typeof value.updatedAt === 'string' &&
    /^\d{4}-\d{2}-\d{2}$/.test(value.updatedAt) &&
    Array.isArray(value.sources) &&
    value.sources.length > 0 &&
    value.sources.every(isStoredEditorialSource)
  );
}

function isStoredCost(value: unknown): value is ChatMarginalCost {
  if (!isRecord(value)) return false;
  const unavailable = value.measurement === 'UNAVAILABLE';
  return (
    value.currency === 'USD' &&
    (unavailable
      ? value.amountUsd === null &&
        value.costMicrousd === null &&
        value.inputTokens === null &&
        value.outputTokens === null &&
        value.retrievedDocumentTokens === null
      : typeof value.amountUsd === 'string' &&
        /^\d+\.\d{6}$/.test(value.amountUsd) &&
        Number.isSafeInteger(value.costMicrousd) &&
        (value.costMicrousd as number) >= 0 &&
        (value.measurement === 'ACTUAL' || value.measurement === 'ESTIMATED') &&
        Number.isSafeInteger(value.inputTokens) &&
        (value.inputTokens as number) >= 0 &&
        Number.isSafeInteger(value.outputTokens) &&
        (value.outputTokens as number) >= 0 &&
        Number.isSafeInteger(value.retrievedDocumentTokens) &&
        (value.retrievedDocumentTokens as number) >= 0) &&
    value.scope === 'REQUEST_MARGINAL' &&
    typeof value.pricingVersion === 'string' &&
    value.excludesCorpusPreparation === true
  );
}

function isStoredAnswer(value: unknown): value is ChatStrategyAnswer {
  if (!isRecord(value)) return false;
  const validStatus =
    value.status === undefined ||
    ['completa', 'parcial', 'pregunta', 'abstención', 'error'].includes(value.status as string);
  return (
    (value.strategy === 'current_structured' || value.strategy === 'gemini_file_search') &&
    validStatus &&
    typeof value.content === 'string' &&
    Array.isArray(value.sources) &&
    value.sources.every(isStoredStrategySource) &&
    Array.isArray(value.limits) &&
    value.limits.every((limit) => typeof limit === 'string') &&
    (value.cost === undefined || isStoredCost(value.cost)) &&
    (value.model === undefined || typeof value.model === 'string') &&
    (value.failureCode === undefined || isStoredFailureCode(value.failureCode)) &&
    (value.latencyMs === undefined ||
      (Number.isSafeInteger(value.latencyMs) && (value.latencyMs as number) >= 0)) &&
    typeof value.isStreaming === 'boolean'
  );
}

function isStoredMessage(value: unknown): value is ChatMessage {
  if (!isRecord(value)) return false;
  return (
    typeof value.id === 'string' &&
    (value.role === 'user' || value.role === 'assistant') &&
    typeof value.content === 'string' &&
    typeof value.createdAt === 'string' &&
    (value.comparisonId === undefined ||
      (typeof value.comparisonId === 'string' && /^chat-[\w-]{1,123}$/.test(value.comparisonId))) &&
    (value.isStreaming === undefined || typeof value.isStreaming === 'boolean') &&
    (value.sources === undefined ||
      (Array.isArray(value.sources) && value.sources.every(isStoredSource))) &&
    (value.answers === undefined ||
      (Array.isArray(value.answers) && value.answers.every(isStoredAnswer))) &&
    (value.editorial === undefined ||
      (value.role === 'assistant' &&
        value.content.trim().length > 0 &&
        isStoredEditorial(value.editorial)))
  );
}

type StoredConversation = Omit<Conversation, 'ledgerId' | 'accessToken'> & {
  ledgerId?: string;
  accessToken?: string;
};

function isStoredConversation(value: unknown): value is StoredConversation {
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
  return (
    (value.ledgerId === undefined ||
      (typeof value.ledgerId === 'string' && /^[\w-]{1,128}$/.test(value.ledgerId))) &&
    (value.accessToken === undefined || validAccessToken(value.accessToken)) &&
    value.messages.every(isStoredMessage)
  );
}

/**
 * Apaga los flags transitorios de todos los mensajes.
 *
 * Un mensaje solo está en streaming mientras vive el generador que lo alimenta, y ese
 * generador no sobrevive a una recarga. Rehidratar `isStreaming: true` deja un cursor
 * parpadeando para siempre y sin forma de recuperarse. Del mismo modo, una petición de
 * cancelación pendiente no sobrevive a una recarga. El texto que alcanzó a llegar se
 * conserva tal cual. Devuelve el mismo array si no había nada que sanear, para no
 * invalidar referencias sin motivo.
 */
export function clearStreamingFlags(conversations: unknown): Conversation[] {
  if (!Array.isArray(conversations)) return [];

  const valid = conversations.filter(isStoredConversation);
  let changed = valid.length !== conversations.length;
  const secured: Conversation[] = valid.map((conversation) => {
    if (conversation.ledgerId && conversation.accessToken) return conversation as Conversation;
    changed = true;
    const messages = conversation.messages.map((message) => {
      // Los comparisonId y jobs anteriores pertenecen al UUID visible que se
      // acaba de abandonar. No deben combinarse con el ledger nuevo.
      const { comparisonId: _legacyComparisonId, ...withoutComparison } = message;
      if (!message.deepResearch) return withoutComparison;
      const { cancellationRequested: _pendingCancellation, ...deepResearch } = message.deepResearch;
      const wasActive = deepResearch.status === 'queued' || deepResearch.status === 'running';
      return {
        ...withoutComparison,
        deepResearch: {
          ...deepResearch,
          comparisonId: null,
          ...(wasActive
            ? {
                status: 'error' as const,
                stage: 'error' as const,
                result: null,
                error:
                  'Esta investigación pertenecía a una versión anterior. Tras la actualización, iníciala de nuevo.',
              }
            : {}),
        },
      };
    });
    return {
      ...conversation,
      // Un historial previo a este contrato empieza un hilo nuevo en el servidor:
      // así nadie puede reclamar por primera vez un UUID antiguo visto en una URL.
      ledgerId: newId(),
      accessToken: newAccessToken(),
      messages,
    };
  });

  const sanitized = secured.map((conversation) => {
    if (
      !conversation.messages.some(
        (message) =>
          message.isStreaming ||
          message.deepResearch?.cancellationRequested ||
          message.answers?.some((answer) => answer.isStreaming)
      )
    ) {
      return conversation;
    }
    changed = true;
    return {
      ...conversation,
      messages: conversation.messages.map((message) => {
        const hasStreamingFlag =
          message.isStreaming || message.answers?.some((answer) => answer.isStreaming);
        const hasCancellationFlag = message.deepResearch?.cancellationRequested;
        if (!hasStreamingFlag && !hasCancellationFlag) return message;

        let deepResearch = message.deepResearch;
        if (deepResearch?.cancellationRequested) {
          deepResearch = { ...deepResearch };
          delete deepResearch.cancellationRequested;
        }

        return {
          ...message,
          ...(hasStreamingFlag
            ? {
                isStreaming: false,
                answers: message.answers?.map((answer) => ({ ...answer, isStreaming: false })),
              }
            : {}),
          ...(deepResearch ? { deepResearch } : {}),
        };
      }),
    };
  });

  return changed ? sanitized : secured;
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
        const id = newId();
        const conversation: Conversation = {
          id,
          ledgerId: id,
          accessToken: newAccessToken(),
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
      version: CONVERSATIONS_STORAGE_VERSION,
      migrate: (persistedState) => ({
        conversations: clearStreamingFlags(
          isRecord(persistedState) ? persistedState.conversations : undefined
        ),
      }),

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
