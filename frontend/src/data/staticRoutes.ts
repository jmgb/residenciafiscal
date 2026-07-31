import staticRouteData from './staticRoutes.json';

/**
 * Metadatos SEO de las rutas públicas de contenido estático. Las rutas de chat
 * por país viven en `countryRoutes.json`; aquí entran las demás, incluidas las
 * subpáginas de contenido de un país como `/espana/fuentes`.
 *
 * Existe por el mismo motivo que `countryRoutes.json`: la descripción de una
 * ruta la necesitan tres consumidores —la página, que la fija en runtime;
 * `scripts/prerender.mjs`, que escribe la que leen los bots; y
 * `scripts/build-sitemap.mjs`—, y escribirla en cada uno hacía que el visitante
 * y Google pudieran ver descripciones distintas sin que nada avisara.
 */
export interface StaticRoute {
  path: string;
  title: string;
  description: string;
  /** `false` sacaría la ruta del sitemap y la marcaría `noindex`. */
  indexable: boolean;
  /** Ruta pública de su imagen OG; `null` hereda la de la home. */
  image: string | null;
  sitemap: { changefreq: string; priority: string };
}

export const STATIC_ROUTES = staticRouteData satisfies StaticRoute[];

/** Lanza si la ruta no está registrada: un typo no debe degradar en silencio. */
export function staticRoute(path: string): StaticRoute {
  const route = STATIC_ROUTES.find((candidate) => candidate.path === path);
  if (!route) throw new Error(`ruta estática no registrada: ${path}`);
  return route;
}
