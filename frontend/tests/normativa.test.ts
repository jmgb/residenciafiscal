import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  loadNormativa,
  loadPrecepto,
  normativaLoadFailed,
  preceptosCitados,
  resetNormativaCache,
  sentenciasDe,
} from '@/lib/normativa';
import type { PreceptoEntry, PreceptoTexto } from '@/types/normativa';

const frontendDir = join(dirname(fileURLToPath(import.meta.url)), '..');
const dataDir = join(frontendDir, 'public', 'data');
const repoDir = join(frontendDir, '..');

const entry: PreceptoEntry = {
  slug: 'lirpf-a9',
  jurisdiccion: 'es',
  titulo: 'Artículo 9 LIRPF — Contribuyentes que tienen su residencia habitual',
  norma: 'Ley 35/2006, de 28 de noviembre, del IRPF',
  designacion: 'Artículo 9',
  epigrafe: 'Contribuyentes que tienen su residencia habitual en territorio español',
  grupo: 'nucleo',
  boeId: 'BOE-A-2006-20764',
  urlBoe: 'https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764#a9',
  derogada: false,
  notaDerogacion: null,
  vigenteDesde: '2007-01-01',
  redacciones: 1,
  parrafos: 7,
  sentencias: [
    {
      archivo: 'SAN_1071_2025.pdf',
      roj: 'SAN 1071/2025',
      ejercicios: [2010],
      certeza: 'explicita',
    },
    { archivo: 'SAN_1071_2025.pdf', roj: 'SAN 1071/2025', ejercicios: [2010], certeza: 'inferida' },
  ],
  totalSentencias: 1,
};

const texto: PreceptoTexto = {
  ...entry,
  articulado: ['Artículo 9. Contribuyentes…', '1. Se entenderá que…'],
  redaccionesAnteriores: [],
  notasBoe: [],
};

function jsonResponse(body: unknown, ok = true, status = 200): Response {
  return { ok, status, json: async () => body } as unknown as Response;
}

/** Lo que devuelve el catch-all de Netlify cuando el fichero no existe. */
function htmlResponse(): Response {
  return {
    ok: true,
    status: 200,
    json: async () => {
      throw new SyntaxError('Unexpected token < in JSON at position 0');
    },
  } as unknown as Response;
}

let consoleError: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  resetNormativaCache();
  consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
  consoleError.mockRestore();
  vi.unstubAllGlobals();
});

describe('carga del índice', () => {
  it('devuelve los preceptos válidos', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => jsonResponse([entry]))
    );

    await expect(loadNormativa()).resolves.toEqual([entry]);
    expect(normativaLoadFailed()).toBe(false);
  });

  it('cachea el índice: el fichero es inmutable durante la vida de la página', async () => {
    const fetchMock = vi.fn(async () => jsonResponse([entry]));
    vi.stubGlobal('fetch', fetchMock);

    await loadNormativa();
    await loadNormativa();

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('degrada a vacío y avisa si el catch-all sirve el HTML de la SPA', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => htmlResponse())
    );

    await expect(loadNormativa()).resolves.toEqual([]);
    expect(normativaLoadFailed()).toBe(true);
    expect(consoleError).toHaveBeenCalled();
  });

  it('rechaza un índice que no sea un array', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => jsonResponse({ preceptos: [] }))
    );

    await expect(loadNormativa()).resolves.toEqual([]);
    expect(normativaLoadFailed()).toBe(true);
  });

  it('rechaza una entrada con grupo desconocido', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => jsonResponse([{ ...entry, grupo: 'inventado' }]))
    );

    await expect(loadNormativa()).resolves.toEqual([]);
    expect(normativaLoadFailed()).toBe(true);
  });

  it('rechaza un índice con preceptos duplicados', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => jsonResponse([entry, entry]))
    );

    await expect(loadNormativa()).resolves.toEqual([]);
    expect(normativaLoadFailed()).toBe(true);
  });

  it('no cachea el fallo: un error de red transitorio no deja la sesión sin normativa', async () => {
    const fetchMock = vi
      .fn<() => Promise<Response>>()
      .mockResolvedValueOnce(jsonResponse(null, false, 503))
      .mockResolvedValueOnce(jsonResponse([entry]));
    vi.stubGlobal('fetch', fetchMock);

    await expect(loadNormativa()).resolves.toEqual([]);
    await expect(loadNormativa()).resolves.toEqual([entry]);
    expect(normativaLoadFailed()).toBe(false);
  });
});

