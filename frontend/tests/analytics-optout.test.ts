import { beforeEach, describe, expect, it } from 'vitest';
import { isGoogleAnalyticsEnabled } from '@/components/layout/GoogleAnalytics';
import {
  ANALYTICS_OPTOUT_KEY,
  hasAnalyticsOptOut,
  syncAnalyticsOptOut,
} from '@/lib/analytics-optout';

describe('syncAnalyticsOptOut', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('marks the browser when the opt-out parameter arrives', () => {
    syncAnalyticsOptOut('?no_analytics=1');

    expect(hasAnalyticsOptOut()).toBe(true);
  });

  it('keeps the mark across later visits without the parameter', () => {
    syncAnalyticsOptOut('?no_analytics=1');
    syncAnalyticsOptOut('?utm_source=telegram');

    expect(hasAnalyticsOptOut()).toBe(true);
  });

  it('lets the browser opt back in', () => {
    syncAnalyticsOptOut('?no_analytics=1');
    syncAnalyticsOptOut('?no_analytics=0');

    expect(hasAnalyticsOptOut()).toBe(false);
  });

  it('does nothing when the parameter is absent', () => {
    syncAnalyticsOptOut('');

    expect(window.localStorage.getItem(ANALYTICS_OPTOUT_KEY)).toBeNull();
  });

  it('survives a storage that throws, as in Safari private mode', () => {
    // `vi.spyOn` no sirve aquí: jsdom devuelve un objeto `Storage` distinto en
    // cada acceso a `window.localStorage`, así que hay que sustituir la
    // propiedad entera para que el módulo vea el almacenamiento roto.
    const real = Object.getOwnPropertyDescriptor(window, 'localStorage');
    const roto = {
      getItem: () => {
        throw new Error('SecurityError');
      },
      setItem: () => {
        throw new Error('QuotaExceededError');
      },
      removeItem: () => {
        throw new Error('SecurityError');
      },
    };
    Object.defineProperty(window, 'localStorage', { value: roto, configurable: true });

    try {
      expect(() => syncAnalyticsOptOut('?no_analytics=1')).not.toThrow();
      expect(hasAnalyticsOptOut()).toBe(false);
    } finally {
      if (real) Object.defineProperty(window, 'localStorage', real);
    }
  });
});

describe('isGoogleAnalyticsEnabled with the opt-out', () => {
  it('refuses a production host once the browser opted out', () => {
    expect(isGoogleAnalyticsEnabled({ hostname: 'residenciafiscal.org', search: '' }, true)).toBe(
      false
    );
  });

  it('still allows a production host without the mark', () => {
    expect(isGoogleAnalyticsEnabled({ hostname: 'residenciafiscal.org', search: '' }, false)).toBe(
      true
    );
  });

  it('reads the mark from storage when it is not injected', () => {
    window.localStorage.clear();
    syncAnalyticsOptOut('?no_analytics=1');

    expect(isGoogleAnalyticsEnabled({ hostname: 'residenciafiscal.org', search: '' })).toBe(false);

    window.localStorage.clear();
  });
});
