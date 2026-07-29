import type { CorpusEntry } from '@/types/chat';

/**
 * Carga el corpus ligero generado en build time. Se cachea en memoria: el
 * fichero es inmutable durante la vida de la página.
 *
 * Un fallo degrada a corpus vacío en lugar de romper la aplicación (el chat
 * sigue respondiendo, solo que sin citas), pero NO en silencio:
 *
 * - se registra en consola con la causa;
 * - `corpusLoadFailed()` deja que la UI avise de que faltan las citas;
 * - la caché se limpia para que la siguiente pregunta reintente.
 *
 * El caso peligroso que motiva todo esto: el `/* -> /index.html` con status 200
 * de `netlify.toml`. Si `corpus.json` no llegara a `dist/`, la petición
 * devolvería el HTML de la SPA con `res.ok === true`; sin validar la forma del
 * JSON el sitio respondería en producción sin una sola cita y nadie se
 * enteraría.
 */
const CORPUS_URL = '/data/corpus.json';
const VALID_RESULTS = new Set([
  'GANA_AEAT',
  'GANA_CONTRIBUYENTE',
  'PARCIAL',
  'RETROACCION',
  'INADMISION',
  'DESCONOCIDO',
]);

let cache: Promise<CorpusEntry[]> | null = null;
let failed = false;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isCorpusEntry(value: unknown): value is CorpusEntry {
  if (!isRecord(value)) return false;
  return (
    typeof value.archivo === 'string' &&
    value.archivo.length > 0 &&
    typeof value.roj === 'string' &&
    typeof value.ecli === 'string' &&
    (value.roj.length > 0 || value.ecli.length > 0) &&
    typeof value.organo === 'string' &&
    value.organo.length > 0 &&
    typeof value.fecha === 'string' &&
    typeof value.resultado === 'string' &&
    VALID_RESULTS.has(value.resultado) &&
    Array.isArray(value.criterioDecisivo) &&
    value.criterioDecisivo.every((criterio) => typeof criterio === 'string') &&
    typeof value.esCasoResidencia === 'boolean'
  );
}

async function fetchCorpus(): Promise<CorpusEntry[]> {
  const res = await fetch(CORPUS_URL);
  if (!res.ok) {
    throw new Error(`respuesta HTTP ${res.status} al pedir ${CORPUS_URL}`);
  }

  const data: unknown = await res.json();
  if (!Array.isArray(data)) {
    throw new Error(
      `${CORPUS_URL} no devolvió un array (recibido: ${data === null ? 'null' : typeof data}); ` +
        'lo más probable es que el fichero no exista en el despliegue y el catch-all haya ' +
        'servido index.html'
    );
  }

  const invalidIndex = data.findIndex((entry) => !isCorpusEntry(entry));
  if (invalidIndex >= 0) {
    throw new Error(`entrada inválida en ${CORPUS_URL} (índice ${invalidIndex})`);
  }

  const files = new Set<string>();
  for (const entry of data) {
    if (files.has(entry.archivo)) {
      throw new Error(`archivo duplicado en ${CORPUS_URL}: ${entry.archivo}`);
    }
    files.add(entry.archivo);
  }

  return data;
}

export function loadCorpus(): Promise<CorpusEntry[]> {
  if (!cache) {
    const pending: Promise<CorpusEntry[]> = fetchCorpus().then(
      (entries) => {
        failed = false;
        return entries;
      },
      (error: unknown) => {
        failed = true;
        // Sin caché del fallo: un error de red transitorio no puede dejar toda
        // la sesión sin citas.
        if (cache === pending) cache = null;
        console.error(
          '[corpus] No se pudo cargar el corpus; el chat responderá sin citar sentencias.',
          error
        );
        return [];
      }
    );
    cache = pending;
  }
  return cache;
}

/**
 * `true` si el último intento de carga falló. La UI lo consulta tras esperar a
 * `loadCorpus()` para avisar de que la respuesta va sin fuentes.
 */
export function corpusLoadFailed(): boolean {
  return failed;
}

/** Solo para tests: invalida la caché entre casos. */
export function resetCorpusCache(): void {
  cache = null;
  failed = false;
}
