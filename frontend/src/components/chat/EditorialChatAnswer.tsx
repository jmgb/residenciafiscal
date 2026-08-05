import type { ChatMessage } from '@/types/chat';
import { ChatMessageActions } from './ChatMessageActions';
import { ChatMessageContent } from './ChatMessageContent';
import { JudgmentDocumentActions } from './JudgmentDocumentActions';

interface EditorialChatAnswerProps {
  message: ChatMessage;
}

export const EditorialChatAnswer = ({ message }: EditorialChatAnswerProps) => {
  const editorial = message.editorial;
  if (!editorial) return null;

  return (
    <section aria-label='Respuesta editorial'>
      <ChatMessageContent content={message.content} isUser={false} />

      <ChatMessageActions
        content={message.content}
        sourcesId={`chat-editorial-sources-${message.id}`}
        verifiedSources={editorial.sources.map((source) => ({
          label: source.roj,
          ecli: source.ecli,
          page: source.page,
          sourceSha256: source.sourceSha256,
          quote: source.quote,
          verification: source.verification,
        }))}
      />

      <div id={`chat-editorial-sources-${message.id}`} className='mt-4 border-t border-border pt-3'>
        <h4 className='text-xs font-semibold uppercase tracking-wide text-muted-foreground'>
          Citas verificadas ({editorial.sources.length})
        </h4>
        <ul className='mt-2 flex flex-col gap-2'>
          {editorial.sources.map((source) => (
            <li
              key={`${source.judgmentId}:${source.page}:${source.quote}`}
              className='rounded-lg bg-muted px-3 py-2.5 text-xs text-secondary-foreground'
            >
              <p className='font-semibold text-foreground'>
                {source.roj} · Página PDF {source.page}
              </p>
              <blockquote className='mt-1.5 border-l-2 border-primary/40 pl-2 leading-relaxed'>
                {source.quote}
              </blockquote>
              <JudgmentDocumentActions judgmentId={source.judgmentId} ecli={source.ecli} />
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
};
