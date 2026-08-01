import { describe, expect, it } from 'vitest';
import { COUNTRY_ROUTES } from '@/data/countryRoutes';
import { breadcrumbJsonLd, jsonLdScript, treatyJsonLd } from '@/lib/structured-data';
import type { PreceptoEntry } from '@/types/normativa';

const URUGUAY: PreceptoEntry = {
  slug: 'cdi-boe-a-2011-6551-a4',
  jurisdiccion: 'es',
  titulo: 'Artículo 4 — Residente',
  norma: 'Convenio entre el Reino de España y la República Oriental del Uruguay',
  designacion: 'Artículo 4',
  epigrafe: 'Residente',
  grupo: 'cdi',
  boeId: 'BOE-A-2011-6551',
  urlBoe: 'https://www.boe.es/buscar/act.php?id=BOE-A-2011-6551#a4',
  derogada: false,
  notaDerogacion: null,
  vigenteDesde: '2011-04-24',
  redacciones: 1,
  parrafos: 4,
  sentencias: [],
  totalSentencias: 0,
};

function countryByPath(path: string) {
  const route = COUNTRY_ROUTES.find((candidate) => candidate.path === path);
  if (!route) throw new Error(`ruta de país no registrada: ${path}`);
  return route;
}

describe('breadcrumbJsonLd', () => {
  it('encadena los tramos de una subpágina bajo su país', () => {
    // `/espana/fuentes` es contenido de país, no de método, y tiene la única
    // jerarquía de tres niveles del sitio.
    const breadcrumb = breadcrumbJsonLd([
      countryByPath('/espana'),
      { name: 'El corpus de España', path: '/espana/fuentes' },
    ]);

    expect(breadcrumb.itemListElement.map((item) => [item.position, item.name, item.item])).toEqual(
      [
        [1, 'Residencia Fiscal', 'https://residenciafiscal.org/'],
        [2, 'España', 'https://residenciafiscal.org/espana'],
        [3, 'El corpus de España', 'https://residenciafiscal.org/espana/fuentes'],
      ]
    );
  });

  it('describe la jerarquía del sitio con URLs absolutas', () => {
    const breadcrumb = breadcrumbJsonLd([countryByPath('/francia')]);

    expect(breadcrumb['@context']).toBe('https://schema.org');
    expect(breadcrumb['@type']).toBe('BreadcrumbList');
    expect(breadcrumb.itemListElement).toEqual([
      {
        '@type': 'ListItem',
        position: 1,
        name: 'Residencia Fiscal',
        item: 'https://residenciafiscal.org/',
      },
      {
        '@type': 'ListItem',
        position: 2,
        name: 'Francia',
        item: 'https://residenciafiscal.org/francia',
      },
    ]);
  });
});

describe('treatyJsonLd', () => {
  it('describe el artículo de residencia del convenio con su identificador del BOE', () => {
    const legislation = treatyJsonLd(URUGUAY);

    expect(legislation).toMatchObject({
      '@context': 'https://schema.org',
      '@type': 'Legislation',
      name: 'Artículo 4 — Residente',
      legislationIdentifier: 'BOE-A-2011-6551',
      url: 'https://www.boe.es/buscar/act.php?id=BOE-A-2011-6551#a4',
      inLanguage: 'es',
      legislationJurisdiction: 'España',
      isPartOf: {
        '@type': 'Legislation',
        name: 'Convenio entre el Reino de España y la República Oriental del Uruguay',
      },
    });
  });

  it('publica la fecha como versión consolidada, no como fecha de adopción', () => {
    // `vigenteDesde` es la redacción vigente del precepto, no la firma del
    // convenio: `legislationDate` diría algo que el corpus no sabe.
    const legislation = treatyJsonLd(URUGUAY);

    expect(legislation.legislationDateVersion).toBe('2011-04-24');
    expect(legislation).not.toHaveProperty('legislationDate');
  });

  it('declara la fuerza legal desde el corpus, sin presumir vigencia', () => {
    expect(treatyJsonLd(URUGUAY).legislationLegalForce).toBe('https://schema.org/InForce');
    expect(
      treatyJsonLd({ ...URUGUAY, derogada: true, notaDerogacion: 'Sustituido en 2013' })
        .legislationLegalForce
    ).toBe('https://schema.org/NotInForce');
  });

  it('omite los campos que el corpus no tiene en lugar de inventarlos', () => {
    const legislation = treatyJsonLd({ ...URUGUAY, urlBoe: null, vigenteDesde: null });

    expect(legislation).not.toHaveProperty('url');
    expect(legislation).not.toHaveProperty('legislationDateVersion');
  });
});

describe('jsonLdScript', () => {
  it('escapa `<` para que el texto legal no pueda cerrar la etiqueta', () => {
    // Un `</script>` dentro de un título del BOE romperia el documento entero.
    const serializado = jsonLdScript({ name: '</script><img src=x>' });

    expect(serializado).not.toContain('</script>');
    expect(serializado).toContain('\\u003c/script');
    expect(JSON.parse(serializado)).toEqual({ name: '</script><img src=x>' });
  });
});
