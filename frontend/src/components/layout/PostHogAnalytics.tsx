import { useEffect } from 'react';
import { useLocation } from 'react-router';
import { isGoogleAnalyticsEnabled } from './GoogleAnalytics';

/** Proyecto «Residencia Fiscal» (237205) en la organización europea de PostHog. */
export const POSTHOG_PROJECT_API_KEY = 'phc_AtzZdHURMtdxTrP9sCNM5jEuQQ2T5dvvudWoE6ohbG4f';
export const POSTHOG_HOST = 'https://eu.i.posthog.com';

const POSTHOG_SCRIPT_ID = 'posthog-script';
const POSTHOG_SCRIPT_SRC = `${POSTHOG_HOST}/static/array.js`;

type PostHogClient = {
  init: (apiKey: string, options: Record<string, unknown>) => void;
  capture: (event: string, properties?: Record<string, unknown>) => void;
  identify: (distinctId: string, properties?: Record<string, unknown>) => void;
};

declare global {
  interface Window {
    posthog?: Partial<PostHogClient> & { _pendiente?: [string, unknown[]][] };
    __residenciaFiscalPostHogInitialized?: boolean;
  }
}

/**
 * PostHog usa exactamente el mismo criterio que GA4: solo hosts canónicos de
 * producción y nunca las visitas del monitor sintético. Reutilizamos la función
 * en lugar de duplicar la lista para que no puedan divergir.
 */
export const isPostHogEnabled = isGoogleAnalyticsEnabled;

/**
 * Cola mínima equivalente al snippet oficial: permite llamar a `capture` antes
 * de que el script real termine de descargarse sin perder el evento.
 */
const createPostHogStub = () => {
  const pendiente: [string, unknown[]][] = [];
  const stub: Window['posthog'] = {
    _pendiente: pendiente,
    capture: (...args: unknown[]) => pendiente.push(['capture', args]),
    identify: (...args: unknown[]) => pendiente.push(['identify', args]),
  } as Window['posthog'];
  return stub;
};

const installPostHog = () => {
  if (!isPostHogEnabled(window.location)) return;
  if (document.getElementById(POSTHOG_SCRIPT_ID)) return;

  window.posthog = window.posthog ?? createPostHogStub();

  const script = document.createElement('script');
  script.id = POSTHOG_SCRIPT_ID;
  script.async = true;
  script.src = POSTHOG_SCRIPT_SRC;
  script.addEventListener('load', () => {
    if (window.__residenciaFiscalPostHogInitialized) return;
    const pendiente = window.posthog?._pendiente ?? [];
    window.posthog?.init?.(POSTHOG_PROJECT_API_KEY, {
      api_host: POSTHOG_HOST,
      person_profiles: 'identified_only',
      // La SPA controla sus propias vistas: el pageview automático de PostHog
      // solo vería la carga inicial y perdería toda navegación por rutas.
      capture_pageview: false,
      capture_pageleave: true,
    });
    window.__residenciaFiscalPostHogInitialized = true;
    for (const [metodo, args] of pendiente) {
      const fn = window.posthog?.[metodo as 'capture' | 'identify'];
      (fn as ((...a: unknown[]) => void) | undefined)?.(...args);
    }
  });
  document.head.appendChild(script);
};

/** Registra un evento de producto; no hace nada fuera de producción. */
export const trackEvent = (event: string, properties?: Record<string, unknown>) => {
  if (typeof window === 'undefined') return;
  if (!isPostHogEnabled(window.location)) return;
  window.posthog?.capture?.(event, properties);
};

/** Instala PostHog una vez y registra cada cambio de ruta de la SPA. */
export const PostHogAnalytics = () => {
  const location = useLocation();

  useEffect(() => {
    installPostHog();
  }, []);

  useEffect(() => {
    if (!isPostHogEnabled(window.location)) return;

    const pagePath = `${location.pathname}${location.search}${location.hash}`;
    // La primera vista también se registra aquí, porque desactivamos el
    // pageview automático del SDK.
    window.posthog?.capture?.('$pageview', {
      $current_url: `${window.location.origin}${pagePath}`,
      page_title: document.title,
    });
  }, [location.hash, location.pathname, location.search]);

  return null;
};
