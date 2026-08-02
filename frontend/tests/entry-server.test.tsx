import { describe, expect, it } from 'vitest';
import { COUNTRY_ROUTES } from '@/data/countryRoutes';
import { STATIC_ROUTES } from '@/data/staticRoutes';
import { render } from '@/entry-server';
import { readEmbeddedTreatyPreload, TREATY_PRELOAD_ELEMENT_ID } from '@/lib/treaty-preload';
import type { PreceptoEntry, PreceptoTexto } from '@/types/normativa';

/**
 * Lo que de verdad se sirve.
 *
 * `scripts/prerender.mjs` escribe la salida de `render()` dentro del HTML
 * estático, así que estos tests comprueban lo que ve un buscador que no ejecute
 * JavaScript. Si algún día el árbol deja de renderizar fuera del navegador, el
 * build seguiría produciendo páginas —vacías— sin que nada avisara.
 */

const ENTRY: PreceptoEntry = {
  slug: 'cdi-boe-a-1997-12729-a4',
  jurisdiccion: 'es',
  titulo: 'Artículo 4 — Residente',
  norma: 'Convenio entre el Reino de España y la República Francesa…',
  designacion: 'Artículo 4',
  epigrafe: 'Residente',
  grupo: 'cdi',
  boeId: 'BOE-A-1997-12729',
  urlBoe: 'https://www.boe.es/buscar/act.php?id=BOE-A-1997-12729#a4',
  derogada: false,
  notaDerogacion: null,
  vigenteDesde: '1997-07-01',
  redacciones: 1,
  parrafos: 4,
  sentencias: [],
  totalSentencias: 0,
};

const TEXTO: PreceptoTexto = {
  ...ENTRY,
  articulado: ['1. A los efectos de este Convenio, la expresión «residente de un Estado»…'],
  redaccionesAnteriores: [],
  notasBoe: [],
};

