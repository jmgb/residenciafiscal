import type { PreceptoEntry, PreceptoTexto } from '@/types/normativa';

/**
 * Carga el corpus normativo generado en build time por `build-normativa.mjs`.
 *
 * Dos niveles a propósito:
 *
 * - `loadNormativa()` trae el índice de los 110 preceptos (~99 KB): metadatos y
 *   qué sentencias citan cada uno.
 * - `loadPrecepto(slug)` trae el articulado literal de uno solo. Los 108 juntos
 *   son ~600 KB y nadie necesita los 95 convenios para leer el artículo 9 LIRPF.
 *
 * La validación es igual de desconfiada que en `corpus.ts`, y por el mismo
 * motivo: el `/* -> /index.html` con status 200 de `netlify.toml` hace que un
 * fichero ausente devuelva el HTML de la SPA con `res.ok === true`. Sin
 * comprobar la forma del JSON, el sitio mostraría cero preceptos en producción
 * sin que nadie se enterara.
 *
 * Un fallo degrada a vacío —el chat sigue respondiendo, solo sin normativa— pero
 * nunca en silencio: se registra en consola y `normativaLoadFailed()` deja que
 * la UI lo avise.
 */
const NORMATIVA_URL = '/data/normativa.json';
const PRECEPTO_URL = (slug: string) => `/data/preceptos/${slug}.json`;

const GRUPOS = new Set(['nucleo', 'nucleo_derogado', 'cdi', 'cdi_derogado']);

let indexCache: Promise<PreceptoEntry[]> | null = null;
const textCache = new Map<string, Promise<PreceptoTexto | null>>();
let failed = false;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.length > 0;
}

function isPreceptoEntry(value: unknown): value is PreceptoEntry {
  if (!isRecord(value)) return false;
  return (
    isNonEmptyString(value.slug) &&
    isNonEmptyString(value.jurisdiccion) &&
    isNonEmptyString(value.titulo) &&
    isNonEmptyString(value.designacion) &&
    isNonEmptyString(value.boeId) &&
    typeof value.grupo === 'string' &&
    GRUPOS.has(value.grupo) &&
    typeof value.derogada === 'boolean' &&
    typeof value.parrafos === 'number' &&
    value.parrafos > 0 &&
    typeof value.totalSentencias === 'number' &&
    Array.isArray(value.sentencias)
  );
}

function isPreceptoTexto(value: unknown): value is PreceptoTexto {
  if (!isRecord(value)) return false;
  return (
    isNonEmptyString(value.slug) &&
    isNonEmptyString(value.titulo) &&
    typeof value.derogada === 'boolean' &&
    Array.isArray(value.articulado) &&
    value.articulado.length > 0 &&
    value.articulado.every(isNonEmptyString)
  );
}

async function fetchJson(url: string): Promise<unknown> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`respuesta HTTP ${res.status} al pedir ${url}`);
  }
  return res.json();
}

async function fetchIndex(): Promise<PreceptoEntry[]> {
  const data = await fetchJson(NORMATIVA_URL);
  if (!Array.isArray(data)) {
    throw new Error(
      `${NORMATIVA_URL} no devolvió un array (recibido: ${data === null ? 'null' : typeof data}); ` +
        'lo más probable es que el fichero no exista en el despliegue y el catch-all haya ' +
        'servido index.html'
    );
  }

  const invalidIndex = data.findIndex((entry) => !isPreceptoEntry(entry));
  if (invalidIndex >= 0) {
    throw new Error(`entrada inválida en ${NORMATIVA_URL} (índice ${invalidIndex})`);
  }

  const slugs = new Set<string>();
  for (const entry of data) {
    if (slugs.has(entry.slug)) {
      throw new Error(`precepto duplicado en ${NORMATIVA_URL}: ${entry.slug}`);
    }
    slugs.add(entry.slug);
  }

  return data;
}

export function loadNormativa(): Promise<PreceptoEntry[]> {
  if (!indexCache) {
    const pending: Promise<PreceptoEntry[]> = fetchIndex().then(
      (entries) => {
        failed = false;
        return entries;
      },
      (error: unknown) => {
        failed = true;
        // Sin caché del fallo: un error de red transitorio no puede dejar toda
        // la sesión sin normativa.
        if (indexCache === pending) indexCache = null;
        console.error(
          '[normativa] No se pudo cargar el corpus normativo; las respuestas irán sin el texto de la ley.',
          error
        );
        return [];
      }
    );
    indexCache = pending;
  }
  return indexCache;
}

/**
 * Articulado literal de un precepto. `null` si no se puede cargar: quien lo pida
 * debe poder seguir sin él, nunca mostrar texto legal a medias.
 */
export function loadPrecepto(slug: string): Promise<PreceptoTexto | null> {
  const cached = textCache.get(slug);
  if (cached) return cached;

  // `.catch` encadenado y no el segundo argumento de `.then`: ese solo atrapa el
  // fallo del fetch, no el de la validación, y una validación fallida escaparía
  // como promesa rechazada en vez de degradar a `null`.
  const pending: Promise<PreceptoTexto | null> = fetchJson(PRECEPTO_URL(slug))
    .then((data) => {
      if (!isPreceptoTexto(data)) {
        throw new Error(`${PRECEPTO_URL(slug)} no tiene la forma de un precepto`);
      }
      if (data.slug !== slug) {
        throw new Error(`${PRECEPTO_URL(slug)} declara el slug ${data.slug}`);
      }
      return data;
    })
    .catch((error: unknown) => {
      if (textCache.get(slug) === pending) textCache.delete(slug);
      console.error(`[normativa] No se pudo cargar el precepto ${slug}.`, error);
      return null;
    });
  textCache.set(slug, pending);
  return pending;
}

/** `true` si el último intento de cargar el índice falló. */
export function normativaLoadFailed(): boolean {
  return failed;
}

/** Preceptos que cita al menos una sentencia, de más citado a menos. */
export function preceptosCitados(preceptos: PreceptoEntry[]): PreceptoEntry[] {
  return preceptos
    .filter((precepto) => precepto.totalSentencias > 0)
    .sort((a, b) => b.totalSentencias - a.totalSentencias || a.slug.localeCompare(b.slug));
}

/** Sentencias que citan un precepto, sin repetir archivo. */
export function sentenciasDe(precepto: PreceptoEntry): string[] {
  return [...new Set(precepto.sentencias.map((cita) => cita.archivo))].sort();
}

/** Solo para tests: invalida las cachés entre casos. */
export function resetNormativaCache(): void {
  indexCache = null;
  textCache.clear();
  failed = false;
}
