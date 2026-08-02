import type { ChatStrategyAnswer } from '@/types/chat';
import { ChatMessageContent } from './ChatMessageContent';

const STATUS_LABEL = {
  completa: 'Respuesta completa',
  parcial: 'Respuesta parcial',
  pregunta: 'Necesita más datos',
  abstención: 'Sin cobertura suficiente',
  error: 'Error aislado',
} as const;

interface ChatStrategyAnswerPanelProps {
  answer: ChatStrategyAnswer;
  label: string;
  className?: string;
  id?: string;
  labelledBy?: string;
  ariaLabel?: string;
  tabPanel?: boolean;
}

export const ChatStrategyAnswerPanel = ({
  answer,
  label,
  className,
  id,
  labelledBy,
  ariaLabel,
  tabPanel = false,
}: ChatStrategyAnswerPanelProps) => (
  <section
    id={id}
    role={tabPanel ? 'tabpanel' : 'region'}
    aria-labelledby={labelledBy}
    aria-label={labelledBy ? undefined : (ariaLabel ?? label)}
    className={`min-w-0 rounded-xl border border-border bg-background p-4 ${className ?? ''}`}
  >
    <div className='mb-3 flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3'>
      <h3 className='font-heading text-sm font-semibold text-foreground'>{label}</h3>
      {answer.status && (
        <span className='rounded-full bg-muted px-2.5 py-1 text-[0.6875rem] font-medium text-secondary-foreground'>
          {STATUS_LABEL[answer.status]}
        </span>
      )}
    </div>

    {answer.content ? (
      <ChatMessageContent content={answer.content} isUser={false} />
    ) : answer.isStreaming ? (
      <p className='text-sm text-muted-foreground'>Preparando respuesta…</p>
    ) : null}
    {answer.isStreaming && <span className='animate-pulse text-muted-foreground'>▍</span>}

    {answer.sources.length > 0 && (
      <div className='mt-4 border-t border-border pt-3'>
        <h4 className='text-xs font-semibold uppercase tracking-wide text-muted-foreground'>
          Citas verificadas ({answer.sources.length})
        </h4>
        <ul className='mt-2 flex flex-col gap-2'>
          {answer.sources.map((source) => (
            <li
              key={`${source.judgmentId}:${source.page}:${source.quote}`}
              className='rounded-lg bg-muted px-3 py-2.5 text-xs'
            >
              <p className='font-semibold text-foreground'>
                {source.judgmentId} · Página PDF {source.page}
              </p>
              <blockquote className='mt-1.5 border-l-2 border-primary/40 pl-2 leading-relaxed'>
                {source.quote}
              </blockquote>
              <p className='mt-1.5 break-all font-mono text-[0.625rem] text-muted-foreground'>
                PDF SHA-256: {source.sourceSha256}
              </p>
            </li>
          ))}
        </ul>
      </div>
    )}

    {answer.limits.length > 0 && (
      <div className='mt-4 rounded-lg bg-muted px-3 py-2.5 text-xs text-secondary-foreground'>
        <p className='font-semibold'>Límites detectados</p>
        <ul className='mt-1 list-disc space-y-1 pl-4'>
          {answer.limits.map((limit) => (
            <li key={limit}>{limit}</li>
          ))}
        </ul>
      </div>
    )}

    {answer.cost && (
      <div className='mt-4 border-t border-border pt-3 text-xs text-muted-foreground'>
        <p>
          Coste de esta respuesta:{' '}
          <strong>
            {answer.cost.measurement === 'UNAVAILABLE'
              ? 'no disponible'
              : `USD ${answer.cost.amountUsd}`}
          </strong>
          {answer.cost.measurement !== 'UNAVAILABLE' && (
            <> · {answer.cost.measurement === 'ACTUAL' ? 'uso medido' : 'estimación'}</>
          )}
        </p>
        <p className='mt-0.5'>No incluye la preparación previa del corpus.</p>
      </div>
    )}
  </section>
);
