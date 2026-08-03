import { CheckCircle2, CircleAlert, LoaderCircle, Search, Square } from 'lucide-react';
import { Button } from '@/shared/components/ui/button';
import type { DeepResearchJob, DeepResearchOutput } from '@/types/chat';
import { ChatComparisonVote } from './ChatComparisonVote';
import { ChatMessageContent } from './ChatMessageContent';

interface DeepResearchCardProps {
  job: DeepResearchJob;
  comparisonId?: string | null;
  onCancel: () => void;
}

const stageLabel: Record<DeepResearchJob['stage'], string> = {
  searching: 'Buscando en el corpus',
  reading: 'Leyendo fuentes',
  verifying: 'Verificando evidencias',
  completed: 'Investigación profunda completada',
  cancelled: 'Investigación cancelada',
  error: 'No se ha podido completar la investigación',
};

const costLabel = (
  microusd: number | null,
  measurement: DeepResearchOutput['costMeasurement']
): string => {
  if (microusd === null || measurement === 'UNAVAILABLE') return 'Coste: no disponible';
  const label = measurement === 'ACTUAL' ? 'Coste real' : 'Coste estimado';
  return `${label}: ${new Intl.NumberFormat('es-ES', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(microusd / 1_000_000)} USD`;
};

const latencyLabel = (latencyMs: number): string =>
  `Respuesta en: ${new Intl.NumberFormat('es-ES', {
    minimumFractionDigits: latencyMs % 1000 === 0 ? 0 : 1,
    maximumFractionDigits: 1,
  }).format(latencyMs / 1000)} s`;

const judgmentLabel = (judgmentId: string): string => {
  const [prefix, ...rest] = judgmentId.split('-');
  const title = rest.join(' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
  return prefix?.toLowerCase() === 'sts' ? `STS ${title}` : `${prefix ?? ''} ${title}`.trim();
};

export function DeepResearchCard({ job, comparisonId, onCancel }: DeepResearchCardProps) {
  const isActive = job.status === 'queued' || job.status === 'running';
  const result = job.result;
  const statusIcon =
    job.status === 'completed' ? (
      <CheckCircle2 className='h-5 w-5 text-emerald-700' aria-hidden='true' />
    ) : job.status === 'error' || job.status === 'cancelled' ? (
      <CircleAlert className='h-5 w-5 text-accent-foreground' aria-hidden='true' />
    ) : (
      <LoaderCircle className='h-5 w-5 animate-spin text-primary' aria-hidden='true' />
    );

  return (
    <article className='w-full rounded-xl border border-border bg-card shadow-sm'>
      <div
        role='status'
        className='flex items-center gap-2 border-b border-border px-4 py-3 text-sm font-semibold text-foreground'
      >
        {statusIcon}
        <Search className='h-4 w-4 text-muted-foreground' aria-hidden='true' />
        <span>
          {job.status === 'queued' ? 'Investigación profunda en cola' : stageLabel[job.stage]}
        </span>
      </div>

      {isActive && (
        <div className='flex justify-end px-4 py-3'>
          <Button
            type='button'
            variant='outline'
            size='sm'
            onClick={onCancel}
            aria-label='Cancelar investigación profunda'
          >
            <Square className='h-3.5 w-3.5' aria-hidden='true' />
            Cancelar
          </Button>
        </div>
      )}

      {job.status === 'error' && (
        <p className='px-4 py-4 text-sm text-destructive'>{job.error ?? 'Error desconocido.'}</p>
      )}

      {job.status === 'completed' && result && (
        <div className='space-y-4 p-4'>
          <ChatMessageContent content={result.text} isUser={false} />
          {result.evidence.length > 0 && (
            <section className='rounded-lg bg-muted p-3'>
              <h3 className='mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground'>
                Evidencias verificadas
              </h3>
              <ul className='space-y-2'>
                {result.evidence.map((evidence) => (
                  <li
                    key={`${evidence.judgmentId}-${evidence.page}-${evidence.sourceSha256}-${evidence.quote}`}
                    className='text-xs leading-relaxed'
                  >
                    <p className='font-semibold text-primary'>
                      {judgmentLabel(evidence.judgmentId)} · página {evidence.page}
                    </p>
                    <p className='mt-0.5 text-muted-foreground'>“{evidence.quote}”</p>
                  </li>
                ))}
              </ul>
            </section>
          )}
          {result.limits.length > 0 && (
            <p className='text-xs leading-relaxed text-muted-foreground'>
              <strong>Límites:</strong> {result.limits.join(' ')}
            </p>
          )}
          <div className='flex flex-wrap gap-x-4 gap-y-1 border-t border-border pt-3 text-xs text-muted-foreground'>
            <span>{costLabel(result.costMicrousd, result.costMeasurement)}</span>
            <span>{latencyLabel(result.latencyMs)}</span>
            <span>Modelo: {result.model}</span>
          </div>
          {comparisonId && <ChatComparisonVote comparisonId={comparisonId} includeDeepResearch />}
        </div>
      )}
    </article>
  );
}
