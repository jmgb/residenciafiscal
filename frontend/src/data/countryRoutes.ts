export interface CountryRoute {
  name: string;
  path: string;
}

export const COUNTRY_ROUTES: CountryRoute[] = [
  { name: 'España', path: '/españa' },
  { name: 'Argentina', path: '/argentina' },
  { name: 'Bolivia', path: '/bolivia' },
  { name: 'Brasil', path: '/brasil' },
  { name: 'Chile', path: '/chile' },
  { name: 'Colombia', path: '/colombia' },
  { name: 'Costa Rica', path: '/costa-rica' },
  { name: 'Cuba', path: '/cuba' },
  { name: 'Ecuador', path: '/ecuador' },
  { name: 'El Salvador', path: '/el-salvador' },
  { name: 'Guatemala', path: '/guatemala' },
  { name: 'Haití', path: '/haiti' },
  { name: 'Honduras', path: '/honduras' },
  { name: 'México', path: '/mexico' },
  { name: 'Nicaragua', path: '/nicaragua' },
  { name: 'Panamá', path: '/panama' },
  { name: 'Paraguay', path: '/paraguay' },
  { name: 'Perú', path: '/peru' },
  { name: 'República Dominicana', path: '/republica-dominicana' },
  { name: 'Uruguay', path: '/uruguay' },
  { name: 'Venezuela', path: '/venezuela' },
];

export const SPAIN_ROUTE = COUNTRY_ROUTES[0];
