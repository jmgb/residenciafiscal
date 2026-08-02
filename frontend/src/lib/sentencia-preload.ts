import { createContext, useContext } from 'react';
import type { SentenciaPublica, SentenciasIndex } from '@/types/sentencias';

/**
 * Sentencias resueltas antes de que haya navegador.
 *
 * Mismo mecanismo y mismos motivos que `precepto-preload.ts`: en el build no
 * corren los efectos, así que sin esto el HTML prerenderizado de una ficha diría
 * «Cargando la sentencia…», que es justo lo que el prerender existe para evitar.
 *
 * En el build lo rellena `scripts/prerender.mjs`; en el navegador, `main.tsx` lo
 * lee del JSON embebido. Vacío, las páginas cargan por `fetch` como siempre.
 */
export interface SentenciaPreload {
  index: SentenciasIndex | null;
  fichas: Record<string, SentenciaPublica>;
}

export const SentenciaPreloadContext = createContext<SentenciaPreload>({
  index: null,
  fichas: {},
});

/** El identificador del elemento `<script>` que transporta la precarga. */
export const SENTENCIA_PRELOAD_ELEMENT_ID = 'sentencia-preload';

export function useSentenciaPreload(judgmentId: string | null): SentenciaPublica | undefined {
  const { fichas } = useContext(SentenciaPreloadContext);
  return judgmentId ? fichas[judgmentId] : undefined;
}

export function useSentenciasIndexPreload(): SentenciasIndex | null {
  return useContext(SentenciaPreloadContext).index;
}

/**
 * Lee la precarga embebida. Desconfiada como las demás: un JSON roto o ausente
 * degrada al `fetch` de siempre, nunca tumba el arranque.
 */
export function readEmbeddedSentenciaPreload(document: Document): SentenciaPreload {
  const vacio: SentenciaPreload = { index: null, fichas: {} };
  const element = document.getElementById(SENTENCIA_PRELOAD_ELEMENT_ID);
  if (!element?.textContent) return vacio;
  try {
    const parsed: unknown = JSON.parse(element.textContent);
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) return vacio;
    const candidato = parsed as Partial<SentenciaPreload>;
    return {
      index: candidato.index ?? null,
      fichas: candidato.fichas ?? {},
    };
  } catch (error) {
    console.error('[sentencia-preload] JSON embebido inválido; se cargará por red.', error);
    return vacio;
  }
}
