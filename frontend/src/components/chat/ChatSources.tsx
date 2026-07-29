import { ChevronDown, FileText } from 'lucide-react';
import { useState } from 'react';
import { cn } from '@/shared/lib/utils';
import type { ChatSource } from '@/types/chat';

const RESULTADO_LABEL: Record<string, string> = {
  GANA_AEAT: 'Gana AEAT',
  GANA_CONTRIBUYENTE: 'Gana contribuyente',
  PARCIAL: 'Parcial',
  RETROACCION: 'Retroacción',
  INADMISION: 'Inadmisión',
  DESCONOCIDO: 'Sin clasificar',
};

/** Abrevia el órgano largo del pipeline a algo legible en un chip. */
function shortOrgano(organo: string): string {
  if (organo.startsWith('Tribunal Supremo')) return 'Tribunal Supremo';
  if (organo.startsWith('Audiencia Nacional')) return 'Audiencia Nacional';
  return organo.split('.')[0] ?? organo;
}

function year(fecha: string): string {
  return fecha.slice(0, 4);
}

interface ChatSourcesProps {
  sources: ChatSource[];
}

export function ChatSources({ sources }: ChatSourcesProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (sources.length === 0) return null;

  return (
    <section aria-label='Sentencias citadas' className='mt-3 border-t border-border pt-3'>
      <h3 className='mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground'>
        Sentencias citadas ({sources.length})
      </h3>
      <ul className='flex flex-col gap-1.5'>
        {sources.map((source) => {
          const isExpanded = expandedId === source.archivo;
          return (
            <li key={source.archivo}>
              <button
                type='button'
                onClick={() => setExpandedId(isExpanded ? null : source.archivo)}
                aria-expanded={isExpanded}
                className='flex w-full items-center gap-2 rounded-lg border border-border bg-background px-2.5 py-2 text-left text-xs transition-colors hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-ring'
              >
                <FileText className='h-3.5 w-3.5 shrink-0 text-primary' aria-hidden='true' />
                <span className='font-semibold text-foreground'>{source.roj}</span>
                <span className='truncate text-muted-foreground'>
                  {shortOrgano(source.organo)} · {year(source.fecha)}
                </span>
                <span className='ml-auto shrink-0 rounded bg-muted px-1.5 py-0.5 text-[0.6875rem] text-muted-foreground'>
                  {RESULTADO_LABEL[source.resultado] ?? source.resultado}
                </span>
                <ChevronDown
                  className={cn(
                    'h-3.5 w-3.5 shrink-0 transition-transform',
                    isExpanded && 'rotate-180'
                  )}
                  aria-hidden='true'
                />
              </button>
              {isExpanded && (
                <div className='mt-1 rounded-lg bg-muted px-3 py-2 text-xs leading-relaxed text-muted-foreground'>
                  <p>{source.extracto}</p>
                  <p className='mt-1.5 font-mono text-[0.6875rem]'>{source.ecli}</p>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
