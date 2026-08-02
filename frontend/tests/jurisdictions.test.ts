import { describe, expect, it } from 'vitest';
import { COUNTRY_ROUTES, SPAIN_ROUTE } from '@/data/countryRoutes';
import countryRouteData from '@/data/countryRoutes.json';
import {
  counterpartNamesWithSeveralTreaties,
  currentTreatyBoeId,
  jurisdictionName,
  jurisdictionPath,
  treatyCounterpart,
  treatyCounterpartName,
  treatyInstruments,
} from '@/data/jurisdictions';

/**
 * El frontend consume el catálogo compartido en vez de guardar una copia.
 *
 * Antes, el nombre de un país y su convenio vivían a la vez en
 * `countryRoutes.json`, en `normativaFichas.json` y en una tabla de Python.
 * Tres copias editables del mismo hecho divergen sin que nada lo detecte: la
 * página de un país podía decir «Méjico» y la ficha de su convenio «México».
 *
 * Los dos JSON que se leen aquí los genera `src/export_frontend_projections.py`
 * y `tests/test_frontend_projections.py` falla si quedan desincronizados.
 */
describe('catálogo de jurisdicciones', () => {
  it('el JSON de rutas ya no guarda el nombre ni el convenio', () => {
    for (const route of countryRouteData) {
      expect(route, route.code).not.toHaveProperty('name');
      expect(route, route.code).not.toHaveProperty('treatyBoeId');
    }
  });

  it('compone el nombre de las 34 rutas desde la proyección', () => {
    expect(COUNTRY_ROUTES).toHaveLength(34);
    for (const route of COUNTRY_ROUTES) {
      expect(route.name, route.code).toBe(jurisdictionName(route.code));
      expect(route.name.length, route.code).toBeGreaterThan(0);
    }
    expect(SPAIN_ROUTE.name).toBe('España');
  });

  it('la ruta de cada país es el slug del catálogo', () => {
    for (const route of COUNTRY_ROUTES) {
      expect(jurisdictionPath(route.code), route.code).toBe(route.path);
    }
  });

  it('resuelve el convenio vigente de cada país desde el registro', () => {
    const conConvenio = COUNTRY_ROUTES.filter((route) => route.treatyBoeId !== null);
    expect(conConvenio).toHaveLength(27);
    expect(SPAIN_ROUTE.treatyBoeId).toBeNull();

    for (const route of conConvenio) {
      expect(route.treatyBoeId, route.code).toBe(currentTreatyBoeId(route.code));
      expect(treatyCounterpart(route.treatyBoeId as string), route.code).toBe(route.code);
    }
  });

  it('las jurisdicciones sin convenio en vigor lo dicen con null, no con undefined', () => {
    for (const code of ['gt', 'ht', 'hn', 'ni', 'pe', 'mc']) {
      expect(currentTreatyBoeId(code), code).toBeNull();
      expect(treatyInstruments(code), code).toHaveLength(0);
    }
  });

  it('los países con dos convenios exponen el sustituido y el vigente', () => {
    for (const code of ['gb', 'ar', 'jp', 'ro', 'cn']) {
      const instruments = treatyInstruments(code);
      expect(
        instruments.map((instrument) => instrument.status),
        code
      ).toEqual(['superseded', 'current']);
    }
    expect(counterpartNamesWithSeveralTreaties()).toEqual(
      new Set(['Reino Unido', 'Argentina', 'Japón', 'Rumanía', 'China'])
    );
  });

  it('el convenio de Japón sustituido rige hasta el ejercicio 2021', () => {
    // El convenio de 2018 surte efecto para los ejercicios que comienzan desde
    // el 1 de enero del año siguiente a su entrada en vigor (1-5-2021).
    const [anterior, vigente] = treatyInstruments('jp');
    expect(anterior.toTaxYear).toBe(2021);
    expect(vigente.fromTaxYear).toBe(2022);
  });

  it('nombra la contraparte de un convenio sin mirar el título de la norma', () => {
    expect(treatyCounterpartName('BOE-A-1990-30940')).toBe('Estados Unidos');
    expect(treatyCounterpartName('BOE-A-1967-3470')).toBe('Suiza');
    // Estados extintos: sus convenios siguen en el corpus con su contraparte
    // histórica, codificada según ISO 3166-3.
    expect(treatyCounterpartName('BOE-A-1981-15642')).toBe('Checoslovaquia');
    expect(treatyCounterpartName('BOE-A-2006-20764')).toBeNull();
  });

  it('un código desconocido rompe el build en vez de publicar «undefined»', () => {
    expect(() => jurisdictionName('zz')).toThrow(/no está en el catálogo/);
    expect(() => jurisdictionPath('zz')).toThrow(/no está en el catálogo/);
  });
});
