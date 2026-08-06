import { useCallback } from 'react';
import { useNavigate } from 'react-router';
import { trackEvent } from '@/components/layout/PostHogAnalytics';
import { recordEditorialTurn } from '@/lib/editorial-chat-record';
import { useConversations } from '@/stores/useConversations';
import type { EditorialChatAnswer } from '@/types/chat';

interface EditorialChatAnswerOptions {
  conversationId?: string;
  countryPath: string;
  /** Con el motor simulado no hay ledger al que registrar el turno. */
  isStub?: boolean;
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
  isStub = false,
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
      const targetConversation = useConversations.getState().getConversation(targetId);
      if (!targetConversation) throw new Error('No se pudo crear la conversación editorial');
      if (targetId !== conversationId) navigate(`/c/${targetId}`, { replace: true });

      const now = new Date().toISOString();
      const userMessageId = newMessageId();
      const assistantId = newMessageId();
      appendMessage(targetId, {
        id: userMessageId,
        role: 'user',
        content: answer.question,
        createdAt: now,
      });
      appendMessage(targetId, {
        id: assistantId,
        role: 'assistant',
        content: '',
        createdAt: now,
        isStreaming: true,
      });

      const completion = waitForEditorialAnswer(signal).then(async (completed) => {
        if (!completed) {
          updateMessage(targetId, assistantId, {
            content: 'Respuesta detenida.',
            isStreaming: false,
          });
          return;
        }

        // La respuesta se hace visible antes de persistirla, pero conserva el
        // estado streaming para bloquear seguimientos hasta terminar el registro.
        // Así, si el usuario cancela cuando el servidor ya pudo confirmar el
        // turno, navegador y ledger no discrepan sobre lo que llegó a mostrarse.
        updateMessage(targetId, assistantId, {
          content: answer.content,
          isStreaming: !isStub,
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

        // El servidor no ve estas respuestas —se resuelven aquí—, así que sin
        // este registro un seguimiento sobre ellas llegaría sin antecedente. Se
        // espera antes de liberar el composer; un timeout de red conserva la
        // degradación sin contexto.
        if (!isStub) {
          await recordEditorialTurn(
            {
              conversationId: targetConversation.ledgerId,
              conversationAccessToken: targetConversation.accessToken,
              userMessageId,
              countryPath,
              answerId: answer.id,
            },
            signal
          );
          updateMessage(targetId, assistantId, { isStreaming: false });
        }
      });

      return { conversationId: targetId, completion };
    },
    [
      appendMessage,
      conversationId,
      countryPath,
      createConversation,
      isStub,
      navigate,
      updateMessage,
    ]
  );
};
