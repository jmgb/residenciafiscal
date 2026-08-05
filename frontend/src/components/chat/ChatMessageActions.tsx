import { BookOpen, Check, Copy, Download } from 'lucide-react';
import { useState } from 'react';
import type { ChatSource } from '@/types/chat';

interface ChatMessageActionsProps {
  content: string;
  messageId?: string;
  sources: ChatSource[];
}

const iconButtonClassName =
  'inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-ring';

function sourcesDownloadText(content: string, sources: ChatSource[]): string {
  const sourceText = sources
    .map((source) =>
      [
        `${source.roj} · ${source.fecha}`,
        source.organo,
        `ECLI: ${source.ecli}`,
        `Archivo: ${source.archivo}`,
        `Extracto: ${source.extracto}`,
      ].join('\n')
    )
    .join('\n\n');

  return [`Respuesta`, content, '', 'Fuentes', sourceText].join('\n');
}

async function copyToClipboard(content: string): Promise<void> {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(content);
    return;
  }

  const textarea = document.createElement('textarea');
  textarea.value = content;
  textarea.setAttribute('readonly', '');
  textarea.style.position = 'fixed';
  textarea.style.opacity = '0';
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand('copy');
  textarea.remove();
}

function downloadSources(content: string, sources: ChatSource[]): void {
  const blob = new Blob([sourcesDownloadText(content, sources)], {
    type: 'text/plain;charset=utf-8',
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'fuentes-residencia-fiscal.txt';
  link.click();
  URL.revokeObjectURL(url);
}

export function ChatMessageActions({ content, messageId, sources }: ChatMessageActionsProps) {
  const [copied, setCopied] = useState(false);
  const sourcesId = `chat-sources-${messageId ?? 'respuesta'}`;

  const handleCopy = async () => {
    await copyToClipboard(content);
    setCopied(true);
  };

  return (
    <div className='mt-2 flex items-center gap-1 text-muted-foreground'>
      <button
        type='button'
        className={iconButtonClassName}
        onClick={() => void handleCopy()}
        aria-label={copied ? 'Respuesta copiada' : 'Copiar respuesta'}
        title={copied ? 'Respuesta copiada' : 'Copiar respuesta'}
      >
        {copied ? (
          <Check className='h-4 w-4' aria-hidden='true' />
        ) : (
          <Copy className='h-4 w-4' aria-hidden='true' />
        )}
      </button>
      {sources.length > 0 && (
        <>
          <button
            type='button'
            className={iconButtonClassName}
            onClick={() => downloadSources(content, sources)}
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
    </div>
  );
}
