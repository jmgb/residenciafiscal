import { FlaskConical } from 'lucide-react';
import type { ChatStrategyAnswer, ChatStrategyId } from '@/types/chat';
import { ChatMessageContent } from './ChatMessageContent';

const STRATEGY_LABEL: Record<ChatStrategyId, string> = {
  current_structured: 'Corpus estructurado',
  gemini_file_search: 'Gemini File Search',
};

const STRATEGY_ARIA_LABEL: Record<ChatStrategyId, string> = {
  current_structured: 'Respuesta con corpus estructurado',
  gemini_file_search: 'Respuesta con Gemini File Search',
};

const STATUS_LABEL = {
  completa: 'Respuesta completa',
  parcial: 'Respuesta parcial',
  pregunta: 'Necesita más datos',
  abstención: 'Sin cobertura suficiente',
  error: 'Error aislado',
} as const;

interface ChatComparisonAnswersProps {
  answers: ChatStrategyAnswer[];
}

export function ChatComparisonAnswers({ answers }: ChatComparisonAnswersProps) {
  return (
    <div className='flex flex-col gap-3'>
      <p className='flex items-start gap-1.5 rounded-md bg-accent px-2.5 py-2 text-xs text-accent-foreground'>
        <FlaskConical className='mt-0.5 h-3.5 w-3.5 shrink-0' aria-hidden='true' />
        Comparación experimental: las dos estrategias recuperan y responden de forma independiente.
      </p>
      {answers.map((answer) => (
        <section
          key={answer.strategy}
          aria-label={STRATEGY_ARIA_LABEL[answer.strategy]}
          className='rounded-lg border border-border bg-background p-3'
        >
          <div className='mb-2 flex flex-wrap items-center justify-between gap-2'>
            <h3 className='text-sm font-semibold text-foreground'>
              {STRATEGY_LABEL[answer.strategy]}
            </h3>
            {answer.status && (
              <span className='rounded bg-muted px-2 py-0.5 text-[0.6875rem] text-secondary-foreground'>
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
            <div className='mt-3 border-t border-border pt-2'>
              <h4 className='text-xs font-semibold uppercase tracking-wide text-muted-foreground'>
                Citas verificadas ({answer.sources.length})
              </h4>
              <ul className='mt-1.5 flex flex-col gap-2'>
                {answer.sources.map((source) => (
                  <li
                    key={`${source.judgmentId}:${source.page}:${source.quote}`}
                    className='rounded-md bg-muted px-2.5 py-2 text-xs'
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
            <div className='mt-3 rounded-md bg-muted px-2.5 py-2 text-xs text-secondary-foreground'>
              <p className='font-semibold'>Límites detectados</p>
              <ul className='mt-1 list-disc pl-4'>
                {answer.limits.map((limit) => (
                  <li key={limit}>{limit}</li>
                ))}
              </ul>
            </div>
          )}

          {answer.cost && (
            <div className='mt-3 border-t border-border pt-2 text-xs text-muted-foreground'>
              <p>
                Coste de esta respuesta: <strong>USD {answer.cost.amountUsd}</strong> ·{' '}
                {answer.cost.measurement === 'ACTUAL' ? 'uso medido' : 'estimación'}
              </p>
              <p className='mt-0.5'>No incluye la preparación previa del corpus.</p>
            </div>
          )}
        </section>
      ))}
    </div>
  );
}
