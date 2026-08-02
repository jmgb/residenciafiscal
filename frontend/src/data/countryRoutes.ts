import { z } from 'zod';
import { normalizeRoutePath } from '@/lib/route-path';
import countryRouteData from './countryRoutes.json';
import { currentTreatyBoeId, jurisdictionName } from './jurisdictions';

const legalReferenceSchema = z.object({
  kind: z.enum(['domestic-residence', 'tax-treaty']),
  shortCitation: z.string().min(1),
  title: z.string().min(1),
  officialUrl: z.url(),
  reviewedAt: z.iso.date(),
});

/**
 * Configuración de producto y SEO de cada página de país.
 *
 * **No contiene identidad de la jurisdicción.** El nombre y el convenio vigente
 * salían de aquí y del catálogo compartido a la vez, y dos copias editables del
 * mismo hecho divergen: la página de un país podía decir «Méjico» mientras la
 * ficha de su convenio decía «México». Ahora se componen desde
 * `jurisdictions.ts`, y este fichero solo decide lo que es editorial.
 */
const countryRouteSchema = z.object({
  /**
   * Código ISO 3166-1 alfa-2 en minúscula: la misma clave que usan
   * `normativa/<code>/` y el campo `jurisdiccion` del corpus. La ruta es un
   * slug legible (`/espana`) y no sirve para cruzar la web con los datos; sin
   * este campo, cada consumidor tendría que reconstruir la correspondencia.
   */
  code: z.string().regex(/^[a-z]{2}$/),
  path: z.string().startsWith('/'),
  corpusStatus: z.enum(['published', 'pending']),
  legalReferences: z.array(legalReferenceSchema),
  /** Título completo de la página, tal cual sale en la pestaña y en el buscador. */
  title: z.string().min(1),
  description: z.string().min(1),
  indexable: z.boolean(),
  sitemap: z.object({
    changefreq: z.enum(['weekly', 'monthly', 'yearly']),
    priority: z.string().regex(/^[01]\.\d$/),
  }),
});

export type CorpusStatus = z.infer<typeof countryRouteSchema>['corpusStatus'];
export type LegalReference = z.infer<typeof legalReferenceSchema>;
export type CountryRoute = z.infer<typeof countryRouteSchema> & {
  /** Nombre en español, del catálogo compartido. */
  name: string;
  /**
   * Convenio de doble imposición entre España y este país, por su identificador
   * del BOE. Es **norma española**, no el marco nacional de la jurisdicción: por
   * eso no vive en `legalReferences`, que describe el derecho del propio país y
   * exige validación de un especialista de allí. `null` significa que no hay
   * convenio en vigor según la relación oficial de la AEAT, no que no se haya
   * buscado. Sale del registro bilateral, que declara además desde qué
   * ejercicio rige.
   */
  treatyBoeId: string | null;
};

export const COUNTRY_ROUTES: CountryRoute[] = z
  .array(countryRouteSchema)
  .parse(countryRouteData)
  .map((route) => ({
    ...route,
    name: jurisdictionName(route.code),
    treatyBoeId: currentTreatyBoeId(route.code),
  }));

export const COUNTRY_ROUTE_REDIRECTS = COUNTRY_ROUTES.flatMap((route) => {
  const legacyPath = `/${route.name.toLowerCase().replace(/\s+/g, '-')}`;
  return legacyPath === route.path ? [] : [{ from: legacyPath, to: route.path }];
});

export const SPAIN_ROUTE = COUNTRY_ROUTES.find((route) => route.path === '/espana') as CountryRoute;

export function getCountryRoute(pathname: string): CountryRoute | undefined {
  const normalizedPath = normalizeRoutePath(pathname);
  return COUNTRY_ROUTES.find((route) => route.path === normalizedPath);
}

export function getJurisdictionRoute(pathname: string): CountryRoute | undefined {
  const normalizedPath = normalizeRoutePath(pathname);
  // Las subpáginas de un país (`/espana/fuentes`) pertenecen a su jurisdicción.
  const countryRoute = COUNTRY_ROUTES.find(
    (route) => route.path === normalizedPath || normalizedPath.startsWith(`${route.path}/`)
  );
  if (countryRoute) return countryRoute;

  if (normalizedPath === '/consulta' || normalizedPath.startsWith('/c/')) return SPAIN_ROUTE;

  return undefined;
}

export function getJurisdictionLabel(country: CountryRoute | undefined): string {
  if (!country) return 'Jurisprudencia por país';
  if (country.corpusStatus === 'pending') return `${country.name} · Sin corpus`;

  const [primaryReference] = country.legalReferences;
  if (!primaryReference) return `${country.name} · Corpus publicado`;

  return `${country.name} · ${primaryReference.shortCitation}`;
}
