import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { COUNTRY_ROUTES, type CountryRoute } from '@/data/countryRoutes';
import { CONTACT_EMAIL, EXPERT_PROFILES } from '@/lib/contribution';
import { CountryPage } from '@/pages/CountryPage';

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

  it('marca por falta de corpus, no por una fecha prometida', () => {
    renderCountry('/uruguay');

    expect(screen.getByRole('link', { name: 'Uruguay' })).toHaveAttribute('aria-current', 'page');
    const pendientes = COUNTRY_ROUTES.filter((route) => route.corpusStatus === 'pending');
    expect(screen.getAllByText('Sin corpus')).toHaveLength(pendientes.length);
    expect(screen.queryByText('Próximamente')).not.toBeInTheDocument();
  });
});
