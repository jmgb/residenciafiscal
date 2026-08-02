import { Link } from 'react-router';
import { jurisdictionName } from '@/data/jurisdictions';
import { fichaPath } from '@/lib/normativa-fichas';
import type { PreceptoEntry } from '@/types/normativa';
import type { SentenciaPublica } from '@/types/sentencias';

const CENDOJ_SEARCH = 'https://www.poderjudicial.es/search/';

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
        {judgment.roj} · {judgment.ecli} · {judgment.pageCount} páginas.{' '}
        <a
          className='text-primary underline-offset-4 hover:underline'
          href={CENDOJ_SEARCH}
          rel='noreferrer noopener'
          target='_blank'
        >
          Buscador del CENDOJ
        </a>
      </p>
      <p className='mt-1 break-all text-muted-foreground text-xs'>
        SHA-256 del PDF: {judgment.sourceSha256}
      </p>
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
