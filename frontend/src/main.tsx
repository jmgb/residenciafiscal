import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router';
import { App } from './App';
import { installModulePreloadRecovery } from './lib/module-preload-recovery';
import { initializeSentry, SentryErrorBoundary } from './lib/sentry';
import { readEmbeddedTreatyPreload, TreatyPreloadContext } from './lib/treaty-preload';
import './index.css';

// Antes de montar nada: si el HTML es de un deploy anterior, el primer chunk que
// falte dispara el error durante el arranque.
installModulePreloadRecovery();

void initializeSentry({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  enabled: import.meta.env.PROD && import.meta.env.VITE_SENTRY_ENABLED !== 'false',
  environment: import.meta.env.VITE_SENTRY_ENVIRONMENT || import.meta.env.MODE,
  release: __SENTRY_RELEASE__,
  tracesSampleRate: Number(import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE || '0.1'),
});

const container = document.getElementById('root');
if (!container) throw new Error('No se encontró el elemento #root');

// El HTML llega con la página ya renderizada por el build. React la sustituye
// al montar —`createRoot` limpia el contenedor—, y para que el visitante no vea
// desaparecer el convenio mientras se pide por red, el convenio de esta página
// viaja embebido en el propio HTML.
const treaties = readEmbeddedTreatyPreload(document);

createRoot(container).render(
  <StrictMode>
    <SentryErrorBoundary
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
      <TreatyPreloadContext.Provider value={treaties}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </TreatyPreloadContext.Provider>
    </SentryErrorBoundary>
  </StrictMode>
);
