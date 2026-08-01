import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { PreceptoPreloadContext, type PreceptoPreloadMap } from '@/lib/precepto-preload';
import { PreceptoPage } from '@/pages/PreceptoPage';
import type { PreceptoEntry, PreceptoTexto } from '@/types/normativa';

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
  parrafos: 1,
  sentencias: [],
  totalSentencias: 0,
};

const TEXTO: PreceptoTexto = {
  ...ENTRY,
  articulado: ['1. A los efectos de este Convenio, la expresión «residente de un Estado»…'],
  redaccionesAnteriores: [],
  notasBoe: [],
};

const DEROGADO: PreceptoEntry = {
  ...ENTRY,
  slug: 'cdi-boe-a-1994-20084-a4',
  boeId: 'BOE-A-1994-20084',
  grupo: 'cdi_derogado',
  derogada: true,
  notaDerogacion: 'CDI España-Argentina de 1992, sustituido por el de 2013',
};

function renderFicha(slug: string, preload: PreceptoPreloadMap) {
  return render(
    <PreceptoPreloadContext.Provider value={preload}>
      <MemoryRouter initialEntries={[`/espana/normativa/${slug}`]}>
        <Routes>
          <Route path='/espana/normativa/:slug' element={<PreceptoPage />} />
        </Routes>
      </MemoryRouter>
    </PreceptoPreloadContext.Provider>
  );
}

describe('PreceptoPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('completa por red una precarga parcial del índice (sin articulado)', async () => {
    // La precarga del índice llega sin texto y sin citas: si la ficha se
    // quedara con ella, publicaría el artículo sin su texto para siempre.
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        if (String(url).endsWith('/data/normativa.json')) {
          return new Response(JSON.stringify([ENTRY]));
        }
        if (String(url).endsWith(`/data/preceptos/${ENTRY.slug}.json`)) {
          return new Response(JSON.stringify(TEXTO));
        }
        return new Response('no encontrado', { status: 404 });
      })
    );

    renderFicha(ENTRY.slug, {
      [ENTRY.slug]: { entry: { ...ENTRY, sentencias: [] }, texto: null },
    });

    // La cabecera sale de la precarga en el primer render…
    expect(
      screen.getByRole('heading', { name: 'Artículo 4 del convenio España-Francia' })
    ).toBeInTheDocument();
    // …y el articulado literal llega después por red.
    expect(await screen.findByText(/residente de un Estado/)).toBeInTheDocument();
  });

  it('publica el articulado literal, el enlace al BOE y la página del país', () => {
    renderFicha(ENTRY.slug, { [ENTRY.slug]: { entry: ENTRY, texto: TEXTO } });

    expect(
      screen.getByRole('heading', { name: 'Artículo 4 del convenio España-Francia' })
    ).toBeInTheDocument();
    expect(screen.getByText(/residente de un Estado/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Texto oficial en el BOE' })).toHaveAttribute(
      'href',
      ENTRY.urlBoe
    );
    // El convenio con Francia tiene página de país: la ficha debe enlazarla.
    expect(screen.getByRole('link', { name: /la página del país/ })).toHaveAttribute(
      'href',
      '/francia'
    );
    expect(screen.getByText(/Reproducción literal del texto del BOE/)).toBeInTheDocument();
  });

  it('fija el título y la descripción que también escribe el prerender', async () => {
    renderFicha(ENTRY.slug, { [ENTRY.slug]: { entry: ENTRY, texto: TEXTO } });

    await waitFor(() => {
      expect(document.title).toBe('Artículo 4 del CDI España-Francia: residencia fiscal');
    });
  });

  it('rotula las normas derogadas para que nadie las lea como derecho vigente', () => {
    renderFicha(DEROGADO.slug, { [DEROGADO.slug]: { entry: DEROGADO, texto: null } });

    expect(screen.getByText('Norma derogada.')).toBeInTheDocument();
    expect(screen.getByText(/sustituido por el de 2013/)).toBeInTheDocument();
  });

  it('un slug desconocido dice que el precepto no existe y enlaza el índice', async () => {
    renderFicha('no-existe', {});

    expect(
      await screen.findByRole('heading', { name: 'Precepto no encontrado' })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: /normativa de residencia fiscal en España/ })
    ).toHaveAttribute('href', '/espana/normativa');
  });
});