describe('carga del articulado', () => {
  it('devuelve el texto de un precepto', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => jsonResponse(texto))
    );

    await expect(loadPrecepto('lirpf-a9')).resolves.toEqual(texto);
  });

  it('devuelve null si el articulado viene vacío', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => jsonResponse({ ...texto, articulado: [] }))
    );

    await expect(loadPrecepto('lirpf-a9')).resolves.toBeNull();
    expect(consoleError).toHaveBeenCalled();
  });

  it('rechaza un fichero que declara otro slug', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => jsonResponse({ ...texto, slug: 'lgt-a105' }))
    );

    await expect(loadPrecepto('lirpf-a9')).resolves.toBeNull();
  });
});

describe('utilidades', () => {
  it('ordena los citados de más a menos sentencias', () => {
    const otro = { ...entry, slug: 'lgt-a105', totalSentencias: 8 };
    const sinCitas = { ...entry, slug: 'cdi-x', totalSentencias: 0 };

    expect(preceptosCitados([entry, otro, sinCitas]).map((p) => p.slug)).toEqual([
      'lgt-a105',
      'lirpf-a9',
    ]);
  });

  it('no repite una sentencia que cita el mismo precepto dos veces', () => {
    expect(sentenciasDe(entry)).toEqual(['SAN_1071_2025.pdf']);
  });
});

describe('datos generados', () => {
  it('el índice versionado supera la validación del loader', async () => {
    const data: unknown = JSON.parse(readFileSync(join(dataDir, 'normativa.json'), 'utf8'));
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => jsonResponse(data))
    );

    const preceptos = await loadNormativa();

    expect(normativaLoadFailed()).toBe(false);
    expect(preceptos.length).toBeGreaterThan(100);
    expect(preceptos.every((p) => p.jurisdiccion === 'es')).toBe(true);
  });

  it('el índice no lleva articulado: es lo que lo mantiene ligero', () => {
    const data = JSON.parse(readFileSync(join(dataDir, 'normativa.json'), 'utf8')) as Record<
      string,
      unknown
    >[];

    expect(data.every((entrada) => !('articulado' in entrada))).toBe(true);
  });

  it('el articulado publicado es literal: aparece tal cual en el Markdown de origen', () => {
    // El invariante jurídico cruza aquí a JavaScript. Si el generador recortara,
    // uniera o normalizara un párrafo, el frontend mostraría texto legal que el
    // BOE no publicó.
    for (const slug of ['lirpf-a9', 'lgt-a108', 'cdi-boe-a-1994-20084-a4']) {
      const precepto = JSON.parse(
        readFileSync(join(dataDir, 'preceptos', `${slug}.json`), 'utf8')
      ) as PreceptoTexto;
      const markdown = readFileSync(
        join(repoDir, 'knowledge', 'normativa', 'es', 'preceptos', `${slug}.md`),
        'utf8'
      );

      expect(precepto.articulado.length).toBeGreaterThan(0);
      for (const parrafo of precepto.articulado) {
        expect(markdown).toContain(parrafo);
      }
    }
  });

  it('los convenios sustituidos llegan marcados como derogados', () => {
    const data = JSON.parse(
      readFileSync(join(dataDir, 'normativa.json'), 'utf8')
    ) as PreceptoEntry[];
    const derogados = data.filter((p) => p.derogada);

    expect(derogados).toHaveLength(4);
    for (const precepto of derogados) {
      expect(precepto.notaDerogacion).toBeTruthy();
    }
  });
});
