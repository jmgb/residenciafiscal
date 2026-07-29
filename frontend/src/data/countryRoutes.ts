import { normalizeRoutePath } from '@/lib/route-path';
import countryRouteData from './countryRoutes.json';

export interface CountryRoute {
  name: string;
  path: string;
  description: string;
  indexable: boolean;
}

export const COUNTRY_ROUTES = countryRouteData satisfies CountryRoute[];

export const COUNTRY_ROUTE_REDIRECTS = COUNTRY_ROUTES.flatMap((route) => {
  const legacyPath = `/${route.name.toLowerCase().replace(/\s+/g, '-')}`;
  return legacyPath === route.path ? [] : [{ from: legacyPath, to: route.path }];
});

export const SPAIN_ROUTE = COUNTRY_ROUTES.find((route) => route.path === '/espana') as CountryRoute;

export function getCountryRoute(pathname: string): CountryRoute | undefined {
  const normalizedPath = normalizeRoutePath(pathname);
  return COUNTRY_ROUTES.find((route) => route.path === normalizedPath);
}