describe('entry-server', () => {
  it('renderiza el contenido de una página de país sin navegador', () => {
    const html = render('/francia');

    expect(html).toContain('Residencia fiscal en');
    expect(html).toContain('Francia');
    expect(html).toContain('Convenio de doble imposición España');
    // La invitación a contribuir también tiene que estar en el HTML servido.
    expect(html).toContain('necesita a sus especialistas');
  });

  it('publica el convenio ya resuelto, no el «cargando»', () => {
    // El componente lo pide en un efecto, y en el build no hay efectos: sin la
    // precarga, la página estática se quedaría con el texto de espera.
    const html = render('/francia', { [ENTRY.boeId]: { entry: ENTRY, texto: TEXTO } });

    expect(html).toContain('residente de un Estado');
    expect(html).toContain('https://www.boe.es/buscar/act.php?id=BOE-A-1997-12729#a4');
    expect(html).not.toContain('Cargando el convenio');
  });

  it('dice sin convenio en las jurisdicciones que no lo tienen', () => {
    const html = render('/peru');

    expect(html).toContain('no tienen convenio');
    expect(html).not.toContain('Cargando el convenio');
  });

  it('publica en /espana la sección estática que lee un buscador sin JavaScript', () => {
    const html = render('/espana');

    expect(html).toContain('La residencia fiscal en España: qué dice el art. 9 LIRPF');
    expect(html).toContain('Permanencia de más de 183 días');
    expect(html).toContain('Núcleo principal de los intereses económicos');
    expect(html).toContain('no una aprobación humana');
  });

  it('publica la ficha de un precepto con su articulado literal', () => {
    const html = render(
      '/espana/normativa/cdi-boe-a-1997-12729-a4',
      {},
      { [ENTRY.slug]: { entry: ENTRY, texto: TEXTO } }
    );

    expect(html).toContain('Artículo 4 del convenio España-Francia');
    expect(html).toContain('residente de un Estado');
    expect(html).toContain('https://www.boe.es/buscar/act.php?id=BOE-A-1997-12729#a4');
    expect(html).not.toContain('Cargando el precepto');
  });

  it('publica el índice de normativa con enlaces a las fichas', () => {
    // Dos entradas como mínimo: el índice descarta a propósito una precarga de
    // una sola (sería la de una ficha, no el corpus completo).
    const SEGUNDO: PreceptoEntry = {
      ...ENTRY,
      slug: 'lirpf-a9',
      boeId: 'BOE-A-2006-20764',
      grupo: 'nucleo',
      titulo: 'Artículo 9 — Contribuyentes con residencia habitual',
      designacion: 'Artículo 9',
      epigrafe: null,
    };
    const html = render(
      '/espana/normativa',
      {},
      {
        [ENTRY.slug]: { entry: ENTRY, texto: null },
        [SEGUNDO.slug]: { entry: SEGUNDO, texto: null },
      }
    );

    expect(html).toContain('Normativa de la residencia fiscal en España');
    expect(html).toContain('href="/espana/normativa/cdi-boe-a-1997-12729-a4"');
    expect(html).toContain('href="/espana/normativa/lirpf-a9"');
  });

  it('sirve los datos estructurados en el HTML, que es donde los lee el bot', () => {
    const html = render('/francia', { [ENTRY.boeId]: { entry: ENTRY, texto: TEXTO } });

    const bloques = [...html.matchAll(/<script type="application\/ld\+json">(.*?)<\/script>/g)].map(
      (match) => JSON.parse(match[1])
    );
    // El layout emite la identidad del sitio en todas las rutas; la página
    // añade su jerarquía y el precepto que publica.
    expect(bloques.map((bloque) => bloque['@type'])).toEqual([
      'WebSite',
      'Organization',
      'BreadcrumbList',
      'Legislation',
    ]);
    expect(bloques[2].itemListElement[1].item).toBe('https://residenciafiscal.org/francia');
    expect(bloques[3].legislationIdentifier).toBe('BOE-A-1997-12729');
  });

  it('marca todas las rutas de país, también las que no usan CountryPage', () => {
    // `/espana` se renderiza con `SpainPage`, no con la plantilla compartida, y
    // por eso se quedó sin datos estructurados: es la landing con más prioridad
    // del sitio. El gate recorre la lista entera para que la próxima página de
    // país con plantilla propia no vuelva a caerse en silencio.
    for (const route of COUNTRY_ROUTES) {
      const html = render(route.path);
      const bloques = [
        ...html.matchAll(/<script type="application\/ld\+json">(.*?)<\/script>/g),
      ].map((match) => JSON.parse(match[1]));
      const breadcrumb = bloques.find((bloque) => bloque['@type'] === 'BreadcrumbList');

      expect(breadcrumb, `${route.path} sin BreadcrumbList`).toBeDefined();
      expect(breadcrumb.itemListElement.at(-1)).toMatchObject({
        name: route.name,
        item: `https://residenciafiscal.org${route.path}`,
      });
    }
    // Renderiza el árbol entero una vez por país, así que es el test más caro de
    // la suite y su coste crece con cada ruta nueva. Con los 5 s por defecto
    // agotaba el plazo de forma intermitente al competir por CPU.
  }, 30_000);

  it('marca también las rutas estáticas que sí se indexan', () => {
    // `/privacidad` es `noindex` y queda fuera a propósito: los datos
    // estructurados son para el buscador, y ahí no hay buscador que los lea.
    for (const route of STATIC_ROUTES.filter((candidate) => candidate.indexable)) {
      const html = render(route.path);
      const bloques = [
        ...html.matchAll(/<script type="application\/ld\+json">(.*?)<\/script>/g),
      ].map((match) => JSON.parse(match[1]));
      const breadcrumb = bloques.find((bloque) => bloque['@type'] === 'BreadcrumbList');

      expect(breadcrumb, `${route.path} sin BreadcrumbList`).toBeDefined();
      expect(breadcrumb.itemListElement.at(-1).item).toBe(
        `https://residenciafiscal.org${route.path}`
      );
    }
  }, 30_000);

  it('no marca lo que no se indexa', () => {
    // La identidad del sitio (WebSite/Organization) la emite el layout en
    // todas las rutas y es inocua; lo que una página `noindex` no debe llevar
    // son marcas de contenido propias: ni jerarquía ni precepto.
    const html = render('/privacidad');

    expect(html).not.toContain('BreadcrumbList');
    expect(html).not.toContain('"Legislation"');
  });

  it('renderiza también las rutas que no son de país', () => {
    expect(render('/manifiesto')).toContain('Manifiesto');
    expect(render('/colaborar')).toContain('fiscalidad y tributación internacional');
    expect(render('/espana')).toContain('Residencia Fiscal');
  });
});

describe('readEmbeddedTreatyPreload', () => {
  function sembrar(contenido: string | null) {
    document.body.replaceChildren();
    if (contenido === null) return;
    const script = document.createElement('script');
    script.id = TREATY_PRELOAD_ELEMENT_ID;
    script.type = 'application/json';
    script.textContent = contenido;
    document.body.append(script);
  }

  it('lee el convenio embebido en la página', () => {
    sembrar(JSON.stringify({ [ENTRY.boeId]: { entry: ENTRY, texto: TEXTO } }));

    expect(readEmbeddedTreatyPreload(document)[ENTRY.boeId]?.entry.boeId).toBe(ENTRY.boeId);
  });

  it('degrada a vacío en vez de tumbar el arranque', () => {
    // Sin el elemento (una página servida por el fallback de la SPA) y con un
    // JSON roto: en los dos casos la aplicación tiene que arrancar y cargar el
    // convenio por red, como hacía antes del prerenderizado.
    sembrar(null);
    expect(readEmbeddedTreatyPreload(document)).toEqual({});

    sembrar('{ esto no es json');
    expect(readEmbeddedTreatyPreload(document)).toEqual({});

    sembrar('["una lista"]');
    expect(readEmbeddedTreatyPreload(document)).toEqual({});
  });
});
