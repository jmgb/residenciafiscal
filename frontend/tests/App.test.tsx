import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router';
import { describe, expect, it } from 'vitest';
import { App } from '@/App';

function LocationProbe() {
  const location = useLocation();
  return <div data-testid='location'>{location.pathname}</div>;
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
