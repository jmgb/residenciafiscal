import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { staticRoute } from '@/data/staticRoutes';
import { PrivacyPage } from '@/pages/PrivacyPage';

const renderPage = () =>
  render(
    <MemoryRouter>
      <PrivacyPage />
    </MemoryRouter>
  );

describe('PrivacyPage', () => {
  it('identifica al responsable del tratamiento', () => {
    renderPage();

    expect(screen.getByText(/Intangible Land LLC/)).toBeInTheDocument();
    expect(screen.getByText(/92-2584862/)).toBeInTheDocument();
    expect(
      screen.getByText(/Brickell Dr #1111, Miami, FL \(33131\), Estados Unidos/)
    ).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: 'info@residenciafiscal.org' })[0]).toHaveAttribute(
      'href',
      'mailto:info@residenciafiscal.org'
    );
  });

  it('explica el recorrido real del chat y sus dos proveedores', () => {
    renderPage();

    expect(screen.getByText(/fragmentos estructurados de 106 sentencias/i)).toBeInTheDocument();
    expect(screen.getByText(/File Search Store de esos 106 PDF/i)).toBeInTheDocument();
    expect(
      screen.getByText(/guarda en Supabase la pregunta y las dos respuestas/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/modelo, tokens, coste, duración y citas/i)).toBeInTheDocument();
    expect(screen.getByText(/navegador mediante localStorage/i)).toBeInTheDocument();
  });

  it('declara base jurídica, encargados, transferencias y plazo de conservación', () => {
    renderPage();

    expect(screen.getByText(/art\. 6\.1\.b RGPD/)).toBeInTheDocument();
    expect(screen.getAllByText(/art\. 6\.1\.f RGPD/).length).toBeGreaterThan(1);
    for (const provider of ['Netlify', 'Cloudflare', 'OpenAI', 'Supabase', 'Sentry', 'PostHog']) {
      expect(screen.getAllByText(provider, { exact: false }).length).toBeGreaterThan(0);
    }
    expect(screen.getByText(/Espacio Económico Europeo/)).toBeInTheDocument();
    expect(screen.getByText(/Preguntas y respuestas del chat: 15 días/)).toBeInTheDocument();
  });

  it('publica los derechos, la autoridad de control y la exclusión de analítica', () => {
    renderPage();

    expect(screen.getByText(/Portabilidad:/)).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: /Agencia Española de Protección de Datos/ })
    ).toHaveAttribute('href', 'https://www.aepd.es');
    expect(screen.getByRole('link', { name: /no_analytics=1/ })).toHaveAttribute(
      'href',
      '/?no_analytics=1'
    );
  });

  it('no publica el pendiente legal interno en la página', () => {
    renderPage();

    expect(screen.queryByText(/identidad legal del responsable/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/cerrado por configuración/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/pendiente de revisión jurídica/i)).not.toBeInTheDocument();
  });

  it('mantiene la descripción canónica y noindex después de hidratar', () => {
    document.head.innerHTML = '<meta name="description"><meta name="robots">';
    const metadata = staticRoute('/privacidad');

    renderPage();

    expect(document.querySelector('meta[name="description"]')).toHaveAttribute(
      'content',
      metadata.description
    );
    expect(document.querySelector('meta[name="robots"]')).toHaveAttribute(
      'content',
      'noindex, follow'
    );
  });
});
