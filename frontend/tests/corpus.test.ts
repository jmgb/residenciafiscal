import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { corpusLoadFailed, loadCorpus, resetCorpusCache } from '@/lib/corpus';
import type { CorpusEntry } from '@/types/chat';

const entry: CorpusEntry = {
  archivo: 'STS_107_2018.pdf',
  roj: 'STS 107/2018',
  ecli: 'ECLI:ES:TS:2018:107',
  organo: 'Tribunal Supremo. Sala de lo Contencioso-Administrativo',
  fecha: '2018-01-16',
  resultado: 'GANA_AEAT',
  criterioDecisivo: ['CRIT_183_DIAS'],
  esCasoResidencia: true,
};

/** Respuesta mínima con la superficie de `Response` que usa `loadCorpus`. */
function jsonResponse(body: unknown, ok = true, status = 200): Response {
  return {
    ok,
    status,
    json: async () => body,
  } as unknown as Response;
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

function silenceConsoleError() {
  return vi.spyOn(console, 'error').mockImplementation(() => {});
}

let consoleError: ReturnType<typeof silenceConsoleError>;

beforeEach(() => {
  resetCorpusCache();
  consoleError = silenceConsoleError();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  resetCorpusCache();
});

describe('loadCorpus', () => {
  it('devuelve las entradas cuando la respuesta es correcta', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => jsonResponse([entry]))
    );

    await expect(loadCorpus()).resolves.toEqual([entry]);
    expect(corpusLoadFailed()).toBe(false);
    expect(consoleError).not.toHaveBeenCalled();
  });

  it('pide el corpus una sola vez: la segunda llamada usa la caché', async () => {
    const fetchMock = vi.fn(async () => jsonResponse([entry]));
    vi.stubGlobal('fetch', fetchMock);

    const first = await loadCorpus();
    const second = await loadCorpus();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(second).toBe(first);
  });

  it('degrada a corpus vacío y avisa cuando la respuesta no es ok', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => jsonResponse(null, false, 404))
    );

    await expect(loadCorpus()).resolves.toEqual([]);
    expect(corpusLoadFailed()).toBe(true);
    expect(consoleError).toHaveBeenCalledTimes(1);
    expect(String(consoleError.mock.calls[0]?.[1])).toContain('404');
  });

  it('trata como fallo el index.html que sirve el catch-all de Netlify', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => htmlResponse())
    );

    await expect(loadCorpus()).resolves.toEqual([]);
    expect(corpusLoadFailed()).toBe(true);
    expect(consoleError).toHaveBeenCalledTimes(1);
  });

  it('trata como fallo un JSON válido que no es un array', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => jsonResponse({ entradas: [entry] }))
    );

    await expect(loadCorpus()).resolves.toEqual([]);
    expect(corpusLoadFailed()).toBe(true);
    expect(String(consoleError.mock.calls[0]?.[1])).toContain('no devolvió un array');
  });

  it('degrada a corpus vacío y avisa cuando falla la red', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new TypeError('Failed to fetch');
      })
    );

    await expect(loadCorpus()).resolves.toEqual([]);
    expect(corpusLoadFailed()).toBe(true);
    expect(consoleError).toHaveBeenCalledTimes(1);
  });

  it('no cachea el fallo: la siguiente llamada reintenta y puede recuperarse', async () => {
    const fetchMock = vi
      .fn<() => Promise<Response>>()
      .mockImplementationOnce(async () => {
        throw new TypeError('Failed to fetch');
      })
      .mockImplementation(async () => jsonResponse([entry]));
    vi.stubGlobal('fetch', fetchMock);

    await expect(loadCorpus()).resolves.toEqual([]);
    expect(corpusLoadFailed()).toBe(true);

    await expect(loadCorpus()).resolves.toEqual([entry]);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(corpusLoadFailed()).toBe(false);
  });
});
