import { useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';

export const GOOGLE_ANALYTICS_ID = 'G-XKX3N9KVJH';

const GOOGLE_ANALYTICS_SCRIPT_ID = 'google-analytics-script';
const GOOGLE_ANALYTICS_SCRIPT_SRC = `https://www.googletagmanager.com/gtag/js?id=${GOOGLE_ANALYTICS_ID}`;
const GOOGLE_ANALYTICS_HOSTNAMES = new Set(['residenciafiscal.org', 'www.residenciafiscal.org']);

type GoogleAnalyticsCommand =
  | ['js', Date]
  | ['config', string]
  | ['event', string, { page_path: string; page_title: string }];

declare global {
  interface Window {
    dataLayer?: IArguments[];
    gtag?: (...args: GoogleAnalyticsCommand) => void;
    __residenciaFiscalGoogleAnalyticsInitialized?: boolean;
  }
}

export const isGoogleAnalyticsEnabled = ({
  hostname,
  search,
}: Pick<Location, 'hostname' | 'search'>): boolean =>
  GOOGLE_ANALYTICS_HOSTNAMES.has(hostname.toLowerCase()) &&
  !new URLSearchParams(search).has('synthetic_monitor');

const installGoogleAnalytics = () => {
  if (!isGoogleAnalyticsEnabled(window.location)) return;

  window.dataLayer = window.dataLayer ?? [];
  if (!window.gtag) {
    window.gtag = function gtag() {
      // biome-ignore lint/complexity/noArguments: gtag.js requires the Arguments object.
      window.dataLayer?.push(arguments);
    };
  }

  if (!window.__residenciaFiscalGoogleAnalyticsInitialized) {
    window.gtag('js', new Date());
    window.gtag('config', GOOGLE_ANALYTICS_ID);
    window.__residenciaFiscalGoogleAnalyticsInitialized = true;
  }

  if (document.getElementById(GOOGLE_ANALYTICS_SCRIPT_ID)) return;

  const script = document.createElement('script');
  script.id = GOOGLE_ANALYTICS_SCRIPT_ID;
  script.async = true;
  script.src = GOOGLE_ANALYTICS_SCRIPT_SRC;
  document.head.appendChild(script);
};

/** Installs GA4 once and records subsequent SPA route changes as page views. */
export const GoogleAnalyticsFooter = () => {
  const location = useLocation();
  const isInitialPage = useRef(true);

  useEffect(() => {
    installGoogleAnalytics();
  }, []);

  useEffect(() => {
    if (!isGoogleAnalyticsEnabled(window.location)) return;

    if (isInitialPage.current) {
      isInitialPage.current = false;
      return;
    }

    const pagePath = `${location.pathname}${location.search}${location.hash}`;
    window.gtag?.('event', 'page_view', {
      page_path: pagePath,
      page_title: document.title,
    });
  }, [location.hash, location.pathname, location.search]);

  return null;
};
