import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router';
import { JsonLd } from '@/components/seo/JsonLd';
import { COUNTRY_ROUTES } from '@/data/countryRoutes';
import { loadNormativa, loadPrecepto, sentenciasDe } from '@/lib/normativa';
import {
  fichaDescription,
  fichaHeading,
  fichaPath,
  fichaPathForSlug,
  fichaTitle,
  NORMATIVA_INDEX_PATH,
  paisDelConvenio,
} from '@/lib/normativa-fichas';
import { usePreceptoPreload } from '@/lib/precepto-preload';
import { breadcrumbJsonLd, treatyJsonLd } from '@/lib/structured-data';
import { usePageTitle } from '@/lib/usePageTitle';
import type { PreceptoEntry, PreceptoTexto } from '@/types/normativa';

/**
 * Mismo patrón de fases que `TaxTreaty`, y por el mismo motivo: «cargando» y
 * «no existe» son estados distintos y solo el segundo puede decirle al lector
 * que el precepto que busca no está en el corpus.
 */
type EstadoFicha =
  | { fase: 'cargando' }
  | { fase: 'no-encontrado' }
  | { fase: 'listo'; entry: PreceptoEntry };

/**
 * Ficha pública de un precepto del corpus normativo: el texto literal del BOE
 * con su vigencia, sus redacciones y las sentencias del corpus que lo citan.
 *
 * Es la única página del artículo con URL propia —el mismo texto que ya
 * publican las páginas de país dentro de su ficha de convenio— y existe para
 * que «artículo 9 LIRPF» o «convenio doble imposición España-Francia texto»
 * tengan una respuesta indexable. El articulado no se reescribe ni se recorta:
 * si falta, la ficha se queda con su enlace al BOE.
 */
