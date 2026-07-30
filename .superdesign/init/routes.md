# Routes

Routing uses React Router v8 with `BrowserRouter`. Every route renders inside `AppLayout`.

- `/` → redirect to `/espana`
- `/espana` → `frontend/src/pages/SpainPage.tsx`; main full-height jurisprudence chat
- `/espana/chat/:conversationId` → `SpainPage`; existing conversation
- Country routes from `countryRoutes.json` → `CountryPage`; Spain is excluded because it has the chat
- Country conversation paths → redirect to the corresponding country landing page
- Legacy country slugs → canonical country paths
- `/manifiesto` → `ManifiestoPage`
- `/metodologia` → `MetodologiaPage`
- `/colaborar` → `ColaborarPage`
- all others → redirect to `/`

### `frontend/src/App.tsx`

```tsx
import { Navigate, Route, Routes } from 'react-router';
import { ChatView } from '@/components/chat/ChatView';
import { AppLayout } from '@/components/layout/AppLayout';
import { COUNTRY_ROUTE_REDIRECTS, COUNTRY_ROUTES, SPAIN_ROUTE } from '@/data/countryRoutes';
import { chatEngine, chatEngineMode } from '@/lib/chat-engine';
import { ColaborarPage } from '@/pages/ColaborarPage';
import { CountryPage } from '@/pages/CountryPage';
import { ManifiestoPage } from '@/pages/ManifiestoPage';
import { MetodologiaPage } from '@/pages/MetodologiaPage';
import { SpainPage } from '@/pages/SpainPage';

const isStub = chatEngineMode === 'stub';

export function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path='/' element={<Navigate to={SPAIN_ROUTE.path} replace />} />
        <Route path={SPAIN_ROUTE.path} element={<SpainPage />} />
        <Route
          path='/consulta'
          element={
            <ChatView
              engine={chatEngine}
              isStub={isStub}
              canonicalPath='/consulta'
              country={SPAIN_ROUTE}
            />
          }
        />
        <Route
          path='/c/:conversationId'
          element={
            <ChatView
              engine={chatEngine}
              isStub={isStub}
              canonicalPath='/consulta'
              country={SPAIN_ROUTE}
            />
          }
        />
        {COUNTRY_ROUTES.filter((country) => country.path !== SPAIN_ROUTE.path).map((country) => (
          <Route
            key={country.path}
            path={country.path}
            element={<CountryPage country={country} />}
          />
        ))}
        {COUNTRY_ROUTE_REDIRECTS.map(({ from, to }) => (
          <Route key={from} path={from} element={<Navigate to={to} replace />} />
        ))}
        <Route path='/manifiesto' element={<ManifiestoPage />} />
        <Route path='/metodologia' element={<MetodologiaPage />} />
        <Route path='/colaborar' element={<ColaborarPage />} />
        <Route path='*' element={<Navigate to='/' replace />} />
      </Route>
    </Routes>
  );
}
```

### `frontend/src/main.tsx`

```tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router';
import { App } from './App';
import { initializeSentry, SentryErrorBoundary } from './lib/sentry';
import './index.css';

void initializeSentry({
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
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </SentryErrorBoundary>
  </StrictMode>
);
```

