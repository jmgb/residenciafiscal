import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { CONTACT_EMAIL, EXPERT_PROFILES } from '@/lib/contribution';
import { ColaborarPage } from '@/pages/ColaborarPage';

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/colaborar']}>
      <ColaborarPage />
    </MemoryRouter>
  );
}

describe('ColaborarPage', () => {
  it('explica que el proyecto se nutre de la contribución de expertos', () => {
    renderPage();

    expect(screen.getByRole('heading', { level: 1, name: /Colaborar/ })).toBeInTheDocument();
    expect(
      screen.getByText(/expertos en fiscalidad y tributación internacional/i)
    ).toBeInTheDocument();
    // El corpus español se presenta como trabajo cualificado, no como una
    // recopilación que hizo cualquiera.
    expect(screen.getByText(/criterio jurídico-tributario/i)).toBeInTheDocument();
  });

  it('enumera los perfiles de experto que pueden colaborar', () => {
    renderPage();

    const perfiles = screen.getByRole('list', { name: 'Perfiles que pueden colaborar' });
    expect(perfiles).toBeInTheDocument();
    for (const profile of EXPERT_PROFILES) {
      expect(screen.getByText(profile.title)).toBeInTheDocument();
    }
  });

  it('ofrece los dos canales, GitHub y correo', () => {
    renderPage();

    expect(screen.getByRole('link', { name: /Proponer un país/ })).toHaveAttribute(
      'href',
      expect.stringContaining('template=aportar_pais.yml')
    );
    expect(screen.getByRole('link', { name: new RegExp(CONTACT_EMAIL) })).toHaveAttribute(
      'href',
      expect.stringContaining(`mailto:${CONTACT_EMAIL}`)
    );
  });

  it('dice qué pasa después de proponer un país y con qué criterio', () => {
    renderPage();

    expect(screen.getByRole('heading', { name: /Qué pasa cuando propones un país/ })).toBeVisible();
    expect(screen.getByText(/fuente reutilizable y un revisor comprometido/i)).toBeInTheDocument();
  });

  it('mantiene los invariantes del corpus a la vista', () => {
    renderPage();

    expect(screen.getByText(/no se reescribe/i)).toBeInTheDocument();
    expect(screen.getByText(/aislado/i)).toBeInTheDocument();
    expect(screen.getByText(/validación de un especialista/i)).toBeInTheDocument();
  });

  it('es indexable, al contrario que las páginas de país sin corpus', async () => {
    // El `afterEach` global vacía el head, así que las etiquetas se siembran aquí.
    const robots = document.createElement('meta');
    robots.setAttribute('name', 'robots');
    robots.setAttribute('content', 'noindex, follow');
    const canonical = document.createElement('link');
    canonical.setAttribute('rel', 'canonical');
    canonical.setAttribute('href', 'https://residenciafiscal.org/');
    document.head.append(robots, canonical);

    renderPage();

    await waitFor(() => {
      expect(document.querySelector('meta[name="robots"]')).toHaveAttribute(
        'content',
        'index, follow'
      );
      expect(document.querySelector('link[rel="canonical"]')).toHaveAttribute(
        'href',
        'https://residenciafiscal.org/colaborar'
      );
    });
  });
});
