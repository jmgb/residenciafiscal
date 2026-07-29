import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { SidebarNavigation } from '@/components/layout/SidebarContent';

describe('CountryNavigation', () => {
  it('muestra tres países y despliega el resto con Mostrar más', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={['/espana']}>
        <SidebarNavigation />
      </MemoryRouter>
    );

    expect(screen.getByRole('link', { name: 'España' })).toHaveAttribute('href', '/espana');
    expect(screen.getByRole('link', { name: 'Argentina' })).toHaveAttribute('href', '/argentina');
    expect(screen.getByRole('link', { name: 'Bolivia' })).toHaveAttribute('href', '/bolivia');
    expect(screen.queryByRole('link', { name: 'Brasil' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Mostrar más' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Mostrar más' }));

    expect(screen.getByRole('link', { name: 'México' })).toHaveAttribute('href', '/mexico');
    expect(screen.getByRole('link', { name: 'Brasil' })).toHaveAttribute('href', '/brasil');
    expect(screen.getByRole('link', { name: 'Perú' })).toHaveAttribute('href', '/peru');
    expect(screen.queryByRole('button', { name: 'Mostrar más' })).not.toBeInTheDocument();
  });
});
