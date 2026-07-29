import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { SidebarNavigation } from '@/components/layout/SidebarContent';

describe('CountryNavigation', () => {
  it('marca España como activa cuando la ruta contiene la ñ codificada', () => {
    render(
      <MemoryRouter initialEntries={['/espa%C3%B1a']}>
        <SidebarNavigation />
      </MemoryRouter>
    );

    expect(screen.getByRole('link', { name: 'España' })).toHaveAttribute('aria-current', 'page');
  });
});
