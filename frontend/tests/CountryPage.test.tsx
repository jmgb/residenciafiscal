import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it, vi } from 'vitest';
import { COUNTRY_ROUTES, type CountryRoute } from '@/data/countryRoutes';
import { CONTACT_EMAIL, EXPERT_PROFILES } from '@/lib/contribution';
import { loadNormativa } from '@/lib/normativa';
import { TreatyPreloadContext } from '@/lib/treaty-preload';
import { CountryPage } from '@/pages/CountryPage';

/**
 * El corpus normativo se sirve por `fetch` desde `public/data/`, que en jsdom no
 * existe. Se sustituye por el precepto real del convenio España-Uruguay: basta
 * con uno para comprobar que la ficha se compone con lo que devuelve el índice.
 */
const URUGUAY = vi.hoisted(() => ({
  entry: {
    slug: 'cdi-boe-a-2011-6551-a4',
    jurisdiccion: 'es',
    titulo: 'Artículo 4 — Residente',
    norma: 'Convenio entre el Reino de España y la República Oriental del Uruguay…',
    designacion: 'Artículo 4',
    epigrafe: 'Residente',
    grupo: 'cdi' as const,
    boeId: 'BOE-A-2011-6551',
    urlBoe: 'https://www.boe.es/buscar/act.php?id=BOE-A-2011-6551#a4',
    derogada: false,
    notaDerogacion: null,
    vigenteDesde: '2011-04-24',
    redacciones: 1,
    parrafos: 4,
    sentencias: [],
    totalSentencias: 0,
  },
  get texto() {
    // `PreceptoTexto` extiende la entrada del índice: el articulado viaja con
    // los mismos metadatos, no sueltos.
    return {
      ...this.entry,
      articulado: ['1. A los efectos de este Convenio, la expresión «residente de un Estado»…'],
      redaccionesAnteriores: [],
      notasBoe: [],
    };
  },
}));

vi.mock('@/lib/normativa', () => ({
  loadNormativa: vi.fn(async () => [URUGUAY.entry]),
  loadPrecepto: vi.fn(async () => URUGUAY.texto),
  sentenciasDe: () => [],
}));

function countryByPath(path: string): CountryRoute {
  const route = COUNTRY_ROUTES.find((candidate) => candidate.path === path);
  if (!route) throw new Error(`ruta de país no registrada: ${path}`);
  return route;
}

function renderCountry(path: string) {
  const country = countryByPath(path);
  return render(
    <MemoryRouter initialEntries={[country.path]}>
      <CountryPage country={country} />
    </MemoryRouter>
  );
}

