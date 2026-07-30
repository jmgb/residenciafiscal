import { render, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import {
  GOOGLE_ANALYTICS_ID,
  GoogleAnalytics,
  isGoogleAnalyticsEnabled,
} from '@/components/layout/GoogleAnalytics';

describe('isGoogleAnalyticsEnabled', () => {
  it('only enables analytics on the canonical production hosts', () => {
    expect(isGoogleAnalyticsEnabled({ hostname: 'residenciafiscal.org', search: '' })).toBe(true);
    expect(isGoogleAnalyticsEnabled({ hostname: 'www.residenciafiscal.org', search: '' })).toBe(
      true
    );
    expect(
      isGoogleAnalyticsEnabled({
        hostname: 'deploy-preview-12--residenciafiscal.netlify.app',
        search: '',
      })
    ).toBe(false);
    expect(isGoogleAnalyticsEnabled({ hostname: 'localhost', search: '' })).toBe(false);
  });

  it('skips synthetic monitor visits', () => {
    expect(
      isGoogleAnalyticsEnabled({
        hostname: 'residenciafiscal.org',
        search: '?synthetic_monitor=1',
      })
    ).toBe(false);
  });
});

describe('GoogleAnalytics', () => {
  it('installs Google Analytics once for every page', async () => {
    render(
      <MemoryRouter initialEntries={['/metodologia']}>
        <GoogleAnalytics />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(document.querySelector('#google-analytics-script')).toBeInTheDocument();
    });

    const scripts = document.querySelectorAll(
      `script[src="https://www.googletagmanager.com/gtag/js?id=${GOOGLE_ANALYTICS_ID}"]`
    );

    expect(scripts).toHaveLength(1);
    expect(document.querySelector('footer')).not.toBeInTheDocument();
    expect(Array.from(window.dataLayer?.[1] ?? [])).toEqual(['config', GOOGLE_ANALYTICS_ID]);
  });
});
