import type { CorpusEntry } from '@/types/chat';

/**
 * Carga el corpus ligero generado en build time. Se cachea en memoria: el
 * fichero es inmutable durante la vida de la página.
 *
 * Un fallo de red o un JSON corrupto degradan a corpus vacío en lugar de
 * romper la aplicación: el chat sigue respondiendo, solo que sin citas.
 */
let cache: Promise<CorpusEntry[]> | null = null;

export function loadCorpus(): Promise<CorpusEntry[]> {
  if (!cache) {
    cache = fetch('/data/corpus.json')
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => (Array.isArray(data) ? (data as CorpusEntry[]) : []))
      .catch(() => []);
  }
  return cache;
}

/** Solo para tests: invalida la caché entre casos. */
export function resetCorpusCache(): void {
  cache = null;
}
