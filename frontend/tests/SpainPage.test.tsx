import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { SpainPage } from '@/pages/SpainPage';

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/españa']}>
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
    expect(screen.getByText(/106 sentencias del Tribunal Supremo/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /183 días/ })).toBeInTheDocument();
  });

  it('mantiene el aviso del motor simulado de la home', () => {
    renderPage();

    expect(screen.getByRole('status', { name: 'Aviso: motor simulado' })).toBeInTheDocument();
  });
});