export function PreceptoPage() {
  const { slug = '' } = useParams();
  const preload = usePreceptoPreload(slug);
  const [estado, setEstado] = useState<EstadoFicha>(() =>
    preload ? { fase: 'listo', entry: preload.entry } : { fase: 'cargando' }
  );
  const [texto, setTexto] = useState<PreceptoTexto | null>(preload?.texto ?? null);

  // Igual que en TaxTreaty: al navegar entre fichas la SPA reutiliza el
  // componente, y el primer render de la ruta nueva llega con el estado de la
  // anterior. Nada de esta página puede componerse desde un precepto que no
  // sea el del slug actual.
  const entry = estado.fase === 'listo' && estado.entry.slug === slug ? estado.entry : null;
  const articulado = texto?.slug === slug ? texto : null;
  const noEncontrado = estado.fase === 'no-encontrado';

  usePageTitle(
    entry ? fichaTitle(entry) : undefined,
    slug ? fichaPathForSlug(slug) : NORMATIVA_INDEX_PATH,
    entry ? fichaDescription(entry) : undefined,
    Boolean(entry),
    true
  );

  useEffect(() => {
    if (!slug) return;
    if (preload) {
      setEstado({ fase: 'listo', entry: preload.entry });
      setTexto(preload.texto);
      // Solo la precarga de la propia ficha trae el articulado. La del índice
      // es parcial —sin texto y sin citas de sentencias— y quedarse con ella
      // publicaría la ficha sin el artículo para siempre: se completa por red,
      // sin volver a «cargando» porque la cabecera ya está en pantalla.
      if (preload.texto) return;
    }
    let vigente = true;
    if (!preload) {
      setEstado({ fase: 'cargando' });
      setTexto(null);
    }
    loadNormativa().then((entradas) => {
      if (!vigente) return;
      const encontrado = entradas.find((precepto) => precepto.slug === slug);
      if (!encontrado) {
        // Con precarga parcial el precepto existe seguro: un fallo de red del
        // índice no puede degradar la ficha a «no encontrado».
        if (!preload) setEstado({ fase: 'no-encontrado' });
        return;
      }
      setEstado({ fase: 'listo', entry: encontrado });
      loadPrecepto(slug).then((cargado) => {
        if (vigente) setTexto(cargado);
      });
    });
    return () => {
      vigente = false;
    };
  }, [slug, preload]);

  const paisRoute = entry
    ? COUNTRY_ROUTES.find((route) => route.treatyBoeId === entry.boeId)
    : undefined;

  return (
    <div className='mx-auto w-full max-w-3xl overflow-y-auto px-4 py-8'>
      <nav aria-label='Miga de pan' className='mb-4 text-xs text-muted-foreground'>
        <Link className='underline underline-offset-4' to='/espana'>
          España
        </Link>
        {' · '}
        <Link className='underline underline-offset-4' to={NORMATIVA_INDEX_PATH}>
          Normativa
        </Link>
      </nav>

      {estado.fase === 'cargando' && (
        <p className='text-sm leading-relaxed text-muted-foreground'>Cargando el precepto…</p>
      )}

      {noEncontrado && (
        <>
          <h1 className='mb-3 font-heading text-2xl font-semibold'>Precepto no encontrado</h1>
          <p className='text-sm leading-relaxed text-muted-foreground'>
            Esta dirección no corresponde a ningún precepto del corpus normativo. El índice completo
            está en{' '}
            <Link className='underline underline-offset-4' to={NORMATIVA_INDEX_PATH}>
              la normativa de residencia fiscal en España
            </Link>
            .
          </p>
        </>
      )}

      {entry && (
        <>
          <JsonLd
            data={breadcrumbJsonLd([
              { name: 'España', path: '/espana' },
              { name: 'Normativa', path: NORMATIVA_INDEX_PATH },
              { name: entry.titulo, path: fichaPath(entry) },
            ])}
          />
          <JsonLd data={treatyJsonLd(entry)} />

          <h1 className='mb-1 font-heading text-2xl font-semibold'>{fichaHeading(entry)}</h1>
          {entry.epigrafe && (
            <p className='mb-4 text-base text-secondary-foreground'>{entry.epigrafe}</p>
          )}

          {entry.derogada && (
            <p className='mb-4 max-w-2xl rounded-lg border border-accent-500/40 bg-accent px-3 py-2 text-sm leading-relaxed text-accent-foreground'>
              <strong className='font-semibold'>Norma derogada.</strong> No es derecho vigente: se
              conserva porque rige ejercicios que las sentencias del corpus enjuician.
              {entry.notaDerogacion ? ` ${entry.notaDerogacion}.` : ''}
            </p>
          )}

          <p className='mb-4 max-w-2xl text-sm leading-relaxed text-secondary-foreground'>
            {entry.norma}
          </p>

          <dl className='mb-5 grid gap-2 text-sm sm:grid-cols-2'>
            <div>
              <dt className='inline font-semibold'>Identificador del BOE: </dt>
              <dd className='inline font-mono text-xs text-secondary-foreground'>{entry.boeId}</dd>
            </div>
            {entry.vigenteDesde && (
              <div>
                <dt className='inline font-semibold'>Redacción vigente desde: </dt>
                <dd className='inline text-secondary-foreground'>{entry.vigenteDesde}</dd>
              </div>
            )}
            {entry.redacciones > 1 && (
              <div>
                <dt className='inline font-semibold'>Redacciones conservadas: </dt>
                <dd className='inline text-secondary-foreground'>{entry.redacciones}</dd>
              </div>
            )}
            {entry.totalSentencias > 0 && (
              <div>
                <dt className='inline font-semibold'>En el corpus español: </dt>
                <dd className='inline text-secondary-foreground'>
                  {entry.totalSentencias === 1
                    ? 'lo aplica 1 sentencia'
                    : `lo aplican ${entry.totalSentencias} sentencias`}{' '}
                  (
                  {sentenciasDe(entry)
                    .map((archivo) => archivo.replace(/\.pdf$/i, '').replace(/_/g, ' '))
                    .join(', ')}
                  )
                </dd>
              </div>
            )}
          </dl>

          {entry.urlBoe && (
            <p className='mb-6'>
              <a
                className='control-focus control-press inline-flex items-center justify-center rounded-md border border-border px-4 py-2.5 text-sm font-medium transition-colors hover:bg-secondary'
                href={entry.urlBoe}
                rel='noreferrer'
                target='_blank'
              >
                Texto oficial en el BOE
              </a>
            </p>
          )}

          {articulado && (
            <div className='rounded-lg border border-border bg-muted p-5'>
              <h2 className='mb-3 font-heading text-sm font-semibold'>
                {entry.designacion}, literal
              </h2>
              <div className='space-y-3 text-sm leading-relaxed text-secondary-foreground'>
                {articulado.articulado.map((parrafo) => (
                  <p key={parrafo}>{parrafo}</p>
                ))}
              </div>
              <p className='mt-4 text-xs leading-relaxed text-muted-foreground'>
                Reproducción literal del texto del BOE. La única versión con valor jurídico es la
                edición oficial.
              </p>
            </div>
          )}

          {/*
           * Las redacciones anteriores NO se publican aquí a propósito:
           * `build-normativa.mjs` las aplana en una sola secuencia sin la fecha
           * de vigencia de cada una, y mostrar redacciones sucesivas sin saber
           * cuál regía cada ejercicio contradice el contrato del corpus. Si el
           * pipeline conserva algún día los límites y fechas por versión, esta
           * ficha es el sitio donde publicarlas.
           */}
          {entry.redacciones > 1 && (
            <p className='mt-4 max-w-2xl text-xs leading-relaxed text-muted-foreground'>
              El corpus conserva {entry.redacciones} redacciones de este precepto; las anteriores
              pueden consultarse con su fecha en la versión consolidada del BOE.
            </p>
          )}

          {paisRoute && (
            <p className='mt-6 text-sm leading-relaxed'>
              <Link className='text-primary underline underline-offset-4' to={paisRoute.path}>
                Residencia fiscal en {paisRoute.name}: la página del país
              </Link>
            </p>
          )}

          {paisDelConvenio(entry) && (
            <p className='mt-4 max-w-2xl text-xs leading-relaxed text-muted-foreground'>
              El convenio es norma española y solo resuelve de qué Estado es residente quien podría
              serlo de los dos; no describe la ley interna del otro país.
            </p>
          )}
        </>
      )}
    </div>
  );
}
