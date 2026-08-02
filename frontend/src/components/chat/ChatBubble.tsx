import type { ChatMessage } from '@/types/chat';
import { ChatComparisonAnswers } from './ChatComparisonAnswers';
import { ChatMessageContent } from './ChatMessageContent';
import { ChatSources } from './ChatSources';
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
}

export function ChatBubble({ message }: ChatBubbleProps) {
  const isUser = message.role === 'user';
  const isComparison = !isUser && (message.answers?.length ?? 0) > 1;

  return (
    <div
      data-chat-message-id={message.id}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div
        data-testid={isUser ? 'chat-bubble-user' : 'chat-bubble-assistant'}
        className={`relative rounded-xl px-3.5 py-2.5 shadow-sm ${
          isComparison ? 'w-[96%]' : 'max-w-[92%]'
        } ${
          isUser ? 'rounded-tr-none bg-primary-100' : 'rounded-tl-none bg-card border border-border'
        }`}
      >
        {!isUser && message.editorial ? (
          <EditorialChatAnswer message={message} />
        ) : !isUser && message.answers ? (
          <ChatComparisonAnswers answers={message.answers} comparisonId={message.comparisonId} />
        ) : (
          <ChatMessageContent content={message.content} isUser={isUser} />
        )}
        {message.isStreaming && !message.answers && (
          <span className='ml-0.5 animate-pulse text-muted-foreground'>▍</span>
        )}
        {!isUser && message.sources && <ChatSources sources={message.sources} />}
        <span className='mt-1 block text-right text-[0.6875rem] text-muted-foreground'>
          {formatTime(message.createdAt)}
        </span>
      </div>
    </div>
  );
}
