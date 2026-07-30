import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useScrollTopOnLoad } from '@/lib/useScrollTopOnLoad';

function Pagina() {
  const scrollRef = useScrollTopOnLoad<HTMLDivElement>();
  return (
    <div ref={scrollRef} data-testid='scroller'>
      contenido
    </div>
  );
}

// El hook desplaza dentro de un rAF para dejar que el navegador restaure antes
// su posición de scroll; aquí se capturan los frames y se ejecutan a mano para
// poder simular esa restauración entre el montaje y el desplazamiento.
let frames: FrameRequestCallback[] = [];

interface ScrollToCall {
  options: ScrollToOptions | undefined;
}

function renderPagina(initialEntries: string[]) {
  const utils = render(
    <MemoryRouter initialEntries={initialEntries}>
      <Pagina />
    </MemoryRouter>
  );
  const scroller = utils.getByTestId('scroller');
  // jsdom no implementa `scrollTo` en elementos: se instala un doble que anota
  // las opciones, igual que haría el navegador real.
  const calls: ScrollToCall[] = [];
  Object.defineProperty(scroller, 'scrollTo', {
    configurable: true,
    value: (options?: ScrollToOptions) => {
      calls.push({ options });
    },
  });
  return { scroller, calls };
}

function flushFrames() {
  const pending = frames;
  frames = [];
  for (const frame of pending) frame(0);
}

function stubReducedMotion(matches: boolean) {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: (query: string) => ({ matches, media: query }),
  });
}

beforeEach(() => {
  frames = [];
  vi.spyOn(window, 'requestAnimationFrame').mockImplementation((callback) => {
    frames.push(callback);
    return frames.length;
  });
});

afterEach(() => {
  vi.restoreAllMocks();
  Reflect.deleteProperty(window, 'matchMedia');
});

describe('useScrollTopOnLoad', () => {
  it('desplaza suavemente hasta arriba al cargar la página', () => {
    const { scroller, calls } = renderPagina(['/manifiesto']);
    // El navegador restaura una posición previa antes del primer frame.
    scroller.scrollTop = 640;

    flushFrames();

    expect(calls).toHaveLength(1);
    expect(calls[0].options).toMatchObject({ top: 0, behavior: 'smooth' });
  });

  it('respeta prefers-reduced-motion con un desplazamiento instantáneo', () => {
    stubReducedMotion(true);
    const { calls } = renderPagina(['/manifiesto']);

    flushFrames();

    expect(calls[0].options).toMatchObject({ top: 0, behavior: 'auto' });
  });

  it('no desplaza cuando la URL trae un ancla: el destino lo decide el hash', () => {
    const { calls } = renderPagina(['/metodologia#corpus']);

    flushFrames();

    expect(calls).toHaveLength(0);
  });

  it('sin scrollTo (jsdom) cae al reset directo de scrollTop', () => {
    const utils = render(
      <MemoryRouter initialEntries={['/manifiesto']}>
        <Pagina />
      </MemoryRouter>
    );
    const scroller = utils.getByTestId('scroller');
    scroller.scrollTop = 320;

    flushFrames();

    expect(scroller.scrollTop).toBe(0);
  });
});
