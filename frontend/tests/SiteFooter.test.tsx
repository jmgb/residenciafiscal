import { render, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { GOOGLE_ANALYTICS_ID, SiteFooter } from '@/components/layout/SiteFooter';

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
    expect(window.dataLayer?.[1]).toEqual(['config', GOOGLE_ANALYTICS_ID]);
  });
});
