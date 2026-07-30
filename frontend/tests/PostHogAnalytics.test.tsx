import { render, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  isPostHogEnabled,
  POSTHOG_HOST,
  POSTHOG_PROJECT_API_KEY,
  PostHogAnalytics,
  trackEvent,
} from '@/components/layout/PostHogAnalytics';

const setHostname = (hostname: string, search = '') => {
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: { ...window.location, hostname, search, origin: `https://${hostname}` },
  });
};

afterEach(() => {
  document.getElementById('posthog-script')?.remove();
  window.posthog = undefined;
  window.__residenciaFiscalPostHogInitialized = undefined;
  vi.restoreAllMocks();
});

describe('isPostHogEnabled', () => {
  it('aplica el mismo criterio que Google Analytics', () => {
    expect(isPostHogEnabled({ hostname: 'residenciafiscal.org', search: '' })).toBe(true);
    expect(isPostHogEnabled({ hostname: 'www.residenciafiscal.org', search: '' })).toBe(true);
    expect(
      isPostHogEnabled({ hostname: 'deploy-preview-12--residenciafiscal.netlify.app', search: '' })
    ).toBe(false);
    expect(isPostHogEnabled({ hostname: 'localhost', search: '' })).toBe(false);
  });

  it('ignora las visitas del monitor sintético', () => {
    expect(
      isPostHogEnabled({ hostname: 'residenciafiscal.org', search: '?synthetic_monitor=1' })
    ).toBe(false);
  });
});

describe('PostHogAnalytics', () => {
  it('no instala nada fuera de los hosts de producción', () => {
    setHostname('localhost');
    render(
      <MemoryRouter initialEntries={['/metodologia']}>
        <PostHogAnalytics />
      </MemoryRouter>
    );
    expect(document.getElementById('posthog-script')).toBeNull();
  });

  it('instala el script del proyecto europeo en producción', async () => {
    setHostname('residenciafiscal.org');
    render(
      <MemoryRouter initialEntries={['/metodologia']}>
        <PostHogAnalytics />
      </MemoryRouter>
    );

    await waitFor(() => {
      const script = document.getElementById('posthog-script') as HTMLScriptElement | null;
      expect(script?.src).toBe(`${POSTHOG_HOST}/static/array.js`);
    });
  });

  it('registra la vista inicial, porque el pageview automático está desactivado', async () => {
    setHostname('residenciafiscal.org');
    const capture = vi.fn();
    window.posthog = { capture };

    render(
      <MemoryRouter initialEntries={['/metodologia']}>
        <PostHogAnalytics />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(capture).toHaveBeenCalledWith('$pageview', expect.objectContaining({}));
    });
  });
});

describe('trackEvent', () => {
  it('no emite eventos fuera de producción', () => {
    setHostname('localhost');
    const capture = vi.fn();
    window.posthog = { capture };
    trackEvent('consulta_enviada', { pais: '/espana' });
    expect(capture).not.toHaveBeenCalled();
  });

  it('emite el evento con sus propiedades en producción', () => {
    setHostname('residenciafiscal.org');
    const capture = vi.fn();
    window.posthog = { capture };
    trackEvent('consulta_enviada', { pais: '/espana' });
    expect(capture).toHaveBeenCalledWith('consulta_enviada', { pais: '/espana' });
  });
});

describe('configuración del proyecto', () => {
  it('apunta al proyecto Residencia Fiscal en la región europea', () => {
    expect(POSTHOG_PROJECT_API_KEY).toBe('phc_AtzZdHURMtdxTrP9sCNM5jEuQQ2T5dvvudWoE6ohbG4f');
    expect(POSTHOG_HOST).toBe('https://eu.i.posthog.com');
  });
});
