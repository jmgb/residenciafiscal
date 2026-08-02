import { jurisdictionSectionPath } from '../src/data/jurisdictions.ts';

/**
 * Inventario único de rutas de sentencias materializadas en un despliegue.
 *
 * El generador de datos decide qué jurisdicciones y fichas existen. Sitemap,
 * redirects y prerender consumen después esta misma lista, para que una nueva
 * jurisdicción no pueda aparecer en uno de los tres artefactos y faltar en los
 * otros dos.
 */
export function sentenciaRouteInventory(manifest, { publishedOnly = false } = {}) {
  const indexes = Object.values(manifest?.jurisdictions ?? {});
  return indexes.flatMap((index) => {
    const judgments = publishedOnly
      ? index.judgments.filter((entry) => entry.publicationState === 'published')
      : index.judgments;
    if (judgments.length === 0) return [];

    const indexPath = jurisdictionSectionPath(index.jurisdiction, 'sentencias');
    return [
      {
        kind: 'index',
        jurisdiction: index.jurisdiction,
        path: indexPath,
        index,
      },
      ...judgments.map((entry) => ({
        kind: 'judgment',
        jurisdiction: index.jurisdiction,
        path: `${indexPath}/${entry.judgmentId}`,
        index,
        entry,
      })),
    ];
  });
}
