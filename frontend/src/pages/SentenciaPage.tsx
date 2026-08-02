import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router';
import { CuestionSection } from '@/components/sentencias/CuestionSection';
import { JsonLd } from '@/components/seo/JsonLd';
import { jurisdictionName, jurisdictionPath } from '@/data/jurisdictions';
import { loadNormativa } from '@/lib/normativa';
import { fichaPath } from '@/lib/normativa-fichas';
import { usePreceptoPreloadAll } from '@/lib/precepto-preload';
import {
  entryDeSentencia,
  esBorrador,
  revisionLabel,
  SENTENCIAS_INDEX_PATH,
  sentenciaDescription,
  sentenciaHeading,
  sentenciaPath,
  sentenciaTitle,
} from '@/lib/sentencia-metadata';
import { useSentenciaPreload } from '@/lib/sentencia-preload';
import { loadSentencia } from '@/lib/sentencias';
import { breadcrumbJsonLd } from '@/lib/structured-data';
import { usePageTitle } from '@/lib/usePageTitle';
import type { PreceptoEntry } from '@/types/normativa';
import type { AnclajeLiteral, SentenciaPublica } from '@/types/sentencias';

const CENDOJ_BUSCADOR = 'https://www.poderjudicial.es/search/';

type Estado =
  | { fase: 'cargando' }
  | { fase: 'no-encontrada' }
  | { fase: 'lista'; sentencia: SentenciaPublica };

function paginaLabel(fragmento: { pageIndex: number; printedPage: string | null }): string {
  const fisica = `Página PDF ${fragmento.pageIndex}`;
  if (!fragmento.printedPage || fragmento.printedPage === String(fragmento.pageIndex))
    return fisica;
  return `${fisica} · Página impresa ${fragmento.printedPage}`;
}

/**
 * Extractos literales de la sentencia. Es lo único de la página que reproduce
 * texto judicial, y por eso va con su página física, su etiqueta impresa y el
 * hash del PDF del que sale. No se recorta, une ni reformatea: si hay que
 * abreviarlo para la UI, se abrevia con CSS.
 */
function Anclajes({ anchors }: { anchors: AnclajeLiteral[] }) {
  if (anchors.length === 0) return null;
  return (
    <section aria-labelledby='anclajes' className='mt-8 border-border border-t pt-6'>
      <h2 id='anclajes' className='mb-1.5 font-heading font-semibold text-lg'>
        Extractos literales de la sentencia
      </h2>
      <p className='mb-4 text-muted-foreground text-xs leading-relaxed'>
        Texto copiado del PDF publicado por el CENDOJ y verificado carácter a carácter contra él.
        Todo lo demás de esta página es análisis estructurado, no palabras del tribunal.
      </p>
      <ul className='space-y-4'>
        {anchors.map((anclaje) => (
          <li key={anclaje.anchorId}>
            {anclaje.fragments.map((fragmento) => (
              <figure key={`${anclaje.anchorId}:${fragmento.pageIndex}`}>
                <blockquote className='border-border border-l-2 pl-3 text-sm leading-relaxed italic'>
                  {fragmento.verbatimText}
                </blockquote>
                <figcaption className='mt-1 text-muted-foreground text-xs'>
                  {paginaLabel(fragmento)}
                </figcaption>
              </figure>
            ))}
          </li>
        ))}
      </ul>
    </section>
  );
}

/**
 * Ficha pública de una sentencia del corpus.
 *
 * Se renderiza desde la proyección con allowlist, nunca desde el caso canónico,
 * y declara siempre su procedencia automática y su estado real de revisión: el
 * proyecto no afirma que su análisis esté revisado por especialistas mientras no
 * lo esté.
 *
 * Emite `BreadcrumbList` y nada más. No hay `Article`, `Review` ni `FAQPage`: no
 * existe un tipo de schema.org con soporte de Google para resoluciones
 * judiciales, y `Legislation` es de las fichas que publican texto legal.
 */
