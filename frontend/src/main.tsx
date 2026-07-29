import * as Sentry from '@sentry/react';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router';
import { App } from './App';
import { initializeSentry } from './lib/sentry';
import './index.css';

initializeSentry({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  enabled: import.meta.env.PROD && import.meta.env.VITE_SENTRY_ENABLED !== 'false',
  environment: import.meta.env.VITE_SENTRY_ENVIRONMENT || import.meta.env.MODE,
  release: __SENTRY_RELEASE__,
  tracesSampleRate: Number(import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE || '0.1'),
});

const container = document.getElementById('root');
if (!container) throw new Error('No se encontró el elemento #root');

createRoot(container).render(
  <StrictMode>
    <Sentry.ErrorBoundary
      fallback={
        <main className='mx-auto flex min-h-screen max-w-xl flex-col justify-center gap-4 px-6'>
          <h1 className='text-2xl font-semibold'>No hemos podido cargar la aplicación</h1>
          <p>El error se ha registrado. Recarga la página para volver a intentarlo.</p>
          <button
            className='w-fit rounded-md bg-slate-900 px-4 py-2 text-white'
            onClick={() => window.location.reload()}
            type='button'
          >
            Recargar
          </button>
        </main>
      }
    >
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </Sentry.ErrorBoundary>
  </StrictMode>
);
