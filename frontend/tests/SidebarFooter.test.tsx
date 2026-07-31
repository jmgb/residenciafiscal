import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { SidebarFooter } from '@/components/layout/SidebarContent';
import { CONTACT_EMAIL } from '@/lib/contribution';

function renderFooter({ collapsed = false, route = '/' } = {}) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <SidebarFooter collapsed={collapsed} />
    </MemoryRouter>
  );
}

describe('SidebarFooter', () => {
  it('con España activa enlaza su corpus, no la metodología', () => {
    renderFooter({ route: '/espana' });

    const corpusLink = screen.getByRole('link', { name: 'Corpus de España' });
    expect(corpusLink).toHaveAttribute('href', '/espana/fuentes');
    const hrefs = screen.getAllByRole('link').map((link) => link.getAttribute('href'));
    expect(hrefs).not.toContain('/metodologia#corpus');
  });

  it('mantiene el enlace al corpus dentro de la propia página de fuentes', () => {
    renderFooter({ route: '/espana/fuentes' });

    expect(screen.getByRole('link', { name: 'Corpus de España' })).toBeInTheDocument();
  });

  it('oculta el corpus con un país sin corpus seleccionado', () => {
    renderFooter({ route: '/portugal' });

    expect(screen.queryByRole('link', { name: /corpus de/i })).not.toBeInTheDocument();
  });

  it('oculta el corpus en las páginas sin jurisdicción', () => {
    renderFooter({ route: '/metodologia' });

    expect(screen.queryByRole('link', { name: /corpus de/i })).not.toBeInTheDocument();
  });

  it('muestra el email completo como último elemento del menú lateral', () => {
    renderFooter();

    const links = screen.getAllByRole('link');
    expect(links.at(-1)).toHaveAccessibleName(CONTACT_EMAIL);
    expect(links.at(-1)).toHaveAttribute('href', `mailto:${CONTACT_EMAIL}`);
  });

  it('mantiene el email completo como último elemento al plegar el menú lateral', () => {
    renderFooter({ collapsed: true });

    const links = screen.getAllByRole('link');
    expect(links.at(-1)).toHaveAccessibleName(CONTACT_EMAIL);
    expect(links.at(-1)).toHaveAttribute('href', `mailto:${CONTACT_EMAIL}`);
  });
});
