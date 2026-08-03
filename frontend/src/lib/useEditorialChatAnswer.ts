import { useCallback } from 'react';
import { useNavigate } from 'react-router';
import { trackEvent } from '@/components/layout/PostHogAnalytics';
import { useConversations } from '@/stores/useConversations';
import type { EditorialChatAnswer } from '@/types/chat';

interface EditorialChatAnswerOptions {
  conversationId?: string;
  countryPath: string;
}

interface EditorialChatAnswerRun {
  conversationId: string;
  completion: Promise<void>;
}

export const EDITORIAL_ANSWER_DELAY_MS = 12_000;

const waitForEditorialAnswer = (signal: AbortSignal): Promise<boolean> =>
  new Promise((resolve) => {
    if (signal.aborted) {
      resolve(false);
      return;
    }

    const onAbort = () => {
      clearTimeout(timeout);
      resolve(false);
    };
    const timeout = setTimeout(() => {
      signal.removeEventListener('abort', onAbort);
      resolve(true);
    }, EDITORIAL_ANSWER_DELAY_MS);
    signal.addEventListener('abort', onAbort, { once: true });
  });

const newMessageId = (): string => {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return crypto.randomUUID();
  return `msg-${Math.random().toString(36).slice(2)}-${Date.now()}`;
};

export const useEditorialChatAnswer = ({
  conversationId,
  countryPath,
}: EditorialChatAnswerOptions) => {
  const navigate = useNavigate();
  const createConversation = useConversations((state) => state.createConversation);
  const appendMessage = useConversations((state) => state.appendMessage);
  const updateMessage = useConversations((state) => state.updateMessage);

  return useCallback(
    (answer: EditorialChatAnswer, signal: AbortSignal): EditorialChatAnswerRun => {
      const existing = conversationId
        ? useConversations.getState().getConversation(conversationId)
        : undefined;
      const targetId = existing?.id ?? createConversation();
      if (targetId !== conversationId) navigate(`/c/${targetId}`, { replace: true });

      const now = new Date().toISOString();
      appendMessage(targetId, {
        id: newMessageId(),
        role: 'user',
        content: answer.question,
        createdAt: now,
      });
      const assistantId = newMessageId();
      appendMessage(targetId, {
        id: assistantId,
        role: 'assistant',
        content: '',
        createdAt: now,
        isStreaming: true,
      });

      const completion = waitForEditorialAnswer(signal).then((completed) => {
        if (!completed) {
          updateMessage(targetId, assistantId, {
            content: 'Respuesta detenida.',
            isStreaming: false,
          });
          return;
        }

        updateMessage(targetId, assistantId, {
          content: answer.content,
          isStreaming: false,
          editorial: {
            answerId: answer.id,
            version: answer.version,
            updatedAt: answer.updatedAt,
            sources: answer.sources.map((source) => ({ ...source })),
          },
        });
        trackEvent('respuesta_editorial_mostrada', {
          pais: countryPath,
          answer_id: answer.id,
          version: answer.version,
        });
      });

      return { conversationId: targetId, completion };
    },
    [appendMessage, conversationId, countryPath, createConversation, navigate, updateMessage]
  );
};
