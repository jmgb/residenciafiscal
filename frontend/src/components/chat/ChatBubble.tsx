import type { ChatMessage } from '@/types/chat';
import { ChatComparisonAnswers } from './ChatComparisonAnswers';
import { ChatMessageActions } from './ChatMessageActions';
import { ChatMessageContent } from './ChatMessageContent';
import { ChatSources } from './ChatSources';
import { DeepResearchCard } from './DeepResearchCard';
import { EditorialChatAnswer } from './EditorialChatAnswer';

function formatTime(isoString: string): string {
  try {
    return new Date(isoString).toLocaleTimeString('es-ES', {
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}

interface ChatBubbleProps {
  message: ChatMessage;
  hideComparisonVote?: boolean;
  onCancelDeepResearch?: (jobId: string) => void;
}

export function ChatBubble({
  message,
  hideComparisonVote = false,
  onCancelDeepResearch,
}: ChatBubbleProps) {
  const isUser = message.role === 'user';
  const isComparison = !isUser && (message.answers?.length ?? 0) > 1;
  const isDeepResearch = !isUser && message.deepResearch !== undefined;

  return (
    <div
      data-chat-message-id={message.id}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div
        data-testid={isUser ? 'chat-bubble-user' : 'chat-bubble-assistant'}
        className={
          isDeepResearch
            ? 'relative w-full max-w-full'
            : `relative px-3.5 py-2.5 ${isComparison ? 'w-[96%]' : 'max-w-[92%]'} ${
                isUser ? 'rounded-3xl bg-black' : 'bg-transparent'
              }`
        }
      >
        {!isUser && message.deepResearch ? (
          <DeepResearchCard
            job={message.deepResearch}
            comparisonId={message.deepResearch.comparisonId}
            onCancel={() => onCancelDeepResearch?.(message.deepResearch?.jobId ?? '')}
          />
        ) : !isUser && message.editorial ? (
          <EditorialChatAnswer message={message} />
        ) : !isUser && message.answers ? (
          <ChatComparisonAnswers
            answers={message.answers}
            comparisonId={message.comparisonId}
            showVote={!hideComparisonVote}
          />
        ) : (
          <ChatMessageContent content={message.content} isUser={isUser} />
        )}
        {!isUser &&
          !isDeepResearch &&
          !message.isStreaming &&
          !message.answers &&
          !message.editorial && (
            <ChatMessageActions
              content={message.content}
              messageId={message.id}
              sources={message.sources ?? []}
            />
          )}
        {message.isStreaming && !message.answers && (
          <span className='ml-0.5 animate-pulse text-muted-foreground'>▍</span>
        )}
        {!isUser && message.sources && (
          <ChatSources id={`chat-sources-${message.id}`} sources={message.sources} />
        )}
        <span
          className={`mt-1 block text-right text-[0.6875rem] ${
            isUser ? 'text-primary-foreground/70' : 'text-muted-foreground'
          }`}
        >
          {formatTime(message.createdAt)}
        </span>
      </div>
    </div>
  );
}
