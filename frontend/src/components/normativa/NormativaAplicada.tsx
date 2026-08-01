import { useEffect, useState } from 'react';
import { loadNormativa, normativaLoadFailed, preceptosCitados } from '@/lib/normativa';
import type { PreceptoEntry } from '@/types/normativa';

/**
 * Preceptos que las sentencias del corpus citan, de más citado a menos.
 *
 * Solo se listan los citados: los 110 preceptos completos incluyen 95 convenios
 * de doble imposición, y enumerarlos aquí sería ruido. El índice completo vive en
 * `knowledge/normativa/es/preceptos/index.md`.
 *
 * No se muestra articulado: el texto legal se sirve en su propio fichero y se
 * carga solo cuando alguien lo pide. Aquí basta con el enlace al BOE, que es la
 * fuente oficial.
 */
export function NormativaAplicada() {
  const [preceptos, setPreceptos] = useState<PreceptoEntry[] | null>(null);
  const [fallo, setFallo] = useState(false);

  useEffect(() => {
    let vigente = true;
    loadNormativa().then((entradas) => {
      if (!vigente) return;
      setPreceptos(preceptosCitados(entradas));
      setFallo(normativaLoadFailed());
    });
    return () => {
      vigente = false;
    };
  }, []);

  if (fallo) {
    return (
      <p className='text-sm leading-relaxed text-muted-foreground'>
        No se ha podido cargar el corpus normativo.
      </p>
    );
  }

  if (preceptos === null) {
    return <p className='text-sm leading-relaxed text-muted-foreground'>Cargando la normativa…</p>;
  }

  if (preceptos.length === 0) {
    return (
      <p className='text-sm leading-relaxed text-muted-foreground'>
        Ninguna sentencia del corpus cita todavía un precepto publicado.
      </p>
    );
  }

  return (
    <ul className='space-y-3'>
      {preceptos.map((precepto) => (
        <li key={precepto.slug} className='text-sm leading-relaxed'>
          <span className='font-medium'>{precepto.titulo}</span>
          {precepto.derogada && (
            // `text-secondary-foreground` y no `text-muted-foreground`: sobre un
            // fondo teñido el segundo no llega a AA (regla 1 del brandbook).
            <span className='ml-2 rounded bg-muted px-1.5 py-0.5 text-xs text-secondary-foreground'>
              derogada
            </span>
          )}
          <span className='block text-muted-foreground'>
            {precepto.totalSentencias === 1
              ? 'Citado por 1 sentencia'
              : `Citado por ${precepto.totalSentencias} sentencias`}
            {precepto.urlBoe && (
              <>
                {' · '}
                <a
                  className='underline underline-offset-2'
                  href={precepto.urlBoe}
                  rel='noreferrer'
                  target='_blank'
                >
                  Texto oficial en el BOE
                </a>
              </>
            )}
          </span>
        </li>
      ))}
    </ul>
  );
}
