import { afterEach, describe, expect, it, vi } from 'vitest';
import { loadSentencia, loadSentenciasIndex, resetSentenciasCache } from '@/lib/sentencias';

function ficha(jurisdiction: string, roj: string) {
  return {
    schemaVersion: 'residenciafiscal-public-judgment/1',
    jurisdiction,
    publicationState: 'published',
    judgment: {
      judgmentId: 'residencia-1-2026',
      roj,
      sourceSha256: 'a'.repeat(64),
    },
    issues: [],
    anchors: [],
  };
}

afterEach(() => {
  vi.restoreAllMocks();
  resetSentenciasCache();
});

describe('loaders de sentencias multijurisdicción', () => {
  it('selecciona cada índice del manifiesto agregado con una sola petición', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          schemaVersion: 'residenciafiscal-sentencias-index/2',
          jurisdictions: {
            es: { jurisdiction: 'es', candidates: 1, includesPreview: false, judgments: [] },
            fr: { jurisdiction: 'fr', candidates: 2, includesPreview: false, judgments: [] },
          },
        })
      )
    );

    const [espana, francia] = await Promise.all([
      loadSentenciasIndex('es'),
      loadSentenciasIndex('fr'),
    ]);

    expect(espana.candidates).toBe(1);
    expect(francia.candidates).toBe(2);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith('/data/sentencias.json');
  });

  it('aísla por país dos fichas con el mismo identificador', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      return new Response(
        JSON.stringify(url.includes('/fr/') ? ficha('fr', 'CE 1/2026') : ficha('es', 'STS 1/2026'))
      );
    });

    const [espana, francia] = await Promise.all([
      loadSentencia('es', 'residencia-1-2026'),
      loadSentencia('fr', 'residencia-1-2026'),
    ]);

    expect(espana?.judgment.roj).toBe('STS 1/2026');
    expect(francia?.judgment.roj).toBe('CE 1/2026');
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      '/data/sentencias/es/residencia-1-2026.json',
      '/data/sentencias/fr/residencia-1-2026.json',
    ]);
  });
});
