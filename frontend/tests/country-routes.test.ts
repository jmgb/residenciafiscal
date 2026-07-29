import { describe, expect, it } from 'vitest';
import { COUNTRY_ROUTES } from '@/data/countryRoutes';

describe('country routes', () => {
  it('declara metadata SEO personalizada para cada ruta', () => {
    expect(COUNTRY_ROUTES).toHaveLength(21);
    expect(COUNTRY_ROUTES.find((route) => route.path === '/españa')).toMatchObject({
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
});
