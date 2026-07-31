import { describe, expect, it } from 'vitest';
import {
  COUNTRY_ROUTE_REDIRECTS,
  COUNTRY_ROUTES,
  getJurisdictionRoute,
  SPAIN_ROUTE,
} from '@/data/countryRoutes';

describe('country routes', () => {
  it('declara metadata SEO personalizada para cada ruta', () => {
    expect(COUNTRY_ROUTES).toHaveLength(29);
    expect(COUNTRY_ROUTES.slice(0, 9).map((route) => route.name)).toEqual([
      'España',
      'Estados Unidos',
      'Portugal',
      'Francia',
      'Reino Unido',
      'Alemania',
      'Suiza',
      'Andorra',
      'Italia',
    ]);
    expect(COUNTRY_ROUTES.find((route) => route.path === '/espana')).toMatchObject({
      name: 'España',
      corpusStatus: 'published',
      indexable: true,
      description: expect.stringContaining('106 sentencias'),
      legalReferences: [
        {
          kind: 'domestic-residence',
          shortCitation: 'Art. 9 LIRPF',
          officialUrl: expect.stringContaining('boe.es'),
          reviewedAt: '2026-07-30',
        },
      ],
    });
    expect(COUNTRY_ROUTES.find((route) => route.path === '/mexico')).toMatchObject({
      name: 'México',
      corpusStatus: 'pending',
      indexable: false,
      description: expect.stringContaining('México'),
      legalReferences: [],
    });
    expect(COUNTRY_ROUTES.find((route) => route.path === '/estados-unidos')).toMatchObject({
      name: 'Estados Unidos',
      indexable: false,
      description: expect.stringContaining('Estados Unidos'),
    });
  });

  it('separa la publicación del corpus de la indexación SEO', () => {
    for (const route of COUNTRY_ROUTES) {
      expect(route).toHaveProperty('corpusStatus');
      expect(route).toHaveProperty('indexable');
      expect(route).toHaveProperty('legalReferences');
      if (route.corpusStatus === 'published') {
        expect(route.legalReferences.length).toBeGreaterThan(0);
      }
      for (const reference of route.legalReferences) {
        expect(reference.reviewedAt).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      }
    }
  });

  it('resuelve las subpáginas de un país a su jurisdicción', () => {
    expect(getJurisdictionRoute('/espana/fuentes')).toBe(SPAIN_ROUTE);
    expect(getJurisdictionRoute('/espana')).toBe(SPAIN_ROUTE);
    expect(getJurisdictionRoute('/consulta')).toBe(SPAIN_ROUTE);
    expect(getJurisdictionRoute('/metodologia')).toBeUndefined();
    expect(getJurisdictionRoute('/colaborar')).toBeUndefined();
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
