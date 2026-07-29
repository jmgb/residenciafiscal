import countryRouteData from './countryRoutes.json';

export interface CountryRoute {
  name: string;
  path: string;
  description: string;
  indexable: boolean;
}

export const COUNTRY_ROUTES = countryRouteData satisfies CountryRoute[];

export const SPAIN_ROUTE = COUNTRY_ROUTES.find((route) => route.path === '/españa') as CountryRoute;
