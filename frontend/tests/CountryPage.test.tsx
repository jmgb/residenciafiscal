import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { COUNTRY_ROUTES, type CountryRoute } from '@/data/countryRoutes';
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
      screen.getByRole('heading', { name: /Argentina lo puede abrir cualquiera/ })
    ).toBeInTheDocument();
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

  it('enumera las tres aportaciones que necesita un país nuevo', () => {
    renderCountry('/chile');

    const requisitos = screen.getByRole('list', { name: 'Qué necesita un país nuevo' });
    expect(requisitos).toBeInTheDocument();
    expect(screen.getByText(/fuente pública oficial/i)).toBeInTheDocument();
    expect(screen.getByText(/equivalente al art\. 9 LIRPF/i)).toBeInTheDocument();
    expect(screen.getByText(/revise que el análisis/i)).toBeInTheDocument();
  });

  it('no afirma que ya exista corpus del país ni ofrece consulta', () => {
    renderCountry('/brasil');

    expect(screen.getByText(/todavía no hay jurisprudencia de Brasil en el corpus/i)).toBeVisible();
    expect(screen.queryByTestId('chat-welcome')).not.toBeInTheDocument();
  });

  it('marca por falta de corpus, no por una fecha prometida', () => {
    renderCountry('/uruguay');

    expect(screen.getByRole('link', { name: 'Uruguay' })).toHaveAttribute('aria-current', 'page');
    // Se cuenta desde `indexable` para no fijar aquí ni el slug ni qué país está
    // publicado: la etiqueta la merece todo país cuyo corpus aún no existe.
    const pendientes = COUNTRY_ROUTES.filter((route) => !route.indexable);
    expect(screen.getAllByText('Sin corpus')).toHaveLength(pendientes.length);
    expect(screen.queryByText('Próximamente')).not.toBeInTheDocument();
  });
});
