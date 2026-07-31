import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';
import { VERSION_MANIFEST_PATH } from '@/lib/app-version';

/**
 * El guardián de versión consulta `/version.json` en cuanto se monta el shell.
 * Sin este corte, cualquier test que renderice el layout saldría a la red y su
 * resultado dependería de lo que hubiera publicado producción en ese momento.
 *
 * Es una sustitución directa, no un spy: los tests que hacen
 * `vi.restoreAllMocks()` no deben poder devolver la suite a la red sin querer.
 * Un test que quiera controlar la respuesta sigue pudiendo espiar `fetch`.
 */
const networkFetch = globalThis.fetch;
globalThis.fetch = ((input: RequestInfo | URL, init?: RequestInit) => {
  const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
  if (url.endsWith(VERSION_MANIFEST_PATH)) {
    return Promise.resolve(new Response('', { status: 404 }));
  }
  return networkFetch(input, init);
}) as typeof fetch;

afterEach(() => {
  cleanup();
  document.head.innerHTML = '';
  delete window.dataLayer;
  delete window.gtag;
  delete window.__residenciaFiscalGoogleAnalyticsInitialized;
});
