import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { SpainPage } from '@/pages/SpainPage';

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/espana']}>
      <SpainPage />
    </MemoryRouter>
  );
}

describe('SpainPage', () => {
  it('conserva literalmente la experiencia de consulta que estaba en la home', () => {
    renderPage();

    expect(screen.getByTestId('chat-welcome')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', {
        name: 'Decide tu fiscalidad con las sentencias en la mano',
      })
    ).toBeInTheDocument();
    expect(screen.getByText(/Modelo de IA entrenado con 106 sentencias/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /183 días/ })).toBeInTheDocument();
  });

  it('no muestra la banda de aviso del motor simulado en la home', () => {
    renderPage();

    expect(screen.queryByRole('status', { name: 'Aviso: motor simulado' })).not.toBeInTheDocument();
    expect(screen.queryByText(/está activo el motor simulado/i)).not.toBeInTheDocument();
  });

  it('publica bajo el chat la sección estática con los criterios del art. 9 LIRPF', () => {
    renderPage();

    const section = screen.getByRole('region', {
      name: 'La residencia fiscal en España: qué dice el art. 9 LIRPF',
    });

    for (const heading of [
      'Permanencia de más de 183 días',
      'Núcleo principal de los intereses económicos',
      'Presunción familiar',
      'Convenios de doble imposición',
      'Qué contiene este corpus',
    ]) {
      expect(within(section).getByRole('heading', { name: heading })).toBeInTheDocument();
    }
  });

  it('la sección estática enlaza a las fuentes, la metodología y el BOE', () => {
    renderPage();

    const section = screen.getByRole('region', {
      name: 'La residencia fiscal en España: qué dice el art. 9 LIRPF',
    });

    expect(
      within(section).getByRole('link', { name: 'Fuentes y normativa del corpus' })
    ).toHaveAttribute('href', '/espana/fuentes');
    expect(
      within(section).getByRole('link', { name: 'Cómo se construye el análisis' })
    ).toHaveAttribute('href', '/metodologia');
    expect(within(section).getByRole('link', { name: 'Art. 9 LIRPF en el BOE' })).toHaveAttribute(
      'href',
      'https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764#a9'
    );
  });

  it('la sección estática mantiene el registro honesto sobre la revisión', () => {
    renderPage();

    const section = screen.getByRole('region', {
      name: 'La residencia fiscal en España: qué dice el art. 9 LIRPF',
    });

    expect(within(section).getByText(/no una aprobación humana/)).toBeInTheDocument();
    expect(within(section).getByText(/no constituye asesoramiento jurídico/)).toBeInTheDocument();
  });

  it('fija el título específico de España, el mismo que escribe el prerender', () => {
    renderPage();

    expect(document.title).toBe('Residencia fiscal en España: jurisprudencia del art. 9 LIRPF');
  });

  it('no muestra el bloque de marco jurídico en la bienvenida', () => {
    renderPage();

    expect(screen.queryByRole('region', { name: 'Marco jurídico' })).not.toBeInTheDocument();
    expect(screen.queryByText('Art. 9 LIRPF')).not.toBeInTheDocument();
    expect(
      screen.queryByText('Ley 35/2006 del Impuesto sobre la Renta de las Personas Físicas')
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/Fuente oficial · Revisada el/)).not.toBeInTheDocument();
  });
});
