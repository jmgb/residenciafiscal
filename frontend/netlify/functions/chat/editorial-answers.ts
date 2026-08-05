import catalogue from '../../../src/data/editorialChatAnswers.json';
import type { StrategySource } from './contracts';

/**
 * Catálogo editorial visto por el servidor. El navegador manda solo el `id` del
 * turno y aquí se materializa el texto: el ledger no puede aceptar como respuesta
 * mostrada un contenido que el cliente podría haber alterado.
 */
interface EditorialCatalogueEntry {
  id: string;
  question: string;
  version: string;
  content: string;
  sources: {
    judgmentId: string;
    page: number;
    sourceSha256: string;
    quote: string;
  }[];
}

const ENTRIES = catalogue as EditorialCatalogueEntry[];

export interface EditorialTurn {
  question: string;
  content: string;
  model: string;
  sources: StrategySource[];
}

/**
 * Las citas editoriales ya están verificadas contra el PDF cuando entran en el
 * catálogo, así que se registran con la misma forma que las de una estrategia.
 * `strategy` las marca como editoriales, no como recuperadas por A.
 */
export const editorialTurn = (answerId: unknown): EditorialTurn | null => {
  if (typeof answerId !== 'string') return null;
  const entry = ENTRIES.find((candidate) => candidate.id === answerId);
  if (!entry) return null;
  return {
    question: entry.question,
    content: entry.content,
    model: `editorial-${entry.version}`,
    sources: entry.sources.map((source) => ({
      strategy: 'editorial' as const,
      judgment_id: source.judgmentId,
      page: source.page,
      source_sha256: source.sourceSha256,
      quote: source.quote,
      verification: 'EXACT' as const,
    })),
  };
};
