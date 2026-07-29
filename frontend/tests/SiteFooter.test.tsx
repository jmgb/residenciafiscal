import { render, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import {
  GOOGLE_ANALYTICS_ID,
  isGoogleAnalyticsEnabled,
} from '@/components/layout/GoogleAnalyticsFooter';
import { SiteFooter } from '@/components/layout/SiteFooter';

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

describe('SiteFooter', () => {
  it('installs Google Analytics once for every page using the shared footer', async () => {
    render(
      <MemoryRouter initialEntries={['/metodologia']}>
        <SiteFooter />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(document.querySelector('#google-analytics-script')).toBeInTheDocument();
    });

    const scripts = document.querySelectorAll(
      `script[src="https://www.googletagmanager.com/gtag/js?id=${GOOGLE_ANALYTICS_ID}"]`
    );

    expect(scripts).toHaveLength(1);
    expect(document.querySelector('footer')).toBeInTheDocument();
    expect(Array.from(window.dataLayer?.[1] ?? [])).toEqual(['config', GOOGLE_ANALYTICS_ID]);
  });
});
