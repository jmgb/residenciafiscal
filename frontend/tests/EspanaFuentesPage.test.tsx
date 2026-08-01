import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Link, MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { EspanaFuentesPage } from '@/pages/EspanaFuentesPage';

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
      <Link to='/espana/fuentes#corpus'>ir al corpus</Link>
      <Routes>
        <Route path='/espana/fuentes' element={<EspanaFuentesPage />} />
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

describe('EspanaFuentesPage', () => {
  it('distingue las fuentes del corpus v3 validado', () => {
    renderPage(['/espana/fuentes']);
    expect(screen.getByRole('heading', { name: 'Fuentes y corpus validado' })).toBeInTheDocument();
    expect(
      screen.getByText('106 resoluciones judiciales españolas conservadas como fuentes.')
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        '106 sentencias estructuradas con validación técnica; 67 aportan unidades recuperables.'
      )
    ).toBeInTheDocument();
    expect(screen.getByText(/revisión jurídica es del agente/i)).toBeInTheDocument();
  });

  it('publica la normativa aplicada de España', () => {
    renderPage(['/espana/fuentes']);
    expect(screen.getByRole('heading', { name: 'Normativa aplicada' })).toBeInTheDocument();
  });

  it('enlaza con la metodología común del proyecto', () => {
    renderPage(['/espana/fuentes']);
    const link = screen.getByRole('link', { name: /metodología/i });
    expect(link).toHaveAttribute('href', '/metodologia');
  });

  it('sin hash no desplaza nada', () => {
    renderPage(['/espana/fuentes']);
    expect(calls).toHaveLength(0);
  });

  it('con #corpus desplaza hasta la sección del corpus', () => {
    renderPage(['/espana/fuentes#corpus']);

    expect(calls).toHaveLength(1);
    expect(calls[0].target).toBe(document.getElementById('corpus'));
    expect(calls[0].options).toMatchObject({ block: 'start' });
  });

  it('con #normativa desplaza hasta la sección de normativa', () => {
    renderPage(['/espana/fuentes#normativa']);

    expect(calls).toHaveLength(1);
    expect(calls[0].target).toBe(document.getElementById('normativa'));
  });

  it('un hash que no existe no rompe la página', () => {
    renderPage(['/espana/fuentes#no-existe']);
    expect(calls).toHaveLength(0);
    expect(screen.getByRole('heading', { name: 'El corpus de España' })).toBeInTheDocument();
  });

  it('desplaza también cuando el hash cambia sin recargar', async () => {
    const user = userEvent.setup();
    renderPage(['/espana/fuentes']);
    expect(calls).toHaveLength(0);

    await user.click(screen.getByRole('link', { name: 'ir al corpus' }));

    expect(calls).toHaveLength(1);
    expect(calls[0].target).toBe(document.getElementById('corpus'));
  });

  it('usa scroll suave por defecto', () => {
    renderPage(['/espana/fuentes#corpus']);
    expect(calls[0].options).toMatchObject({ behavior: 'smooth' });
  });

  it('respeta prefers-reduced-motion', () => {
    stubReducedMotion(true);
    renderPage(['/espana/fuentes#corpus']);
    expect(calls[0].options).toMatchObject({ behavior: 'auto' });
  });
});
