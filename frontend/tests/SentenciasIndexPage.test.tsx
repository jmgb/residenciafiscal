import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { SentenciaPreloadContext } from '@/lib/sentencia-preload';
import { resetSentenciasCache } from '@/lib/sentencias';
import { SentenciasIndexPage } from '@/pages/SentenciasIndexPage';
import type { SentenciaIndexEntry, SentenciasIndex } from '@/types/sentencias';

const ENTRADA: SentenciaIndexEntry = {
  judgmentId: 'san-1386-2017',
  roj: 'SAN 1386/2017',
  court: 'Audiencia Nacional',
  decisionDate: '2017-03-29',
  taxYears: [2009],
  criterionIds: ['CRIT_183_DIAS'],
  outcomes: ['GANA_CONTRIBUYENTE'],
  jurisdictions: ['ch', 'es'],
  publicationState: 'internal_preview',
  legalReview: 'AGENT_REVIEWED',
};

const OTRA: SentenciaIndexEntry = {
  ...ENTRADA,
  judgmentId: 'sts-4306-2017',
  roj: 'STS 4306/2017',
  court: 'Tribunal Supremo',
  decisionDate: '2017-11-16',
  criterionIds: ['CRIT_CDI_TIEBREAKER'],
  outcomes: ['GANA_AEAT'],
};

function indice(judgments: SentenciaIndexEntry[], candidates = judgments.length): SentenciasIndex {
  return {
    schemaVersion: 'residenciafiscal-sentencias-index/1',
    jurisdiction: 'es',
    candidates,
    includesPreview: true,
    judgments,
  };
}

function renderIndice(index: SentenciasIndex) {
  return render(
    <SentenciaPreloadContext.Provider value={{ index, fichas: {} }}>
      <MemoryRouter initialEntries={['/espana/sentencias']}>
        <SentenciasIndexPage />
      </MemoryRouter>
    </SentenciaPreloadContext.Provider>
  );
}

/** `link[rel=canonical]` limpio: jsdom no trae el de `index.html`. */
function prepararCanonical(): HTMLLinkElement {
  for (const previo of document.querySelectorAll('link[rel="canonical"]')) previo.remove();
  const link = document.createElement('link');
  link.setAttribute('rel', 'canonical');
  document.head.appendChild(link);
  return link;
}

function prepararMetaRobots(): HTMLMetaElement {
  for (const previo of document.querySelectorAll('meta[name="robots"]')) previo.remove();
  const meta = document.createElement('meta');
  meta.setAttribute('name', 'robots');
  meta.setAttribute('content', 'index, follow');
  document.head.appendChild(meta);
  return meta;
}

afterEach(() => {
  vi.restoreAllMocks();
  resetSentenciasCache();
});

describe('SentenciasIndexPage', () => {
  it('lista las sentencias con su órgano, criterio y resultado', () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(indice([ENTRADA, OTRA]))) as Response
    );

    renderIndice(indice([ENTRADA, OTRA]));

    expect(screen.getByRole('link', { name: 'SAN 1386/2017' })).toHaveAttribute(
      'href',
      '/espana/sentencias/san-1386-2017'
    );
    // `getAllByText`: la etiqueta aparece también en el desplegable de filtro.
    expect(screen.getAllByText('Permanencia de 183 días').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Gana la Administración').length).toBeGreaterThan(0);
  });

  it('filtra en cliente sin cambiar de URL ni de canonical', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(indice([ENTRADA, OTRA]))) as Response
    );
    const canonical = prepararCanonical();

    renderIndice(indice([ENTRADA, OTRA]));
    await userEvent.selectOptions(screen.getByLabelText('Criterio'), 'CRIT_CDI_TIEBREAKER');

    expect(screen.queryByRole('link', { name: 'SAN 1386/2017' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'STS 4306/2017' })).toBeInTheDocument();
    // El canonical del índice es siempre su ruta base: una faceta no crea URL.
    expect(canonical.getAttribute('href')).toBe('https://residenciafiscal.org/espana/sentencias');
  });

  it('con cero publicadas explica por qué, en vez de aparentar un corpus vacío', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(indice([], 67))) as Response
    );

    renderIndice(indice([], 67));

    await waitFor(() => {
      expect(
        screen.getByText(/67 sentencias sobre residencia fiscal analizadas/)
      ).toBeInTheDocument();
    });
    expect(screen.getByText(/supera la revisión de una persona/)).toBeInTheDocument();
  });

  it('distingue un fallo de carga de un listado legítimamente vacío', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('null', { status: 500 }) as Response
    );
    vi.spyOn(console, 'error').mockImplementation(() => {});

    render(
      <MemoryRouter initialEntries={['/espana/sentencias']}>
        <SentenciasIndexPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/No se ha podido cargar el índice/)).toBeInTheDocument();
    });
  });

  it('marca como borrador lo que aún no está publicado', () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(indice([ENTRADA]))) as Response
    );

    renderIndice(indice([ENTRADA]));

    expect(screen.getByText('borrador interno')).toBeInTheDocument();
  });

  it('mantiene noindex en runtime cuando el índice contiene borradores', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(indice([ENTRADA]))) as Response
    );
    const meta = prepararMetaRobots();

    renderIndice(indice([ENTRADA]));

    await waitFor(() => expect(meta).toHaveAttribute('content', 'noindex, follow'));
  });
});
