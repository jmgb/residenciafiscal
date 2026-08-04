import { useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router';
import { trackEvent } from '@/components/layout/PostHogAnalytics';
import {
  cancelDeepResearch,
  getDeepResearchStatus,
  startDeepResearch,
} from '@/lib/deep-research-client';
import { useConversations } from '@/stores/useConversations';
import type { ChatMessage, DeepResearchJob } from '@/types/chat';

export const messagePatchForDeepResearchStatus = (
  job: DeepResearchJob
): Pick<ChatMessage, 'deepResearch'> & Partial<Pick<ChatMessage, 'content'>> => {
  if (job.status !== 'completed' || !job.result) return { deepResearch: job };
  return { content: job.result.text, deepResearch: job };
};

export const withDeepResearchCancelError = (job: DeepResearchJob): DeepResearchJob => ({
  ...job,
  error: 'No se ha podido cancelar la investigación.',
});

export const mergeDeepResearchPoll = (
  previous: DeepResearchJob,
  next: DeepResearchJob
): DeepResearchJob => {
  const nextIsActive = next.status === 'queued' || next.status === 'running';
  if (!nextIsActive || next.error || !previous.error) return next;
  return { ...next, error: previous.error };
};

export const comparisonIdForLatestQuestion = (messages: ChatMessage[]): string | undefined => {
  const latestQuestionIndex = messages.reduce(
    (latest, message, index) => (message.role === 'user' ? index : latest),
    -1
  );
  if (latestQuestionIndex < 0) return undefined;
  return messages.slice(latestQuestionIndex + 1).find((message) => message.role === 'assistant')
    ?.comparisonId;
};

interface DeepResearchControllerInput {
  conversationId?: string;
  countryPath: string;
  createMessageId(): string;
  isStreaming: boolean;
  messages: ChatMessage[];
}

export const useDeepResearch = ({
  conversationId,
  countryPath,
  createMessageId,
  isStreaming,
  messages,
}: DeepResearchControllerInput) => {
  const navigate = useNavigate();
  const createConversation = useConversations((state) => state.createConversation);
  const appendMessage = useConversations((state) => state.appendMessage);
  const updateMessage = useConversations((state) => state.updateMessage);
  const deepResearchMessage = [...messages].reverse().find((message) => message.deepResearch);
  const deepResearchJob = deepResearchMessage?.deepResearch;
  const latestComparisonId = comparisonIdForLatestQuestion(messages);
  const activeDeepResearch =
    deepResearchJob?.status === 'queued' || deepResearchJob?.status === 'running';

  const start = useCallback(async () => {
    if (isStreaming || activeDeepResearch) return;
    const latestQuestion = [...messages].reverse().find((message) => message.role === 'user');
    if (!latestQuestion) return;
    const existing = conversationId
      ? useConversations.getState().getConversation(conversationId)
      : undefined;
    const targetId = existing?.id ?? createConversation();
    if (targetId !== conversationId) navigate(`/c/${targetId}`, { replace: true });
    const messageId = createMessageId();
    appendMessage(targetId, {
      id: messageId,
      role: 'assistant',
      content: '',
      createdAt: new Date().toISOString(),
      deepResearch: {
        jobId: 'pending',
        comparisonId: latestComparisonId ?? null,
        status: 'queued',
        stage: 'searching',
        result: null,
      },
    });
    try {
      const accepted = await startDeepResearch({
        conversationId: targetId,
        comparisonId: latestComparisonId ?? null,
        countryPath,
        question: latestQuestion.content,
      });
      updateMessage(targetId, messageId, {
        deepResearch: {
          jobId: accepted.jobId,
          comparisonId: latestComparisonId ?? null,
          status: 'queued',
          stage: 'searching',
          result: null,
        },
      });
      trackEvent('investigacion_profunda_iniciada', { pais: countryPath });
    } catch {
      updateMessage(targetId, messageId, {
        deepResearch: {
          jobId: 'pending',
          status: 'error',
          stage: 'error',
          result: null,
          error: 'No se ha podido poner la investigación en cola.',
        },
      });
    }
  }, [
    activeDeepResearch,
    appendMessage,
    conversationId,
    countryPath,
    createConversation,
    createMessageId,
    isStreaming,
    latestComparisonId,
    messages,
    navigate,
    updateMessage,
  ]);

  const cancel = useCallback(
    async (jobId: string) => {
      if (!conversationId || !jobId || jobId === 'pending') return;
      const message = [
        ...(useConversations.getState().getConversation(conversationId)?.messages ?? []),
      ]
        .reverse()
        .find((candidate) => candidate.deepResearch?.jobId === jobId);
      try {
        await cancelDeepResearch(jobId, conversationId);
        if (message) {
          updateMessage(conversationId, message.id, {
            deepResearch: {
              jobId,
              status: 'cancelled',
              stage: 'cancelled',
              result: null,
            },
          });
        }
      } catch {
        if (message?.deepResearch) {
          updateMessage(conversationId, message.id, {
            deepResearch: withDeepResearchCancelError(message.deepResearch),
          });
        }
      }
    },
    [conversationId, updateMessage]
  );

  const activeJobId = activeDeepResearch ? deepResearchJob?.jobId : undefined;
  useEffect(() => {
    if (!conversationId || !activeJobId || activeJobId === 'pending') return;
    let disposed = false;
    let timer: number | undefined;
    const poll = async () => {
      try {
        const next = await getDeepResearchStatus(activeJobId, conversationId);
        if (disposed) return;
        const current = useConversations.getState().getConversation(conversationId);
        const message = [...(current?.messages ?? [])]
          .reverse()
          .find((candidate) => candidate.deepResearch?.jobId === activeJobId);
        if (message) {
          const visibleNext = message.deepResearch
            ? mergeDeepResearchPoll(message.deepResearch, next)
            : next;
          updateMessage(conversationId, message.id, messagePatchForDeepResearchStatus(visibleNext));
        }
        if (next.status === 'completed' || next.status === 'cancelled' || next.status === 'error') {
          trackEvent('investigacion_profunda_respondida', {
            pais: countryPath,
            resultado: next.status,
          });
          return;
        }
      } catch {
        // Un fallo transitorio no borra el job visible; el siguiente polling reintenta.
      }
      if (!disposed) timer = window.setTimeout(poll, 2500);
    };
    timer = window.setTimeout(poll, 1200);
    return () => {
      disposed = true;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [activeJobId, conversationId, countryPath, updateMessage]);

  return {
    activeDeepResearch,
    deepResearchJob,
    cancelDeepResearch: cancel,
    startDeepResearch: start,
  };
};
