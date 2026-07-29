import { Navigate, Route, Routes } from 'react-router';
import { ChatView } from '@/components/chat/ChatView';
import { AppLayout } from '@/components/layout/AppLayout';
import { COUNTRY_ROUTES, SPAIN_ROUTE } from '@/data/countryRoutes';
import { chatEngine, chatEngineMode } from '@/lib/chat-engine';
import { CountryPage } from '@/pages/CountryPage';
import { ManifiestoPage } from '@/pages/ManifiestoPage';
import { MetodologiaPage } from '@/pages/MetodologiaPage';
import { SpainPage } from '@/pages/SpainPage';

const isStub = chatEngineMode === 'stub';

export function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path='/' element={<Navigate to='/españa' replace />} />
        <Route path='/españa' element={<SpainPage />} />
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
        {COUNTRY_ROUTES.filter((country) => country.path !== '/españa').map((country) => (
          <Route
            key={country.path}
            path={country.path}
            element={<CountryPage country={country} />}
          />
        ))}
        <Route path='/manifiesto' element={<ManifiestoPage />} />
        <Route path='/metodologia' element={<MetodologiaPage />} />
        <Route path='*' element={<Navigate to='/' replace />} />
      </Route>
    </Routes>
  );
}
