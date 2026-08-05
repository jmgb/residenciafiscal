import { BookOpen, Check, Copy, Download } from 'lucide-react';
import { useState } from 'react';
import { isChatSourceV2 } from '@/lib/chat-source';
import type { ChatSource, ChatSourceV2 } from '@/types/chat';

export interface VerifiedChatActionSource {
  label: string;
  ecli?: string;
  page: number;
  sourceSha256: string;
  quote: string;
  verification: 'EXACT';
}

interface ChatMessageActionsProps {
  content: string;
  sources?: ChatSource[];
  verifiedSources?: VerifiedChatActionSource[];
  sourcesId?: string;
}

const iconButtonClassName =
  'inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-ring';

const technicalReviewLabel: Record<ChatSourceV2['reviewStatus']['technical'], string> = {
  GENERATED: 'Dato generado',
  VALIDATED: 'Validación técnica',
  NEEDS_REVIEW: 'Revisión técnica pendiente',
  REJECTED: 'Validación técnica rechazada',
};

const legalReviewLabel: Record<ChatSourceV2['reviewStatus']['legal'], string> = {
  UNREVIEWED: 'Pendiente de revisión jurídica',
  AGENT_REVIEWED: 'Revisión jurídica por agente',
  HUMAN_APPROVED: 'Revisión jurídica humana aprobada',
  REJECTED: 'Revisión jurídica rechazada',
};

function rawSourceDownloadText(source: ChatSource): string {
  const common = [
    `${source.roj} · ${source.fecha}`,
    source.organo,
    `ECLI: ${source.ecli}`,
    `Archivo: ${source.archivo}`,
  ];

  if (!isChatSourceV2(source)) {
    return [
      ...common,
      'Fuente histórica sin anclaje v2',
      `Resumen no verificado: ${source.extracto}`,
      'Este resumen no es una cita judicial verificada.',
    ].join('\n');
  }

  return [
    ...common,
    `Cuestión: ${source.issueLabel}`,
    `Página PDF: ${source.pageIndex}`,
    ...(source.printedPage ? [`Página impresa: ${source.printedPage}`] : []),
    source.fidelity === 'exact' ? 'Cita literal exacta' : 'Cita literal exacta con elipsis',
    `Cita: ${source.extracto}`,
    `SHA-256: ${source.sourceSha256}`,
    `${technicalReviewLabel[source.reviewStatus.technical]} · ${
      legalReviewLabel[source.reviewStatus.legal]
    }`,
  ].join('\n');
}

function verifiedSourceDownloadText(source: VerifiedChatActionSource): string {
  return [
    source.label,
    ...(source.ecli ? [`ECLI: ${source.ecli}`] : []),
    `Página PDF: ${source.page}`,
    'Cita literal exacta',
    `Cita: ${source.quote}`,
    `SHA-256: ${source.sourceSha256}`,
    `Verificación: ${source.verification}`,
  ].join('\n');
}

function sourcesDownloadText(
  content: string,
  sources: ChatSource[],
  verifiedSources: VerifiedChatActionSource[]
): string {
  const sourceText = [
    ...sources.map(rawSourceDownloadText),
    ...verifiedSources.map(verifiedSourceDownloadText),
  ].join('\n\n');

  return ['Respuesta', content, '', 'Fuentes', sourceText].join('\n');
}

function copyWithTextarea(content: string): void {
  const textarea = document.createElement('textarea');
  textarea.value = content;
  textarea.setAttribute('readonly', '');
  textarea.style.position = 'fixed';
  textarea.style.opacity = '0';
  document.body.appendChild(textarea);
  textarea.select();

  try {
    if (typeof document.execCommand !== 'function' || !document.execCommand('copy')) {
      throw new Error('Clipboard fallback failed');
    }
  } finally {
    textarea.remove();
  }
}

async function copyToClipboard(content: string): Promise<void> {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(content);
      return;
    } catch {
      copyWithTextarea(content);
      return;
    }
  }

  copyWithTextarea(content);
}

function downloadSources(
  content: string,
  sources: ChatSource[],
  verifiedSources: VerifiedChatActionSource[]
): void {
  const blob = new Blob([sourcesDownloadText(content, sources, verifiedSources)], {
    type: 'text/plain;charset=utf-8',
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'fuentes-residencia-fiscal.txt';
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

export function ChatMessageActions({
  content,
  sources = [],
  verifiedSources = [],
  sourcesId = 'chat-sources-respuesta',
}: ChatMessageActionsProps) {
  const [copyStatus, setCopyStatus] = useState<'idle' | 'copied' | 'error'>('idle');
  const hasSources = sources.length > 0 || verifiedSources.length > 0;

  const handleCopy = async () => {
    try {
      await copyToClipboard(content);
      setCopyStatus('copied');
    } catch {
      setCopyStatus('error');
    }
  };

  const copyLabel = copyStatus === 'copied' ? 'Respuesta copiada' : 'Copiar respuesta';

  return (
    <div className='mt-2 flex flex-wrap items-center gap-1 text-muted-foreground'>
      <button
        type='button'
        className={iconButtonClassName}
        onClick={() => void handleCopy()}
        aria-label={copyLabel}
        title={copyLabel}
      >
        {copyStatus === 'copied' ? (
          <Check className='h-4 w-4' aria-hidden='true' />
        ) : (
          <Copy className='h-4 w-4' aria-hidden='true' />
        )}
      </button>
      {hasSources && (
        <>
          <button
            type='button'
            className={iconButtonClassName}
            onClick={() => downloadSources(content, sources, verifiedSources)}
            aria-label='Descargar fuentes'
            title='Descargar fuentes'
          >
            <Download className='h-4 w-4' aria-hidden='true' />
          </button>
          <a
            href={`#${sourcesId}`}
            className='inline-flex items-center gap-1.5 rounded-md px-2 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-ring'
            aria-label='Ver fuentes'
          >
            <BookOpen className='h-4 w-4' aria-hidden='true' />
            <span>Fuentes</span>
          </a>
        </>
      )}
      {copyStatus === 'error' && (
        <span role='status' className='ml-1 text-xs text-destructive'>
          No se pudo copiar la respuesta
        </span>
      )}
    </div>
  );
}
