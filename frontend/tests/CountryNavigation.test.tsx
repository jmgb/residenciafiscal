import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { SidebarNavigation } from '@/components/layout/SidebarContent';

describe('CountryNavigation', () => {
  it.each(['/francia', '/francia/convenios/espana'])(
    'mantiene visible el país activo al entrar en %s',
    (route) => {
      render(
        <MemoryRouter initialEntries={[route]}>
          <SidebarNavigation />
        </MemoryRouter>
      );

      const countries = within(screen.getByRole('navigation', { name: 'Países' }));
      expect(countries.getByRole('link', { name: 'Francia' })).toHaveAttribute(
        'aria-current',
        'page'
      );
      expect(countries.getAllByRole('link')).toHaveLength(4);
      expect(countries.getByRole('button', { name: 'Mostrar más' })).toBeInTheDocument();
    }
  );

  it('actualiza el país visible al navegar sin desplegar todos', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={['/francia']}>
        <SidebarNavigation />
      </MemoryRouter>
    );

    expect(screen.getByRole('link', { name: 'Francia' })).toHaveAttribute('aria-current', 'page');
    await user.click(screen.getByRole('link', { name: 'Portugal' }));

    expect(screen.getByRole('link', { name: 'Portugal' })).toHaveAttribute('aria-current', 'page');
    expect(screen.queryByRole('link', { name: 'Francia' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Mostrar más' })).toBeInTheDocument();
  });

  it('muestra tres países y despliega el resto con Mostrar más', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={['/espana']}>
        <SidebarNavigation />
      </MemoryRouter>
    );

    expect(screen.getByRole('link', { name: 'España' })).toHaveAttribute('href', '/espana');
    expect(screen.getByRole('link', { name: 'Estados Unidos' })).toHaveAttribute(
      'href',
      '/estados-unidos'
    );
    expect(screen.getByRole('link', { name: 'Portugal' })).toHaveAttribute('href', '/portugal');
    expect(screen.queryByRole('link', { name: 'Francia' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Mostrar más' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Mostrar más' }));

    expect(screen.getByRole('link', { name: 'Francia' })).toHaveAttribute('href', '/francia');
    expect(screen.getByRole('link', { name: 'Reino Unido' })).toHaveAttribute(
      'href',
      '/reino-unido'
    );
    expect(screen.getByRole('link', { name: 'México' })).toHaveAttribute('href', '/mexico');
    expect(screen.getByRole('link', { name: 'Brasil' })).toHaveAttribute('href', '/brasil');
    expect(screen.getByRole('link', { name: 'Perú' })).toHaveAttribute('href', '/peru');
    expect(screen.queryByRole('button', { name: 'Mostrar más' })).not.toBeInTheDocument();
  });
});
