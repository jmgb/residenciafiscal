import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { MetodologiaPage } from '@/pages/MetodologiaPage';

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/metodologia']}>
      <MetodologiaPage />
    </MemoryRouter>
  );
}

describe('MetodologiaPage', () => {
  it('explica el método común a todas las jurisdicciones', () => {
    renderPage();
    expect(
      screen.getByRole('heading', { name: 'Cómo se construye el análisis' })
    ).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Limitaciones' })).toBeInTheDocument();
  });

  it('no contiene las fuentes de España: viven en su página de país', () => {
    renderPage();
    expect(
      screen.queryByRole('heading', { name: 'Fuentes y corpus validado' })
    ).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Normativa aplicada' })).not.toBeInTheDocument();
  });

  it('enlaza con el corpus de España', () => {
    renderPage();
    const link = screen.getByRole('link', { name: /corpus de españa/i });
    expect(link).toHaveAttribute('href', '/espana/fuentes');
  });
});
