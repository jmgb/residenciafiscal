import { ChevronDown, FileText } from 'lucide-react';
import { useState } from 'react';
import { isChatSourceV2 } from '@/lib/chat-source';
import { cn } from '@/shared/lib/utils';
import type { ChatSource, ChatSourceV2 } from '@/types/chat';

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

function sourceKey(source: ChatSource, index: number): string {
  if (isChatSourceV2(source)) return source.sourceId;
  return `legacy:${source.archivo}:${index}`;
}

function fidelityLabel(fidelity: ChatSourceV2['fidelity']): string {
  if (fidelity === 'exact') return 'Cita literal exacta';
  return 'Cita literal exacta con elipsis';
}

function pageLabel(source: ChatSourceV2): string {
  const physical = `Página PDF ${source.pageIndex}`;
  if (!source.printedPage || source.printedPage === String(source.pageIndex)) return physical;
  return `${physical} · Página impresa ${source.printedPage}`;
}

function reviewLabel(source: ChatSourceV2): string {
  const technical = {
    GENERATED: 'Dato generado',
    VALIDATED: 'Validación técnica',
    NEEDS_REVIEW: 'Revisión técnica pendiente',
    REJECTED: 'Validación técnica rechazada',
  }[source.reviewStatus.technical];
  const legal = {
    UNREVIEWED: 'Pendiente de revisión jurídica',
    AGENT_REVIEWED: 'Revisión jurídica por agente',
    HUMAN_APPROVED: 'Revisión jurídica humana aprobada',
    REJECTED: 'Revisión jurídica rechazada',
  }[source.reviewStatus.legal];
  return `${technical} · ${legal}`;
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
        {sources.map((source, index) => {
          const itemId = sourceKey(source, index);
          const isExpanded = expandedId === itemId;
          return (
            <li key={itemId}>
              <button
                type='button'
                onClick={() => setExpandedId(isExpanded ? null : itemId)}
                aria-expanded={isExpanded}
                className='flex w-full items-center gap-2 rounded-lg border border-border bg-background px-2.5 py-2 text-left text-xs transition-colors hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-ring'
              >
                <FileText className='h-3.5 w-3.5 shrink-0 text-primary' aria-hidden='true' />
                <span className='font-semibold text-foreground'>{source.roj}</span>
                <span className='truncate text-muted-foreground'>
                  {shortOrgano(source.organo)} · {year(source.fecha)}
                </span>
                <span className='ml-auto shrink-0 rounded bg-muted px-1.5 py-0.5 text-[0.6875rem] text-secondary-foreground'>
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
                <div className='mt-1 rounded-lg bg-muted px-3 py-2 text-xs leading-relaxed text-secondary-foreground'>
                  {isChatSourceV2(source) ? (
                    <>
                      <p className='font-semibold text-foreground'>{source.issueLabel}</p>
                      <p className='mt-1 text-muted-foreground'>
                        {pageLabel(source)} · {fidelityLabel(source.fidelity)}
                      </p>
                      <blockquote className='mt-2 border-l-2 border-primary/40 pl-2'>
                        {source.extracto}
                      </blockquote>
                      <p className='mt-2 text-muted-foreground'>{reviewLabel(source)}</p>
                      <p className='mt-1.5 break-all font-mono text-[0.6875rem]'>{source.ecli}</p>
                      <p className='mt-1 break-all font-mono text-[0.6875rem]'>
                        PDF SHA-256: {source.sourceSha256}
                      </p>
                    </>
                  ) : (
                    <>
                      <p className='font-semibold text-foreground'>
                        Fuente histórica sin anclaje v2
                      </p>
                      <p className='mt-1'>{source.extracto}</p>
                      <p className='mt-1 text-muted-foreground'>
                        Resumen conservado del motor simulado; no es una cita judicial verificada.
                      </p>
                      <p className='mt-1.5 font-mono text-[0.6875rem]'>{source.ecli}</p>
                    </>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
