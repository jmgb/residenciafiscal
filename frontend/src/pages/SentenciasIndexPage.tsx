import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router';
import { JsonLd } from '@/components/seo/JsonLd';
import {
  anio,
  criterioLabel,
  esBorrador,
  organoCorto,
  resultadoLabel,
  SENTENCIAS_INDEX_PATH,
  sentenciaPath,
} from '@/lib/sentencia-metadata';
import { useSentenciasIndexPreload } from '@/lib/sentencia-preload';
import { loadSentenciasIndex, sentenciasLoadFailed } from '@/lib/sentencias';
import { breadcrumbJsonLd } from '@/lib/structured-data';
import { usePageTitle } from '@/lib/usePageTitle';
import type { SentenciaIndexEntry, SentenciasIndex } from '@/types/sentencias';

const TITLE = 'Sentencias sobre residencia fiscal en España: fichas por sentencia';
const DESCRIPTION =
  'Fichas de las sentencias del Tribunal Supremo y la Audiencia Nacional sobre residencia ' +
  'fiscal: criterios aplicados, pruebas valoradas, resultado y extractos literales con su página.';

const BREADCRUMB = breadcrumbJsonLd([
  { name: 'España', path: '/espana' },
  { name: 'Sentencias', path: SENTENCIAS_INDEX_PATH },
]);

const TODOS = '';

function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span className='rounded bg-muted px-1.5 py-0.5 text-xs text-secondary-foreground'>
      {children}
    </span>
  );
}

function SentenciaRow({ entry }: { entry: SentenciaIndexEntry }) {
  return (
    <li className='border-border border-b py-3 last:border-b-0'>
      <Link
        className='font-medium text-primary underline-offset-4 hover:underline'
        to={sentenciaPath(entry.judgmentId)}
      >
        {entry.roj}
      </Link>
      <span className='ml-2 text-muted-foreground text-sm'>
        {organoCorto(entry.court)} · {anio(entry.decisionDate)}
        {entry.taxYears.length > 0 && ` · ejercicios ${entry.taxYears.join(', ')}`}
      </span>
      <div className='mt-1.5 flex flex-wrap gap-1.5'>
        {entry.outcomes.map((outcome) => (
          <Chip key={outcome}>{resultadoLabel(outcome)}</Chip>
        ))}
        {entry.criterionIds.map((criterio) => (
          <Chip key={criterio}>{criterioLabel(criterio)}</Chip>
        ))}
        {esBorrador(entry) && <Chip>borrador interno</Chip>}
      </div>
    </li>
  );
}

/**
 * Índice de las fichas de sentencia publicadas.
 *
 * **Los filtros no crean URL.** Se aplican en cliente y el canonical es siempre
 * la ruta base: una faceta indexable multiplicaría el inventario por
 * combinaciones sin contenido propio, que es exactamente lo que el proyecto
 * evita. Con 67 candidatas no hay paginación.
 *
 * Cuando ninguna sentencia ha superado la revisión humana, la página lo dice en
 * vez de aparentar un corpus vacío: el listado sin fichas es un estado
 * legítimo, no un error de carga.
 */
export function SentenciasIndexPage() {
  const preloaded = useSentenciasIndexPreload();
  const [index, setIndex] = useState<SentenciasIndex | null>(preloaded);
  const [fallo, setFallo] = useState(false);
  const [criterio, setCriterio] = useState(TODOS);
  const [resultado, setResultado] = useState(TODOS);
  const indexable =
    index !== null &&
    index.judgments.length > 0 &&
    index.judgments.every((entry) => entry.publicationState === 'published');
  usePageTitle(TITLE, SENTENCIAS_INDEX_PATH, DESCRIPTION, indexable, true);

  useEffect(() => {
    let vigente = true;
    loadSentenciasIndex().then((cargado) => {
      if (!vigente) return;
      setIndex(cargado);
      setFallo(sentenciasLoadFailed());
    });
    return () => {
      vigente = false;
    };
  }, []);

  const judgments = useMemo(() => index?.judgments ?? [], [index]);
  const criterios = useMemo(
    () => [...new Set(judgments.flatMap((entry) => entry.criterionIds))].sort(),
    [judgments]
  );
  const resultados = useMemo(
    () => [...new Set(judgments.flatMap((entry) => entry.outcomes))].sort(),
    [judgments]
  );
  const visibles = judgments
    .filter((entry) => !criterio || entry.criterionIds.includes(criterio))
    .filter((entry) => !resultado || entry.outcomes.includes(resultado))
    .sort((a, b) => b.decisionDate.localeCompare(a.decisionDate));

  return (
    <div className='mx-auto w-full max-w-3xl overflow-y-auto px-4 py-8'>
      <JsonLd data={BREADCRUMB} />
      <h1 className='mb-3 font-heading font-semibold text-2xl'>
        Sentencias sobre residencia fiscal
      </h1>
      <p className='mb-6 max-w-2xl text-muted-foreground text-sm leading-relaxed'>
        Una ficha por sentencia del corpus: la cuestión que resuelve, las pruebas que valoró el
        tribunal, el criterio del artículo 9 LIRPF que aplica y el resultado, con extractos
        literales verificados contra el PDF del CENDOJ y su página. El análisis lo genera un modelo
        y solo se publica cuando una persona lo aprueba.
      </p>

      {judgments.length > 0 && (
        <div className='mb-6 flex flex-wrap gap-3'>
          <label className='text-sm'>
            <span className='mr-2 text-muted-foreground'>Criterio</span>
            <select
              className='control-field control-focus w-auto'
              value={criterio}
              onChange={(event) => setCriterio(event.target.value)}
            >
              <option value={TODOS}>Todos</option>
              {criterios.map((valor) => (
                <option key={valor} value={valor}>
                  {criterioLabel(valor)}
                </option>
              ))}
            </select>
          </label>
          <label className='text-sm'>
            <span className='mr-2 text-muted-foreground'>Resultado</span>
            <select
              className='control-field control-focus w-auto'
              value={resultado}
              onChange={(event) => setResultado(event.target.value)}
            >
              <option value={TODOS}>Todos</option>
              {resultados.map((valor) => (
                <option key={valor} value={valor}>
                  {resultadoLabel(valor)}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}

      {judgments.length === 0 ? (
        <p className='text-muted-foreground text-sm leading-relaxed'>
          {fallo
            ? 'No se ha podido cargar el índice de sentencias.'
            : index === null
              ? 'Cargando las sentencias…'
              : `Todavía no hay ninguna ficha publicada. El corpus tiene ${index.candidates} sentencias sobre residencia fiscal analizadas, y cada una se publica cuando su análisis supera la revisión de una persona.`}
        </p>
      ) : (
        <>
          <p className='mb-2 text-muted-foreground text-xs'>
            {visibles.length} de {judgments.length} sentencias
          </p>
          <ul>
            {visibles.map((entry) => (
              <SentenciaRow key={entry.judgmentId} entry={entry} />
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
