import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router';
import { CuestionSection } from '@/components/sentencias/CuestionSection';
import { SentenciaAnchors } from '@/components/sentencias/SentenciaAnchors';
import { SentenciaSource } from '@/components/sentencias/SentenciaSource';
import { JsonLd } from '@/components/seo/JsonLd';
import { jurisdictionName, jurisdictionPath } from '@/data/jurisdictions';
import { loadNormativa } from '@/lib/normativa';
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
import type { SentenciaPublica } from '@/types/sentencias';

type Estado =
  | { fase: 'cargando' }
  | { fase: 'no-encontrada' }
  | { fase: 'lista'; sentencia: SentenciaPublica };

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
    if (!judgmentId) return;
    if (preload) {
      setEstado({ fase: 'lista', sentencia: preload });
      return;
    }
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

      <SentenciaAnchors anchors={sentencia.anchors} />
      <SentenciaSource sentencia={sentencia} preceptos={preceptos} />

      <Link
        className='mt-8 inline-block text-primary text-sm underline-offset-4 hover:underline'
        to={SENTENCIAS_INDEX_PATH}
      >
        Ver todas las sentencias sobre residencia fiscal
      </Link>
    </div>
  );
}
