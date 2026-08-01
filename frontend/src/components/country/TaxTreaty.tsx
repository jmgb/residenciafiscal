import { useEffect, useState } from 'react';
import type { CountryRoute } from '@/data/countryRoutes';
import { loadNormativa, loadPrecepto, sentenciasDe } from '@/lib/normativa';
import type { PreceptoEntry, PreceptoTexto } from '@/types/normativa';

/** Relación oficial de convenios, que es lo que decide si un país tiene o no. */
const AEAT_CONVENIOS =
  'https://sede.agenciatributaria.gob.es/Sede/normativa-criterios-interpretativos/fiscalidad-internacional/convenios-doble-imposicion-firmados-espana.html';

/**
 * Fases explícitas y no un `entry` nullable: «cargando» y «no se ha podido
 * cargar» son estados distintos, y con uno solo la página se quedaba en
 * «Cargando el convenio…» para siempre cuando el índice normativo fallaba
 * —`loadNormativa()` degrada a lista vacía a propósito—.
 */
type EstadoConvenio =
  | { fase: 'cargando' }
  | { fase: 'fallo' }
  | { fase: 'listo'; entry: PreceptoEntry };

/**
 * Convenio de doble imposición entre España y el país de la página.
 *
 * Es lo único verificable que este proyecto puede publicar hoy de una
 * jurisdicción sin corpus: el convenio es **norma española** del BOE, ya
 * versionada en `normativa/es/`, y su artículo de residencia decide de qué
 * Estado es residente quien vive entre los dos países. No dice nada de la ley
 * interna del otro país, y la página no debe insinuar que sí.
 *
 * El articulado se pide aparte (`loadPrecepto`) porque es el texto legal
 * literal y pesa; el índice basta para la ficha. Si el articulado no llega, se
 * queda la ficha con su enlace al BOE: nunca un texto legal a medias.
 */
export function TaxTreaty({ country }: { country: CountryRoute }) {
  const [estado, setEstado] = useState<EstadoConvenio>({ fase: 'cargando' });
  const [texto, setTexto] = useState<PreceptoTexto | null>(null);
  const boeId = country.treatyBoeId;

  useEffect(() => {
    if (!boeId) return;
    let vigente = true;
    // Al navegar entre países la SPA reutiliza este componente: sin reiniciar,
    // `/chile` mostraría durante un instante el articulado de `/francia`. Un
    // texto legal bajo el nombre de otra jurisdicción es un error grave, no un
    // parpadeo.
    setEstado({ fase: 'cargando' });
    setTexto(null);
    loadNormativa().then((entradas) => {
      if (!vigente) return;
      const encontrado = entradas.find((precepto) => precepto.boeId === boeId);
      if (!encontrado) {
        setEstado({ fase: 'fallo' });
        return;
      }
      setEstado({ fase: 'listo', entry: encontrado });
      loadPrecepto(encontrado.slug).then((articulado) => {
        if (vigente) setTexto(articulado);
      });
    });
    return () => {
      vigente = false;
    };
  }, [boeId]);

  if (!boeId) {
    return (
      <section className='mt-12 border-t border-border pt-8' aria-labelledby='country-treaty'>
        <h2 id='country-treaty' className='mb-3 font-heading text-2xl font-semibold'>
          Convenio de doble imposición con España
        </h2>
        <p className='max-w-2xl text-sm leading-relaxed text-secondary-foreground'>
          España y {country.name} <strong className='font-semibold'>no tienen convenio</strong> de
          doble imposición en vigor: no figura en la{' '}
          <a
            className='underline underline-offset-4'
            href={AEAT_CONVENIOS}
            rel='noreferrer'
            target='_blank'
          >
            relación oficial de convenios firmados por España
          </a>
          . Sin convenio no hay reglas de desempate: cada país aplica su ley interna, y por el lado
          español eso significa el artículo 9 LIRPF y los criterios que interpretan los tribunales.
        </p>
      </section>
    );
  }

  return (
    <section className='mt-12 border-t border-border pt-8' aria-labelledby='country-treaty'>
      <h2 id='country-treaty' className='mb-3 font-heading text-2xl font-semibold'>
        Convenio de doble imposición España–{country.name}
      </h2>
      {estado.fase === 'cargando' && (
        <p className='text-sm leading-relaxed text-muted-foreground'>Cargando el convenio…</p>
      )}
      {estado.fase === 'fallo' && (
        <p className='max-w-2xl text-sm leading-relaxed text-muted-foreground'>
          No se ha podido cargar el convenio desde el corpus normativo. Su identificador en el BOE
          es <span className='font-mono text-xs'>{boeId}</span>.
        </p>
      )}
      {estado.fase === 'listo' && (
        <>
          <p className='mb-4 max-w-2xl text-sm leading-relaxed text-secondary-foreground'>
            {estado.entry.norma}
          </p>
          <dl className='mb-5 grid gap-2 text-sm sm:grid-cols-2'>
            <div>
              <dt className='inline font-semibold'>Artículo de residencia: </dt>
              <dd className='inline text-secondary-foreground'>
                {estado.entry.designacion}
                {estado.entry.epigrafe ? ` — ${estado.entry.epigrafe}` : ''}
              </dd>
            </div>
            <div>
              <dt className='inline font-semibold'>Identificador del BOE: </dt>
              <dd className='inline font-mono text-xs text-secondary-foreground'>
                {estado.entry.boeId}
              </dd>
            </div>
            {estado.entry.vigenteDesde && (
              <div>
                <dt className='inline font-semibold'>Redacción vigente desde: </dt>
                <dd className='inline text-secondary-foreground'>{estado.entry.vigenteDesde}</dd>
              </div>
            )}
            {estado.entry.totalSentencias > 0 && (
              <div>
                <dt className='inline font-semibold'>En el corpus español: </dt>
                <dd className='inline text-secondary-foreground'>
                  {estado.entry.totalSentencias === 1
                    ? 'lo aplica 1 sentencia'
                    : `lo aplican ${estado.entry.totalSentencias} sentencias`}{' '}
                  (
                  {sentenciasDe(estado.entry)
                    .map((archivo) => archivo.replace(/\.pdf$/i, '').replace(/_/g, ' '))
                    .join(', ')}
                  )
                </dd>
              </div>
            )}
          </dl>

          {estado.entry.urlBoe && (
            <p className='mb-6'>
              <a
                className='control-focus control-press inline-flex items-center justify-center rounded-md border border-border px-4 py-2.5 text-sm font-medium transition-colors hover:bg-secondary'
                href={estado.entry.urlBoe}
                rel='noreferrer'
                target='_blank'
              >
                Texto oficial del convenio en el BOE
              </a>
            </p>
          )}

          {texto && (
            <div className='rounded-lg border border-border bg-muted p-5'>
              <h3 className='mb-3 font-heading text-sm font-semibold'>
                {estado.entry.designacion} del convenio, literal
              </h3>
              <div className='space-y-3 text-sm leading-relaxed text-secondary-foreground'>
                {texto.articulado.map((parrafo) => (
                  <p key={parrafo}>{parrafo}</p>
                ))}
              </div>
              <p className='mt-4 text-xs leading-relaxed text-muted-foreground'>
                Reproducción literal del texto del BOE. La única versión con valor jurídico es la
                edición oficial.
              </p>
            </div>
          )}

          <p className='mt-4 max-w-2xl text-xs leading-relaxed text-muted-foreground'>
            El convenio es norma española y solo resuelve de qué Estado es residente quien podría
            serlo de los dos. No sustituye a la ley interna de {country.name}, que este proyecto
            todavía no cubre.
          </p>
        </>
      )}
    </section>
  );
}
