import type { SentenciaPublica, SentenciasIndex, SentenciasManifest } from '@/types/sentencias';

/**
 * Carga la proyección pública de sentencias generada en el prebuild.
 *
 * Dos niveles, como en normativa: el índice para el listado y una ficha por
 * sentencia bajo demanda. La ficha completa de un caso pasa de 40 KB y nadie
 * necesita las 67 para leer una.
 *
 * La validación es igual de desconfiada que en `normativa.ts` y por el mismo
 * motivo: si el fichero no existe en el despliegue, Netlify puede servir otra
 * cosa con `res.ok === true`. Aquí importa el doble, porque lo que se publicaría
 * sin comprobar es análisis jurídico atribuido a una sentencia real.
 *
 * **Un fallo degrada a índice vacío, nunca a una ficha a medias.**
 */
const INDEX_URL = '/data/sentencias.json';
const FICHA_URL = (jurisdiction: string, judgmentId: string) =>
  `/data/sentencias/${jurisdiction}/${judgmentId}.json`;

const PUBLICATION_STATES = new Set(['internal_preview', 'publishable', 'published']);

let manifestCache: Promise<SentenciasManifest> | null = null;
const fichaCache = new Map<string, Promise<SentenciaPublica | null>>();
let failed = false;

function emptyIndex(jurisdiction: string): SentenciasIndex {
  return {
    jurisdiction,
    candidates: 0,
    includesPreview: false,
    judgments: [],
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.length > 0;
}

function isIndex(value: unknown, jurisdiction: string): value is SentenciasIndex {
  if (!isRecord(value)) return false;
  if (value.jurisdiction !== jurisdiction) return false;
  if (!Array.isArray(value.judgments)) return false;
  return value.judgments.every(
    (entry) =>
      isRecord(entry) &&
      isNonEmptyString(entry.judgmentId) &&
      isNonEmptyString(entry.roj) &&
      isNonEmptyString(entry.decisionDate) &&
      typeof entry.publicationState === 'string' &&
      PUBLICATION_STATES.has(entry.publicationState)
  );
}

function isManifest(value: unknown): value is SentenciasManifest {
  if (!isRecord(value) || value.schemaVersion !== 'residenciafiscal-sentencias-index/2')
    return false;
  if (!isRecord(value.jurisdictions)) return false;
  return Object.entries(value.jurisdictions).every(([code, index]) => isIndex(index, code));
}

function isFicha(value: unknown): value is SentenciaPublica {
  if (!isRecord(value)) return false;
  const judgment = value.judgment;
  return (
    isRecord(judgment) &&
    isNonEmptyString(judgment.judgmentId) &&
    isNonEmptyString(judgment.roj) &&
    isNonEmptyString(judgment.sourceSha256) &&
    typeof value.publicationState === 'string' &&
    PUBLICATION_STATES.has(value.publicationState) &&
    Array.isArray(value.issues) &&
    Array.isArray(value.anchors)
  );
}

async function fetchJson(url: string): Promise<unknown> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`respuesta HTTP ${res.status} al pedir ${url}`);
  return res.json();
}

export function loadSentenciasIndex(jurisdiction: string): Promise<SentenciasIndex> {
  if (!manifestCache) {
    const pending: Promise<SentenciasManifest> = fetchJson(INDEX_URL)
      .then((data) => {
        if (!isManifest(data)) {
          throw new Error(
            `${INDEX_URL} no tiene la forma del índice de sentencias; lo más probable es que el ` +
              'fichero no exista en el despliegue y el catch-all haya servido otra cosa'
          );
        }
        failed = false;
        return data;
      })
      .catch((error: unknown) => {
        failed = true;
        // Sin cachear el fallo: un error de red transitorio no puede dejar la
        // sesión entera sin el listado.
        if (manifestCache === pending) manifestCache = null;
        console.error('[sentencias] No se pudo cargar el índice de sentencias.', error);
        return { schemaVersion: 'residenciafiscal-sentencias-index/2', jurisdictions: {} };
      });
    manifestCache = pending;
  }
  return manifestCache.then(
    (manifest) => manifest.jurisdictions[jurisdiction] ?? emptyIndex(jurisdiction)
  );
}

/**
 * Ficha completa de una sentencia. `null` si no se puede cargar o si el fichero
 * habla de otra: publicar el análisis de una sentencia bajo el ROJ de otra sería
 * peor que no publicar nada.
 */
export function loadSentencia(
  jurisdiction: string,
  judgmentId: string
): Promise<SentenciaPublica | null> {
  const cacheKey = `${jurisdiction}:${judgmentId}`;
  const cached = fichaCache.get(cacheKey);
  if (cached) return cached;

  const pending: Promise<SentenciaPublica | null> = fetchJson(FICHA_URL(jurisdiction, judgmentId))
    .then((data) => {
      if (!isFicha(data)) {
        throw new Error(
          `${FICHA_URL(jurisdiction, judgmentId)} no tiene la forma de una sentencia pública`
        );
      }
      if (data.jurisdiction !== jurisdiction || data.judgment.judgmentId !== judgmentId) {
        throw new Error(
          `${FICHA_URL(jurisdiction, judgmentId)} declara otra jurisdicción o sentencia`
        );
      }
      return data;
    })
    .catch((error: unknown) => {
      if (fichaCache.get(cacheKey) === pending) fichaCache.delete(cacheKey);
      console.error(
        `[sentencias] No se pudo cargar la sentencia ${jurisdiction}/${judgmentId}.`,
        error
      );
      return null;
    });
  fichaCache.set(cacheKey, pending);
  return pending;
}

/** `true` si el último intento de cargar el índice falló. */
export function sentenciasLoadFailed(): boolean {
  return failed;
}

/** Solo para tests: invalida las cachés entre casos. */
export function resetSentenciasCache(): void {
  manifestCache = null;
  fichaCache.clear();
  failed = false;
}
