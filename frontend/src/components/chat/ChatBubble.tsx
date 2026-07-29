import type { ChatMessage } from '@/types/chat';
import { ChatMessageContent } from './ChatMessageContent';
import { ChatSources } from './ChatSources';

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

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        data-testid={isUser ? 'chat-bubble-user' : 'chat-bubble-assistant'}
        className={`relative max-w-[92%] rounded-xl px-3.5 py-2.5 shadow-sm ${
          isUser ? 'rounded-tr-none bg-primary-100' : 'rounded-tl-none bg-card border border-border'
        }`}
      >
        <ChatMessageContent content={message.content} isUser={isUser} />
        {message.isStreaming && (
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
