import { Navigate, Route, Routes } from 'react-router';
import { ChatView } from '@/components/chat/ChatView';
import { AppLayout } from '@/components/layout/AppLayout';
import { COUNTRY_ROUTE_REDIRECTS, COUNTRY_ROUTES, SPAIN_ROUTE } from '@/data/countryRoutes';
import { chatEngine, chatEngineMode } from '@/lib/chat-engine';
import { ColaborarPage } from '@/pages/ColaborarPage';
import { CountryPage } from '@/pages/CountryPage';
import { EspanaFuentesPage } from '@/pages/EspanaFuentesPage';
import { ManifiestoPage } from '@/pages/ManifiestoPage';
import { MetodologiaPage } from '@/pages/MetodologiaPage';
import { NormativaIndexPage } from '@/pages/NormativaIndexPage';
import { PreceptoPage } from '@/pages/PreceptoPage';
import { PrivacyPage } from '@/pages/PrivacyPage';
import { SpainPage } from '@/pages/SpainPage';

const isStub = chatEngineMode === 'stub';

export function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path='/' element={<Navigate to={SPAIN_ROUTE.path} replace />} />
        <Route path={SPAIN_ROUTE.path} element={<SpainPage />} />
        <Route path='/espana/fuentes' element={<EspanaFuentesPage />} />
        <Route path='/espana/normativa' element={<NormativaIndexPage />} />
        <Route path='/espana/normativa/:slug' element={<PreceptoPage />} />
        {/*
         * `/consulta` y `/c/:id` sirven exactamente el mismo chat que `/espana`,
         * así que canonicalizan allí: es la URL del sitemap. Autocanonicalizarse
         * las publicaba como contenido duplicado indexable, y `/consulta` está
         * enlazada desde `/manifiesto`, que sí se indexa.
         */}
        <Route
          path='/consulta'
          element={
            <ChatView
              engine={chatEngine}
              isStub={isStub}
              canonicalPath={SPAIN_ROUTE.path}
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
              canonicalPath={SPAIN_ROUTE.path}
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
        <Route path='/privacidad' element={<PrivacyPage />} />
        <Route path='*' element={<Navigate to='/' replace />} />
      </Route>
    </Routes>
  );
}
