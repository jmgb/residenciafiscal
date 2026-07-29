import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Link, MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { MetodologiaPage } from '@/pages/MetodologiaPage';

interface ScrollCall {
  target: Element;
  options: boolean | ScrollIntoViewOptions | undefined;
}

const originalScrollIntoView = Element.prototype.scrollIntoView;
let calls: ScrollCall[] = [];

beforeEach(() => {
  calls = [];
  // jsdom no implementa `scrollIntoView`; se instala un doble que anota el destino.
  Element.prototype.scrollIntoView = function scrollIntoView(
    this: Element,
    options?: boolean | ScrollIntoViewOptions
  ) {
    calls.push({ target: this, options });
  };
});

afterEach(() => {
  Element.prototype.scrollIntoView = originalScrollIntoView;
  Reflect.deleteProperty(window, 'matchMedia');
});

function renderPage(initialEntries: string[]) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Link to='/metodologia#corpus'>ir al corpus</Link>
      <Routes>
        <Route path='/metodologia' element={<MetodologiaPage />} />
      </Routes>
    </MemoryRouter>
  );
}

function stubReducedMotion(matches: boolean) {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: (query: string) => ({ matches, media: query }),
  });
}

describe('MetodologiaPage', () => {
  it('renderiza el corpus analizado', () => {
    renderPage(['/metodologia']);
    expect(screen.getByRole('heading', { name: 'Corpus analizado' })).toBeInTheDocument();
    expect(screen.getByText('106 resoluciones judiciales españolas.')).toBeInTheDocument();
  });

  it('sin hash no desplaza nada', () => {
    renderPage(['/metodologia']);
    expect(calls).toHaveLength(0);
  });

  it('con /metodologia#corpus desplaza hasta la sección del corpus', () => {
    renderPage(['/metodologia#corpus']);

    expect(calls).toHaveLength(1);
    expect(calls[0].target).toBe(document.getElementById('corpus'));
    expect(calls[0].options).toMatchObject({ block: 'start' });
  });

  it('un hash que no existe no rompe la página', () => {
    renderPage(['/metodologia#no-existe']);
    expect(calls).toHaveLength(0);
    expect(screen.getByRole('heading', { name: 'Metodología' })).toBeInTheDocument();
  });

  it('desplaza también cuando el hash cambia sin recargar', async () => {
    const user = userEvent.setup();
    renderPage(['/metodologia']);
    expect(calls).toHaveLength(0);

    await user.click(screen.getByRole('link', { name: 'ir al corpus' }));

    expect(calls).toHaveLength(1);
    expect(calls[0].target).toBe(document.getElementById('corpus'));
  });

  it('usa scroll suave por defecto', () => {
    renderPage(['/metodologia#corpus']);
    expect(calls[0].options).toMatchObject({ behavior: 'smooth' });
  });

  it('respeta prefers-reduced-motion', () => {
    stubReducedMotion(true);
    renderPage(['/metodologia#corpus']);
    expect(calls[0].options).toMatchObject({ behavior: 'auto' });
  });
});
