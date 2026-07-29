import { describe, expect, it } from 'vitest';
import { COUNTRY_ROUTE_REDIRECTS, COUNTRY_ROUTES } from '@/data/countryRoutes';

describe('country routes', () => {
  it('declara metadata SEO personalizada para cada ruta', () => {
    expect(COUNTRY_ROUTES).toHaveLength(21);
    expect(COUNTRY_ROUTES.find((route) => route.path === '/espana')).toMatchObject({
      name: 'España',
      indexable: true,
      description: expect.stringContaining('106 sentencias'),
    });
    expect(COUNTRY_ROUTES.find((route) => route.path === '/mexico')).toMatchObject({
      name: 'México',
      indexable: false,
      description: expect.stringContaining('México'),
    });
  });

  it('declara redirecciones ASCII para los nombres de países con tildes', () => {
    expect(COUNTRY_ROUTE_REDIRECTS).toEqual(
      expect.arrayContaining([
        { from: '/españa', to: '/espana' },
        { from: '/haití', to: '/haiti' },
        { from: '/méxico', to: '/mexico' },
        { from: '/panamá', to: '/panama' },
        { from: '/perú', to: '/peru' },
        { from: '/república-dominicana', to: '/republica-dominicana' },
      ])
    );
  });
});
