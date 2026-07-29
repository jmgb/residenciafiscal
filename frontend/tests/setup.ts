import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

afterEach(() => {
  cleanup();
  document.head.innerHTML = '';
  delete window.dataLayer;
  delete window.gtag;
  delete window.__residenciaFiscalGoogleAnalyticsInitialized;
});
