import { describe, expect, it } from 'vitest';
import {
  COUNTRY_ROUTE_REDIRECTS,
  COUNTRY_ROUTES,
  getJurisdictionRoute,
  SPAIN_ROUTE,
} from '@/data/countryRoutes';

describe('country routes', () => {
  it('declara metadata SEO personalizada para cada ruta', () => {
    expect(COUNTRY_ROUTES).toHaveLength(34);
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
      indexable: true,
      title: expect.stringContaining('México'),
      description: expect.stringContaining('México'),
      treatyBoeId: 'BOE-A-1994-23743',
      legalReferences: [],
      sitemap: { changefreq: 'monthly', priority: '0.5' },
    });
    expect(COUNTRY_ROUTES.find((route) => route.path === '/estados-unidos')).toMatchObject({
      name: 'Estados Unidos',
      indexable: true,
      description: expect.stringContaining('Estados Unidos'),
      treatyBoeId: 'BOE-A-1990-30940',
    });
  });

  it('da a cada país un título y una descripción propios', () => {
    // Decenas de páginas con la misma metadata compiten entre sí y no
    // posicionan ninguna: el título y la descripción son lo que las distingue
    // en el buscador, así que ninguno puede repetirse ni quedarse en plantilla.
    const titles = COUNTRY_ROUTES.map((route) => route.title);
    const descriptions = COUNTRY_ROUTES.map((route) => route.description);
    expect(new Set(titles).size).toBe(COUNTRY_ROUTES.length);
    expect(new Set(descriptions).size).toBe(COUNTRY_ROUTES.length);

    for (const route of COUNTRY_ROUTES) {
      expect(route.title.length).toBeLessThanOrEqual(70);
      expect(route.description.length).toBeGreaterThanOrEqual(80);
      expect(route.description.length).toBeLessThanOrEqual(170);
    }
  });

  it('declara el convenio de doble imposición con España de cada país', () => {
    // `null` es una declaración, no un hueco: significa que no hay convenio en
    // vigor. Estos seis están comprobados contra la relación oficial de la
    // AEAT, así que la página puede decirlo en vez de callarse.
    const sinConvenio = COUNTRY_ROUTES.filter(
      (route) => route.corpusStatus === 'pending' && route.treatyBoeId === null
    ).map((route) => route.path);
    expect(sinConvenio).toEqual([
      '/monaco',
      '/guatemala',
      '/haiti',
      '/honduras',
      '/nicaragua',
      '/peru',
    ]);
    // España no tiene convenio consigo misma; su marco es el art. 9 LIRPF.
    expect(SPAIN_ROUTE.treatyBoeId).toBeNull();

    const convenios = COUNTRY_ROUTES.map((route) => route.treatyBoeId).filter(
      (boeId): boeId is string => boeId !== null
    );
    // Un mismo convenio en dos países señalaría un copiar y pegar.
    expect(new Set(convenios).size).toBe(convenios.length);
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

  it('identifica cada jurisdicción con su código ISO, no solo con el slug de la ruta', () => {
    // El dato usa el código ISO (`normativa/es/`, `jurisdiccion: 'es'`) y las
    // rutas usan slug (`/espana`). Sin una clave común, cruzar la web con el
    // corpus de un segundo país obliga a inventar la correspondencia cada vez.
    expect(SPAIN_ROUTE.code).toBe('es');
    expect(COUNTRY_ROUTES.find((route) => route.path === '/reino-unido')?.code).toBe('gb');
    expect(COUNTRY_ROUTES.find((route) => route.path === '/republica-dominicana')?.code).toBe('do');

    const codes = COUNTRY_ROUTES.map((route) => route.code);
    expect(new Set(codes).size).toBe(COUNTRY_ROUTES.length);
    for (const code of codes) expect(code).toMatch(/^[a-z]{2}$/);
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
