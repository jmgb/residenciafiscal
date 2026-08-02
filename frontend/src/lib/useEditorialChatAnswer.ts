import { useCallback } from 'react';
import { useNavigate } from 'react-router';
import { trackEvent } from '@/components/layout/PostHogAnalytics';
import { useConversations } from '@/stores/useConversations';
import type { EditorialChatAnswer } from '@/types/chat';

interface EditorialChatAnswerOptions {
  conversationId?: string;
  countryPath: string;
}

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

  return useCallback(
    (answer: EditorialChatAnswer) => {
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
      appendMessage(targetId, {
        id: newMessageId(),
        role: 'assistant',
        content: answer.content,
        createdAt: now,
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
    },
    [appendMessage, conversationId, countryPath, createConversation, navigate]
  );
};
