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
      screen.getByRole('heading', { name: 'Consulta la jurisprudencia de residencia fiscal' })
    ).toBeInTheDocument();
    expect(screen.getByText(/muestra estructurada y validada de cinco/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /183 días/ })).toBeInTheDocument();
  });

  it('mantiene el aviso del motor simulado de la home', () => {
    renderPage();

    expect(screen.getByRole('status', { name: 'Aviso: motor simulado' })).toBeInTheDocument();
  });

  it('expone el marco jurídico con su fuente oficial y fecha de revisión', () => {
    renderPage();

    const framework = screen.getByRole('region', { name: 'Marco jurídico' });
    const officialSource = within(framework).getByRole('link', { name: 'Art. 9 LIRPF' });

    expect(officialSource).toHaveAttribute(
      'href',
      'https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764#a9'
    );
    expect(officialSource).toHaveAttribute('target', '_blank');
    expect(
      within(framework).getByText('Ley 35/2006 del Impuesto sobre la Renta de las Personas Físicas')
    ).toBeVisible();
    expect(framework).toHaveTextContent('Fuente oficial · Revisada el 30 de julio de 2026');
    expect(framework.querySelector('time')).toHaveAttribute('datetime', '2026-07-30');
  });
});