export function SentenciaPage() {
  const { judgmentId = '' } = useParams();
  const preload = useSentenciaPreload(judgmentId);
  const [estado, setEstado] = useState<Estado>(() =>
    preload ? { fase: 'lista', sentencia: preload } : { fase: 'cargando' }
  );

  // Al navegar entre fichas la SPA reutiliza el componente y el primer render
  // llega con la sentencia anterior: nada puede componerse desde otra.
  const sentencia =
    estado.fase === 'lista' && estado.sentencia.judgment.judgmentId === judgmentId
      ? estado.sentencia
      : null;
  const entry = sentencia ? entryDeSentencia(sentencia) : null;

  usePageTitle(
    entry ? sentenciaTitle(entry) : undefined,
    judgmentId ? sentenciaPath(judgmentId) : SENTENCIAS_INDEX_PATH,
    entry ? sentenciaDescription(entry) : undefined,
    // Un borrador interno nunca es indexable, ni siquiera si alguien comparte
    // su URL de preview.
    Boolean(entry) && !esBorrador(entry ?? { publicationState: 'internal_preview' }),
    true
  );

  // Ficha del convenio de cada jurisdicción enlazada. El slug **no** se
  // construye: el BOE no lo hace uniforme —el artículo 4 es `a4` en Francia,
  // `ar-4` en el Reino Unido de 2013, y hay `ai-4` y `a1-5`— así que fabricarlo
  // produciría enlaces rotos. Se resuelve por `boeId` contra el índice.
  //
  // La precarga es la que hace que el enlace exista en el HTML prerenderizado:
  // en el build no corren los efectos, y sin ella el bot solo vería la ficha sin
  // sus enlaces al convenio hasta que el navegador ejecutara JavaScript.
  const precargados = usePreceptoPreloadAll();
  const [cargados, setCargados] = useState<PreceptoEntry[]>([]);
  const preceptos = cargados.length > 0 ? cargados : precargados.map((item) => item.entry);

  useEffect(() => {
    let vigente = true;
    loadNormativa().then((entradas) => {
      if (vigente) setCargados(entradas);
    });
    return () => {
      vigente = false;
    };
  }, []);

  useEffect(() => {
    if (!judgmentId || preload) return;
    let vigente = true;
    setEstado({ fase: 'cargando' });
    loadSentencia(judgmentId).then((cargada) => {
      if (!vigente) return;
      setEstado(cargada ? { fase: 'lista', sentencia: cargada } : { fase: 'no-encontrada' });
    });
    return () => {
      vigente = false;
    };
  }, [judgmentId, preload]);

  if (!sentencia || !entry) {
    return (
      <div className='mx-auto w-full max-w-3xl px-4 py-8'>
        <p className='text-muted-foreground text-sm leading-relaxed'>
          {estado.fase === 'no-encontrada'
            ? 'Esa sentencia no está publicada en el corpus.'
            : 'Cargando la sentencia…'}
        </p>
        <Link
          className='mt-4 inline-block text-primary text-sm underline-offset-4 hover:underline'
          to={SENTENCIAS_INDEX_PATH}
        >
          Ver todas las sentencias
        </Link>
      </div>
    );
  }

  const { judgment } = sentencia;

  return (
    <div className='mx-auto w-full max-w-3xl overflow-y-auto px-4 py-8'>
      <JsonLd
        data={breadcrumbJsonLd([
          { name: 'España', path: '/espana' },
          { name: 'Sentencias', path: SENTENCIAS_INDEX_PATH },
          { name: judgment.roj, path: sentenciaPath(judgment.judgmentId) },
        ])}
      />

      <h1 className='mb-2 font-heading font-semibold text-2xl'>{sentenciaHeading(entry)}</h1>

      <dl className='mb-4 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm'>
        <dt className='text-muted-foreground'>Órgano</dt>
        <dd>
          {judgment.court}
          {judgment.chamber && `, ${judgment.chamber}`}
        </dd>
        <dt className='text-muted-foreground'>Fecha</dt>
        <dd>{judgment.decisionDate}</dd>
        <dt className='text-muted-foreground'>ECLI</dt>
        <dd>{judgment.ecli}</dd>
        {judgment.taxYears.length > 0 && (
          <>
            <dt className='text-muted-foreground'>Ejercicios</dt>
            <dd>{judgment.taxYears.join(', ')}</dd>
          </>
        )}
        {sentencia.jurisdictions.length > 0 && (
          <>
            <dt className='text-muted-foreground'>Jurisdicciones</dt>
            <dd>
              {sentencia.jurisdictions.map((jurisdiccion, indice) => (
                <span key={jurisdiccion.code}>
                  {indice > 0 && ', '}
                  <Link
                    className='text-primary underline-offset-4 hover:underline'
                    to={jurisdictionPath(jurisdiccion.code)}
                  >
                    {jurisdictionName(jurisdiccion.code)}
                  </Link>
                </span>
              ))}
            </dd>
          </>
        )}
      </dl>

      {/* §6.3: la procedencia y el estado de revisión son visibles y salen del
          manifiesto, no de copy escrito a mano. */}
      <p className='mb-6 rounded border border-border bg-muted/40 px-3 py-2 text-muted-foreground text-xs leading-relaxed'>
        {revisionLabel(judgment.review.legal)}. Generado por {judgment.provenance.producer} (
        {judgment.provenance.modelId}) a partir del texto de la sentencia.{' '}
        {esBorrador(entry) && 'Borrador interno: esta ficha no está publicada.'}
      </p>

      {sentencia.issues.map((cuestion) => (
        <CuestionSection key={cuestion.issueId} cuestion={cuestion} />
      ))}

      <Anclajes anchors={sentencia.anchors} />

      <section aria-labelledby='fuente' className='mt-8 border-border border-t pt-6'>
        <h2 id='fuente' className='mb-2 font-heading font-semibold text-lg'>
          Fuente
        </h2>
        <p className='text-sm leading-relaxed'>
          {judgment.roj} · {judgment.ecli} · {judgment.pageCount} páginas.{' '}
          <a
            className='text-primary underline-offset-4 hover:underline'
            href={CENDOJ_BUSCADOR}
            rel='noreferrer noopener'
            target='_blank'
          >
            Buscador del CENDOJ
          </a>
        </p>
        <p className='mt-1 break-all text-muted-foreground text-xs'>
          SHA-256 del PDF: {judgment.sourceSha256}
        </p>
        {sentencia.jurisdictions.flatMap((jurisdiccion) =>
          jurisdiccion.treatyBoeIds.map((boeId) => {
            const ficha = preceptos.find((precepto) => precepto.boeId === boeId);
            if (!ficha) return null;
            return (
              <p className='mt-2 text-sm' key={`${jurisdiccion.code}:${boeId}`}>
                <Link
                  className='text-primary underline-offset-4 hover:underline'
                  to={fichaPath(ficha)}
                >
                  Convenio de doble imposición España–{jurisdictionName(jurisdiccion.code)}
                  {ficha.derogada && ' (el aplicable al ejercicio, hoy derogado)'}:{' '}
                  {ficha.designacion}
                </Link>
              </p>
            );
          })
        )}
      </section>

      <Link
        className='mt-8 inline-block text-primary text-sm underline-offset-4 hover:underline'
        to={SENTENCIAS_INDEX_PATH}
      >
        Ver todas las sentencias sobre residencia fiscal
      </Link>
    </div>
  );
}
