import { describe, expect, it } from 'vitest';
import countryRoutes from '@/data/countryRoutes.json';
import {
  fichaDescription,
  fichaHeading,
  fichaPath,
  fichaTitle,
  NORMATIVA_INDEX_PATH,
  paisDelConvenio,
} from '@/lib/normativa-fichas';
import type { PreceptoEntry } from '@/types/normativa';
import normativa from '../public/data/normativa.json';

const ENTRIES = normativa as PreceptoEntry[];

/**
 * El contrato de las fichas de precepto: cada uno de los 110 artículos del
 * corpus normativo debe producir una URL, un título y una descripción únicos y
 * competitivos, sin excepciones silenciosas. Si `make export-normativa` añade
 * un convenio nuevo sin entrada en `normativaFichas.json`, estos tests fallan
 * en vez de publicar una ficha sin país.
 */
describe('normativa-fichas', () => {
  it('cubre los 110 preceptos del corpus', () => {
    expect(ENTRIES.length).toBeGreaterThanOrEqual(110);
    for (const entry of ENTRIES) {
      expect(fichaPath(entry), entry.slug).toMatch(/^\/espana\/normativa\/[a-z0-9-]+$/);
      expect(fichaTitle(entry).length, `título de ${entry.slug}`).toBeGreaterThan(20);
      expect(fichaTitle(entry).length, `título de ${entry.slug}`).toBeLessThanOrEqual(80);
      expect(fichaDescription(entry).length, `descripción de ${entry.slug}`).toBeGreaterThan(60);
      expect(fichaDescription(entry).length, `descripción de ${entry.slug}`).toBeLessThanOrEqual(
        180
      );
      expect(fichaHeading(entry).length, `h1 de ${entry.slug}`).toBeGreaterThan(10);
    }
  });

  it('las rutas y los títulos son únicos', () => {
    const paths = ENTRIES.map(fichaPath);
    const titles = ENTRIES.map(fichaTitle);
    expect(new Set(paths).size).toBe(ENTRIES.length);
    expect(new Set(titles).size).toBe(ENTRIES.length);
    expect(paths).not.toContain(NORMATIVA_INDEX_PATH);
  });

  it('todo CDI tiene país y coincide con el nombre de su página de país', () => {
    const byTreaty = new Map(
      countryRoutes
        .filter((route) => route.treatyBoeId)
        .map((route) => [route.treatyBoeId as string, route.name])
    );
    for (const entry of ENTRIES.filter((candidate) => candidate.grupo.startsWith('cdi'))) {
      const pais = paisDelConvenio(entry);
      expect(pais, `país de ${entry.slug}`).toBeTruthy();
      // Verificación cruzada: donde ya existe página de país, el nombre del
      // mapeo curado debe ser exactamente el mismo.
      const routeName = byTreaty.get(entry.boeId);
      if (routeName) expect(pais, entry.slug).toBe(routeName);
      expect(fichaTitle(entry)).toContain(`España-${pais}`);
    }
  });

  it('las normas derogadas lo dicen en el título y la descripción', () => {
    for (const entry of ENTRIES.filter((candidate) => candidate.derogada)) {
      expect(fichaTitle(entry).toLowerCase()).toContain('derogad');
      expect(fichaDescription(entry).toLowerCase()).toContain('derogad');
    }
  });

  it('el artículo 9 LIRPF, la ficha insignia, lleva sus palabras clave', () => {
    const lirpf9 = ENTRIES.find((entry) => entry.slug === 'lirpf-a9');
    expect(lirpf9).toBeDefined();
    if (!lirpf9) return;
    expect(fichaPath(lirpf9)).toBe('/espana/normativa/lirpf-a9');
    expect(fichaTitle(lirpf9)).toContain('Artículo 9');
    expect(fichaTitle(lirpf9)).toContain('LIRPF');
  });
});
