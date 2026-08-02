import type { ChatMessage } from '@/types/chat';
import { ChatMessageContent } from './ChatMessageContent';

interface EditorialChatAnswerProps {
  message: ChatMessage;
}

const formatDate = (date: string) => {
  const [year, month, day] = date.split('-').map(Number);
  return new Intl.DateTimeFormat('es-ES', { dateStyle: 'medium' }).format(
    new Date(year, month - 1, day)
  );
};

export const EditorialChatAnswer = ({ message }: EditorialChatAnswerProps) => {
  const editorial = message.editorial;
  if (!editorial) return null;

  return (
    <section aria-label='Respuesta editorial'>
      <div className='mb-3 flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3'>
        <h3 className='font-heading text-sm font-semibold text-foreground'>Respuesta editorial</h3>
        <span className='rounded-full bg-muted px-2.5 py-1 text-[0.6875rem] font-medium text-secondary-foreground'>
          Actualizada el {formatDate(editorial.updatedAt)}
        </span>
      </div>

      <ChatMessageContent content={message.content} isUser={false} />

      <div className='mt-4 border-t border-border pt-3'>
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
              <p className='mt-1.5 font-mono text-[0.625rem]'>{source.ecli}</p>
              <p className='mt-1 break-all font-mono text-[0.625rem]'>
                PDF SHA-256: {source.sourceSha256}
              </p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
};