describe('CountryPage', () => {
  it('invita a contribuir con la jurisprudencia del país pendiente', () => {
    renderCountry('/argentina');

    expect(
      screen.getByRole('heading', { name: /Argentina necesita a sus especialistas/ })
    ).toBeInTheDocument();
    // El registro es profesional a propósito: la aportación que falta es
    // jurídica y cualificada, no «cualquiera puede».
    expect(screen.queryByText(/lo puede abrir cualquiera/i)).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Proponer Argentina/ })).toHaveAttribute(
      'href',
      'https://github.com/jmgb/residenciafiscal/issues/new?template=aportar_pais.yml&title=Aportar+jurisprudencia%3A+Argentina&pais=Argentina'
    );
  });

  it('codifica el nombre del país en el enlace de la issue', () => {
    renderCountry('/mexico');

    const cta = screen.getByRole('link', { name: /Proponer México/ });
    expect(cta).toHaveAttribute('href', expect.stringContaining('pais=M%C3%A9xico'));
    expect(cta).toHaveAttribute('href', expect.stringContaining('template=aportar_pais.yml'));
  });

  it('explica que el proyecto se nutre de expertos y enumera sus perfiles', () => {
    renderCountry('/colombia');

    expect(
      screen.getByText(/expertos en fiscalidad y tributación internacional/i)
    ).toBeInTheDocument();
    const perfiles = screen.getByRole('list', { name: 'Perfiles que pueden colaborar' });
    expect(perfiles).toBeInTheDocument();
    for (const profile of EXPERT_PROFILES) {
      expect(screen.getByText(profile.title)).toBeInTheDocument();
    }
  });

  it('ofrece el correo como canal equivalente y enlaza a /colaborar', () => {
    renderCountry('/peru');

    expect(screen.getByRole('link', { name: CONTACT_EMAIL })).toHaveAttribute(
      'href',
      `mailto:${CONTACT_EMAIL}?subject=Aportar%20jurisprudencia%3A%20Per%C3%BA`
    );
    expect(screen.getByRole('link', { name: 'Cómo colaborar' })).toHaveAttribute(
      'href',
      '/colaborar'
    );
  });

  it('enumera las tres aportaciones que necesita un país nuevo', () => {
    renderCountry('/chile');

    const requisitos = screen.getByRole('list', { name: 'Qué necesita un país nuevo' });
    expect(requisitos).toBeInTheDocument();
    expect(screen.getByText(/fuente pública oficial/i)).toBeInTheDocument();
    expect(screen.getByText(/equivalente al art\. 9 LIRPF/i)).toBeInTheDocument();
    expect(screen.getByText(/profesional del derecho tributario/i)).toBeInTheDocument();
  });

  it('no afirma que ya exista corpus del país ni ofrece consulta', () => {
    renderCountry('/brasil');

    expect(screen.getByText(/todavía no hay jurisprudencia de Brasil en el corpus/i)).toBeVisible();
    expect(screen.queryByTestId('chat-welcome')).not.toBeInTheDocument();
  });

  it('publica el convenio de doble imposición con España y su enlace oficial', async () => {
    renderCountry('/uruguay');

    expect(
      screen.getByRole('heading', { name: /Convenio de doble imposición España–Uruguay/ })
    ).toBeInTheDocument();
    // El enlace al BOE es lo que hace verificable la página: sin él, el dato
    // sería una afirmación nuestra sobre derecho vigente.
    const oficial = await screen.findByRole('link', {
      name: /Texto oficial del convenio en el BOE/,
    });
    expect(oficial).toHaveAttribute(
      'href',
      'https://www.boe.es/buscar/act.php?id=BOE-A-2011-6551#a4'
    );
    expect(await screen.findByText(/residente de un Estado/)).toBeInTheDocument();
    // Lo que el convenio no resuelve tampoco se insinúa.
    expect(screen.getByText(/No sustituye a la ley interna de Uruguay/)).toBeInTheDocument();
  });

  it('no arrastra el convenio del país anterior al navegar', async () => {
    // La SPA reutiliza el componente entre rutas de país. Publicar el
    // articulado de un convenio bajo el nombre de otra jurisdicción es un error
    // jurídico, no un parpadeo: al cambiar de país se reinicia la ficha.
    const { rerender } = renderCountry('/uruguay');
    expect(await screen.findByText(/residente de un Estado/)).toBeInTheDocument();

    rerender(
      <MemoryRouter initialEntries={['/chile']}>
        <CountryPage country={countryByPath('/chile')} />
      </MemoryRouter>
    );

    expect(screen.queryByText(/residente de un Estado/)).not.toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: /Convenio de doble imposición España–Chile/ })
    ).toBeInTheDocument();
  });

  it('recupera el convenio precargado al volver a su página', async () => {
    // El HTML prerenderizado trae el convenio de esa página embebido. Al
    // navegar a otro país y volver, el estado del componente ya es el del
    // segundo: hay que resembrarlo desde la precarga o `/uruguay` acabaría
    // publicando el articulado de `/chile`.
    const preload = {
      [URUGUAY.entry.boeId]: URUGUAY,
    };
    const renderConPreload = (path: string) =>
      render(
        <TreatyPreloadContext.Provider value={preload}>
          <MemoryRouter initialEntries={[path]}>
            <CountryPage country={countryByPath(path)} />
          </MemoryRouter>
        </TreatyPreloadContext.Provider>
      );

    const { rerender } = renderConPreload('/uruguay');
    expect(await screen.findByText(/residente de un Estado/)).toBeInTheDocument();

    rerender(
      <TreatyPreloadContext.Provider value={preload}>
        <MemoryRouter initialEntries={['/chile']}>
          <CountryPage country={countryByPath('/chile')} />
        </MemoryRouter>
      </TreatyPreloadContext.Provider>
    );
    expect(
      await screen.findByRole('heading', { name: /Convenio de doble imposición España–Chile/ })
    ).toBeInTheDocument();

    rerender(
      <TreatyPreloadContext.Provider value={preload}>
        <MemoryRouter initialEntries={['/uruguay']}>
          <CountryPage country={countryByPath('/uruguay')} />
        </MemoryRouter>
      </TreatyPreloadContext.Provider>
    );

    expect(
      await screen.findByRole('heading', { name: /Convenio de doble imposición España–Uruguay/ })
    ).toBeInTheDocument();
    expect(screen.getByText(URUGUAY.entry.norma)).toBeInTheDocument();
  });

  it('avisa en vez de quedarse cargando si el corpus normativo no responde', async () => {
    // `loadNormativa()` degrada a lista vacía a propósito, así que «no está» y
    // «todavía no ha llegado» tienen que ser estados distintos.
    vi.mocked(loadNormativa).mockResolvedValueOnce([]);
    renderCountry('/uruguay');

    expect(await screen.findByText(/No se ha podido cargar el convenio/)).toBeInTheDocument();
    expect(screen.queryByText('Cargando el convenio…')).not.toBeInTheDocument();
  });

  it('dice que no hay convenio cuando España no lo tiene con ese país', () => {
    renderCountry('/peru');

    expect(screen.getByText(/no tienen convenio/i)).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: /relación oficial de convenios firmados por España/ })
    ).toHaveAttribute('href', expect.stringContaining('agenciatributaria.gob.es'));
    expect(
      screen.queryByRole('link', { name: /Texto oficial del convenio en el BOE/ })
    ).not.toBeInTheDocument();
  });

  it('marca por falta de corpus, no por una fecha prometida', () => {
    renderCountry('/uruguay');

    expect(screen.getByRole('link', { name: 'Uruguay' })).toHaveAttribute('aria-current', 'page');
    const pendientes = COUNTRY_ROUTES.filter((route) => route.corpusStatus === 'pending');
    expect(screen.getAllByText('Sin corpus')).toHaveLength(pendientes.length);
    expect(screen.queryByText('Próximamente')).not.toBeInTheDocument();
  });
});
