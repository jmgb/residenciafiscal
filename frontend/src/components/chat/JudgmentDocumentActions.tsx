import { Download, ExternalLink, FileText } from 'lucide-react';
import { trackEvent } from '@/components/layout/PostHogAnalytics';
import { getJudgmentDocument } from '@/lib/judgment-documents';

interface JudgmentDocumentActionsProps {
  judgmentId: string;
  ecli?: string;
}

const actionClassName =
  'inline-flex items-center gap-1.5 rounded-sm text-[0.6875rem] font-medium text-primary underline-offset-4 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-ring';

export function JudgmentDocumentActions({ judgmentId, ecli }: JudgmentDocumentActionsProps) {
  const document = getJudgmentDocument(judgmentId);
  if (!document) return null;

  const reference = ecli?.startsWith('ECLI:') ? ecli : document.ecli;
  const officialUrl = `https://e-justice.europa.eu/ecli/${reference}`;
  const trackAction = (event: string) => {
    trackEvent(event, {
      judgment_id: document.judgmentId,
      roj: document.roj,
      ecli: reference,
    });
  };

  return (
    <>
      <p className='mt-1.5 text-[0.6875rem] text-muted-foreground'>Referencia: {reference}</p>
      <div className='mt-2.5 flex flex-wrap gap-x-4 gap-y-2 border-t border-border/70 pt-2.5'>
        <a
          className={actionClassName}
          href={document.pdfUrl}
          target='_blank'
          rel='noreferrer noopener'
          aria-label={`Abrir sentencia ${document.roj}`}
          onClick={() => trackAction('sentencia_pdf_abierta')}
        >
          <FileText className='h-3.5 w-3.5' aria-hidden='true' />
          Abrir sentencia
        </a>
        <a
          className={actionClassName}
          href={document.pdfUrl}
          download={document.downloadName}
          aria-label={`Descargar PDF ${document.roj}`}
          onClick={() => trackAction('sentencia_pdf_descargada')}
        >
          <Download className='h-3.5 w-3.5' aria-hidden='true' />
          Descargar PDF
        </a>
        <a
          className={actionClassName}
          href={officialUrl}
          target='_blank'
          rel='noreferrer noopener'
          aria-label={`Fuente oficial ${document.roj}`}
          onClick={() => trackAction('sentencia_fuente_oficial_abierta')}
        >
          <ExternalLink className='h-3.5 w-3.5' aria-hidden='true' />
          Fuente oficial
        </a>
      </div>
    </>
  );
}
