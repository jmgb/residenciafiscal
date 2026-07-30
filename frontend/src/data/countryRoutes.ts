import { z } from 'zod';
import { normalizeRoutePath } from '@/lib/route-path';
import countryRouteData from './countryRoutes.json';

const legalReferenceSchema = z.object({
  kind: z.enum(['domestic-residence', 'tax-treaty']),
  shortCitation: z.string().min(1),
  title: z.string().min(1),
  officialUrl: z.url(),
});

const countryRouteSchema = z.object({
  name: z.string().min(1),
  path: z.string().startsWith('/'),
  corpusStatus: z.enum(['published', 'pending']),
  legalReferences: z.array(legalReferenceSchema),
  description: z.string().min(1),
  indexable: z.boolean(),
});

export type CorpusStatus = z.infer<typeof countryRouteSchema>['corpusStatus'];
export type LegalReference = z.infer<typeof legalReferenceSchema>;
export type CountryRoute = z.infer<typeof countryRouteSchema>;

export const COUNTRY_ROUTES = z.array(countryRouteSchema).parse(countryRouteData);

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
  const countryRoute = getCountryRoute(pathname);
  if (countryRoute) return countryRoute;

  const normalizedPath = normalizeRoutePath(pathname);
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
