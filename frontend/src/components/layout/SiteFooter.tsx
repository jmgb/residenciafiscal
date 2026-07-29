import { GoogleAnalyticsFooter } from './GoogleAnalyticsFooter';

export { GOOGLE_ANALYTICS_ID } from './GoogleAnalyticsFooter';

export const SiteFooter = () => (
  <footer className='border-t border-border bg-background px-6 py-4 text-sm text-muted-foreground'>
    <div className='mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-2'>
      <span>Residencia Fiscal</span>
      <span>Jurisprudencia tributaria sobre el art. 9 LIRPF</span>
    </div>
    <GoogleAnalyticsFooter />
  </footer>
);
