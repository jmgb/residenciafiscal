import { describe, expect, it } from 'vitest';
import { normalizeRoutePath } from '@/lib/route-path';

describe('normalizeRoutePath', () => {
  it('decodifica y convierte las tildes de una ruta a su forma ASCII', () => {
    expect(normalizeRoutePath('/espa%C3%B1a')).toBe('/espana');
    expect(normalizeRoutePath('/per%C3%BA')).toBe('/peru');
    expect(normalizeRoutePath('/rep%C3%BAblica-dominicana')).toBe('/republica-dominicana');
  });

  it('mantiene una ruta mal codificada sin lanzar una excepción', () => {
    expect(normalizeRoutePath('/pais%')).toBe('/pais%');
  });
});
