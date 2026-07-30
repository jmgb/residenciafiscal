import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { SidebarFooter } from '@/components/layout/SidebarContent';
import { CONTACT_EMAIL } from '@/lib/contribution';

function renderFooter(collapsed = false) {
  return render(
    <MemoryRouter>
      <SidebarFooter collapsed={collapsed} />
    </MemoryRouter>
  );
}

describe('SidebarFooter', () => {
  it('muestra el email completo como último elemento del menú lateral', () => {
    renderFooter();

    const links = screen.getAllByRole('link');
    expect(links.at(-1)).toHaveAccessibleName(CONTACT_EMAIL);
    expect(links.at(-1)).toHaveAttribute('href', `mailto:${CONTACT_EMAIL}`);
  });

  it('mantiene el email completo como último elemento al plegar el menú lateral', () => {
    renderFooter(true);

    const links = screen.getAllByRole('link');
    expect(links.at(-1)).toHaveAccessibleName(CONTACT_EMAIL);
    expect(links.at(-1)).toHaveAttribute('href', `mailto:${CONTACT_EMAIL}`);
  });
});
