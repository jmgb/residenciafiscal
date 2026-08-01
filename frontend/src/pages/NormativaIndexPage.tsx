import { useEffect, useState } from 'react';
import { Link } from 'react-router';
import { JsonLd } from '@/components/seo/JsonLd';
import { staticRoute } from '@/data/staticRoutes';
import { loadNormativa, normativaLoadFailed } from '@/lib/normativa';
import {
  fichaHeading,
  fichaPath,
  NORMATIVA_INDEX_PATH,
  paisDelConvenio,
} from '@/lib/normativa-fichas';
import { usePreceptoPreloadAll } from '@/lib/precepto-preload';
import { breadcrumbJsonLd } from '@/lib/structured-data';
import { usePageTitle } from '@/lib/usePageTitle';
import type { PreceptoEntry } from '@/types/normativa';

const META = staticRoute(NORMATIVA_INDEX_PATH);

const BREADCRUMB = breadcrumbJsonLd([
  { name: 'España', path: '/espana' },
  { name: 'Normativa', path: NORMATIVA_INDEX_PATH },
]);

function DerogadaBadge() {
  return (
    <span className='ml-2 rounded bg-muted px-1.5 py-0.5 text-xs text-secondary-foreground'>
      derogada
    </span>
  );
}

function FichaLink({ entry }: { entry: PreceptoEntry }) {
  const pais = paisDelConvenio(entry);
  return (
    <li className='text-sm leading-relaxed'>
      <Link
        className='font-medium text-primary underline-offset-4 hover:underline'
        to={fichaPath(entry)}
      >
        {/* `fichaHeading` añade el año cuando un país tiene dos convenios
            (Japón, China, Argentina…): sin él, dos enlaces serían idénticos. */}
        {pais ? fichaHeading(entry) : entry.titulo}
      </Link>
      {pais && entry.epigrafe && (
        <span className='ml-2 text-muted-foreground'>{entry.epigrafe}</span>
      )}
      {entry.derogada && <DerogadaBadge />}
    </li>
  );
}

/**
 * Índice público del corpus normativo: los preceptos internos que deciden la
 * residencia fiscal en España y el artículo de residencia de cada convenio de
 * doble imposición, cada uno con su ficha propia.
 *
 * En el build llega la lista precargada (sin efectos no hay `fetch`); en el
 * navegador se pide el índice ligero de siempre.
 */
export function NormativaIndexPage() {
  usePageTitle(META.title, META.path, META.description, META.indexable, true);
  const preloaded = usePreceptoPreloadAll();
  const [cargados, setCargados] = useState<PreceptoEntry[] | null>(null);
  const [fallo, setFallo] = useState(false);

  useEffect(() => {
    let vigente = true;
    loadNormativa().then((entradas) => {
      if (!vigente) return;
      if (entradas.length > 0) setCargados(entradas);
      setFallo(normativaLoadFailed());
    });
    return () => {
      vigente = false;
    };
  }, []);

  // La precarga solo es el índice completo cuando la página servida fue el
  // propio índice; la de una ficha trae un único precepto, y presentarlo como
  // si fuera todo el corpus normativo sería mentir en silencio.
  const preloadedIndex = preloaded.length > 1 ? preloaded.map((precepto) => precepto.entry) : null;
  const entries = cargados ?? preloadedIndex ?? [];
  const internos = entries.filter((entry) => !entry.grupo.startsWith('cdi'));
  const convenios = entries
    .filter((entry) => entry.grupo.startsWith('cdi'))
    .sort((a, b) => (paisDelConvenio(a) ?? '').localeCompare(paisDelConvenio(b) ?? '', 'es'));

  return (
    <div className='mx-auto w-full max-w-3xl overflow-y-auto px-4 py-8'>
      <JsonLd data={BREADCRUMB} />
      <h1 className='mb-3 font-heading text-2xl font-semibold'>
        Normativa de la residencia fiscal en España
      </h1>
      <p className='mb-8 max-w-2xl text-sm leading-relaxed text-muted-foreground'>
        Los preceptos que deciden o prueban la residencia fiscal de una persona física en España,
        con su texto literal del BOE: la ley interna —el art. 9 LIRPF y su entorno— y el artículo de
        residencia de cada convenio de doble imposición. Cada ficha publica la redacción vigente y
        las sentencias del corpus que la aplican. Las normas derogadas se conservan rotuladas porque
        rigen ejercicios que el corpus enjuicia.
      </p>

      {entries.length === 0 ? (
        <p className='text-sm leading-relaxed text-muted-foreground'>
          {fallo ? 'No se ha podido cargar el corpus normativo.' : 'Cargando la normativa…'}
        </p>
      ) : (
        <>
          <section aria-labelledby='normativa-interna' className='mb-8'>
            <h2 id='normativa-interna' className='mb-3 font-heading text-lg font-semibold'>
              Ley interna española
            </h2>
            <ul className='space-y-2'>
              {internos.map((entry) => (
                <FichaLink key={entry.slug} entry={entry} />
              ))}
            </ul>
          </section>

          <section aria-labelledby='normativa-cdi'>
            <h2 id='normativa-cdi' className='mb-3 font-heading text-lg font-semibold'>
              Convenios de doble imposición: el artículo de residencia
            </h2>
            <ul className='space-y-2'>
              {convenios.map((entry) => (
                <FichaLink key={entry.slug} entry={entry} />
              ))}
            </ul>
          </section>
        </>
      )}
    </div>
  );
}
