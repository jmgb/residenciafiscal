import { createContext, useContext } from 'react';
import type { PreceptoEntry, PreceptoTexto } from '@/types/normativa';

/** Precepto ya resuelto: la entrada del índice y su articulado literal. */
export interface PreceptoPreload {
  entry: PreceptoEntry;
  texto: PreceptoTexto | null;
}

/** Preceptos resueltos, indexados por slug. */
export type PreceptoPreloadMap = Record<string, PreceptoPreload>;

/**
 * Preceptos resueltos antes de que haya navegador, para las fichas de
 * `/espana/normativa`. Mismo mecanismo y mismos motivos que
 * `treaty-preload.ts`, pero indexado por slug: varios preceptos comparten
 * `boeId` (los artículos 8, 9, 10 y 72 de la LIRPF son la misma norma) y una
 * clave por norma los pisaría entre sí.
 *
 * En el build lo rellena `scripts/prerender.mjs`; en el navegador, `main.tsx`
 * lo lee del JSON embebido en la página. Vacío, las páginas cargan por `fetch`.
 */
export const PreceptoPreloadContext = createContext<PreceptoPreloadMap>({});

/** El identificador del elemento `<script>` que transporta la precarga. */
export const PRECEPTO_PRELOAD_ELEMENT_ID = 'precepto-preload';

export function usePreceptoPreload(slug: string | null): PreceptoPreload | undefined {
  const preloaded = useContext(PreceptoPreloadContext);
  return slug ? preloaded[slug] : undefined;
}

/** Todos los preceptos precargados; el índice de normativa lista con esto. */
export function usePreceptoPreloadAll(): PreceptoPreload[] {
  return Object.values(useContext(PreceptoPreloadContext));
}

/**
 * Lee la precarga embebida en la página. Desconfiada como la del convenio: un
 * JSON roto o ausente degrada al `fetch` de siempre, nunca tumba el arranque.
 */
export function readEmbeddedPreceptoPreload(document: Document): PreceptoPreloadMap {
  const element = document.getElementById(PRECEPTO_PRELOAD_ELEMENT_ID);
  if (!element?.textContent) return {};
  try {
    const parsed: unknown = JSON.parse(element.textContent);
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) return {};
    return parsed as PreceptoPreloadMap;
  } catch (error) {
    console.error('[precepto-preload] JSON embebido inválido; se cargará por red.', error);
    return {};
  }
}
