import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { staticRoute } from '@/data/staticRoutes';
import { PrivacyPage } from '@/pages/PrivacyPage';

describe('PrivacyPage', () => {
  it('explica el recorrido real del chat y sus dos proveedores', () => {
    render(
      <MemoryRouter>
        <PrivacyPage />
      </MemoryRouter>
    );

    expect(screen.getByText(/OpenAI/i)).toBeInTheDocument();
    expect(screen.getByText(/Google Gemini/i)).toBeInTheDocument();
    expect(
      screen.getByText(/no guarda la pregunta, la respuesta ni las citas/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/navegador.*localStorage/i)).toBeInTheDocument();
  });

  it('no publica el pendiente legal interno en la página', () => {
    render(
      <MemoryRouter>
        <PrivacyPage />
      </MemoryRouter>
    );

    expect(screen.queryByText(/identidad legal del responsable/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/cerrado por configuración/i)).not.toBeInTheDocument();
  });

  it('mantiene la descripción canónica y noindex después de hidratar', () => {
    document.head.innerHTML = '<meta name="description"><meta name="robots">';
    const metadata = staticRoute('/privacidad');

    render(
      <MemoryRouter>
        <PrivacyPage />
      </MemoryRouter>
    );

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
