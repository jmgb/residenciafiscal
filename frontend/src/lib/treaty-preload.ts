import { createContext, useContext } from 'react';
import type { PreceptoEntry, PreceptoTexto } from '@/types/normativa';

/** Convenio ya resuelto: la entrada del índice y su articulado literal. */
export interface TreatyPreload {
  entry: PreceptoEntry;
  texto: PreceptoTexto | null;
}

/** Convenios resueltos, indexados por identificador del BOE. */
export type TreatyPreloadMap = Record<string, TreatyPreload>;

/**
 * Convenios resueltos antes de que haya navegador.
 *
 * `TaxTreaty` los pide por `fetch` en un efecto, y los efectos no corren ni en
 * el renderizado del build ni en un cliente sin JavaScript: sin esto, el HTML
 * que sirve Netlify diría «Cargando el convenio…» y ni un buscador ni una
 * persona con JS desactivado verían el texto legal.
 *
 * En el build lo rellena `entry-server.tsx` leyendo el corpus del disco; en el
 * navegador, `main.tsx` lo lee del JSON embebido en la propia página. Vacío
 * —el valor por defecto— el componente vuelve a cargar por `fetch`, que es lo
 * que hacen los tests y cualquier montaje fuera de esos dos caminos.
 */
export const TreatyPreloadContext = createContext<TreatyPreloadMap>({});

/** El identificador del elemento `<script>` que transporta la precarga. */
export const TREATY_PRELOAD_ELEMENT_ID = 'treaty-preload';

export function useTreatyPreload(boeId: string | null): TreatyPreload | undefined {
  const preloaded = useContext(TreatyPreloadContext);
  return boeId ? preloaded[boeId] : undefined;
}

/**
 * Lee la precarga embebida en la página.
 *
 * Desconfiada a propósito, como el resto de cargas de corpus: un JSON roto o
 * ausente devuelve un mapa vacío y la página cae al `fetch` de siempre, en vez
 * de tumbar el arranque de la aplicación.
 */
export function readEmbeddedTreatyPreload(document: Document): TreatyPreloadMap {
  const element = document.getElementById(TREATY_PRELOAD_ELEMENT_ID);
  if (!element?.textContent) return {};
  try {
    const parsed: unknown = JSON.parse(element.textContent);
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) return {};
    return parsed as TreatyPreloadMap;
  } catch (error) {
    console.error('[treaty-preload] JSON embebido inválido; se cargará por red.', error);
    return {};
  }
}
