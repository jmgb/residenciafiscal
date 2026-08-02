import { Link } from 'react-router';
import { JudgmentDocumentActions } from '@/components/chat/JudgmentDocumentActions';
import { jurisdictionName } from '@/data/jurisdictions';
import { fichaPath } from '@/lib/normativa-fichas';
import type { PreceptoEntry } from '@/types/normativa';
import type { SentenciaPublica } from '@/types/sentencias';

export function SentenciaSource({
  sentencia,
  preceptos,
}: {
  sentencia: SentenciaPublica;
  preceptos: PreceptoEntry[];
}) {
  const { judgment } = sentencia;
  return (
    <section aria-labelledby='fuente' className='mt-8 border-border border-t pt-6'>
      <h2 id='fuente' className='mb-2 font-heading font-semibold text-lg'>
        Fuente
      </h2>
      <p className='text-sm leading-relaxed'>
        {judgment.roj} · {judgment.pageCount} páginas.
      </p>
      <JudgmentDocumentActions judgmentId={judgment.judgmentId} ecli={judgment.ecli} />
      {sentencia.jurisdictions.flatMap((jurisdiction) =>
        jurisdiction.treatyBoeIds.map((boeId) => {
          const ficha = preceptos.find((precepto) => precepto.boeId === boeId);
          if (!ficha) return null;
          return (
            <p className='mt-2 text-sm' key={`${jurisdiction.code}:${boeId}`}>
              <Link
                className='text-primary underline-offset-4 hover:underline'
                to={fichaPath(ficha)}
              >
                Convenio de doble imposición España–{jurisdictionName(jurisdiction.code)}
                {ficha.derogada && ' (el aplicable al ejercicio, hoy derogado)'}:{' '}
                {ficha.designacion}
              </Link>
            </p>
          );
        })
      )}
    </section>
  );
}
