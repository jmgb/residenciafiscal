import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { SidebarNavigation } from '@/components/layout/SidebarContent';

describe('CountryNavigation', () => {
  it('muestra España y las rutas de países latinoamericanos en la barra lateral', () => {
    render(
      <MemoryRouter initialEntries={['/españa']}>
        <SidebarNavigation />
      </MemoryRouter>
    );

    expect(screen.getByRole('link', { name: 'España' })).toHaveAttribute('href', '/españa');
    expect(screen.getByRole('link', { name: 'México' })).toHaveAttribute('href', '/mexico');
    expect(screen.getByRole('link', { name: 'Argentina' })).toHaveAttribute('href', '/argentina');
    expect(screen.getByRole('link', { name: 'Brasil' })).toHaveAttribute('href', '/brasil');
    expect(screen.getByRole('link', { name: 'Perú' })).toHaveAttribute('href', '/peru');
  });
});
