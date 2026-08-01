import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router';
import { describe, expect, it } from 'vitest';
import { App } from '@/App';

function LocationProbe() {
  const location = useLocation();
  return <div data-testid='location'>{location.pathname}</div>;
}

/** URLs que el sitemap ofrece a indexación, leídas del artefacto publicado. */
const SITEMAP_LOCATIONS = [
  ...readFileSync(join(__dirname, '..', 'public', 'sitemap.xml'), 'utf8').matchAll(
    /<loc>([^<]+)<\/loc>/g
  ),
].map((match) => match[1]);

async function renderAndReadCanonical(path: string) {
  const canonical = document.createElement('link');
  canonical.setAttribute('rel', 'canonical');
  canonical.setAttribute('href', 'https://residenciafiscal.org/');
  document.head.appendChild(canonical);

  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>
  );
  await screen.findByTestId('chat-welcome');
  return canonical.getAttribute('href');
}

describe('App', () => {
  it('redirige la home a la página de España', async () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <LocationProbe />
        <App />
      </MemoryRouter>
    );

    expect(await screen.findByTestId('chat-welcome')).toBeInTheDocument();
    expect(screen.getByTestId('location')).toHaveTextContent('/espana');
  });

  it('redirige la ruta acentuada de España a su slug canónico', async () => {
    render(
      <MemoryRouter initialEntries={['/espa%C3%B1a']}>
        <LocationProbe />
        <App />
      </MemoryRouter>
    );

    expect(await screen.findByTestId('chat-welcome')).toBeInTheDocument();
    expect(screen.getByTestId('location')).toHaveTextContent('/espana');
  });

  it('sirve el corpus de España en /espana/fuentes', async () => {
    render(
      <MemoryRouter initialEntries={['/espana/fuentes']}>
        <LocationProbe />
        <App />
      </MemoryRouter>
    );

    expect(await screen.findByRole('heading', { name: 'El corpus de España' })).toBeInTheDocument();
    expect(screen.getByTestId('location')).toHaveTextContent('/espana/fuentes');
  });

  it.each(['/consulta', '/c/conversacion-de-prueba'])(
    'canonicaliza %s a la URL que sí publica el sitemap',
    async (path) => {
      const canonical = await renderAndReadCanonical(path);

      // Sirven el mismo chat que `/espana`: si se autocanonicalizaran, el sitio
      // ofrecería a indexación dos URLs con contenido idéntico.
      expect(canonical).toBe('https://residenciafiscal.org/espana');
      expect(SITEMAP_LOCATIONS).toContain(canonical);
    }
  );

  it('redirige la ruta acentuada de Perú a su slug canónico', async () => {
    render(
      <MemoryRouter initialEntries={['/per%C3%BA']}>
        <LocationProbe />
        <App />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('location')).toHaveTextContent('/peru');
    });
  });
});
