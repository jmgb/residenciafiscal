import { ChatView } from '@/components/chat/ChatView';
import { JsonLd } from '@/components/seo/JsonLd';
import { SPAIN_ROUTE } from '@/data/countryRoutes';
import { chatEngine, chatEngineMode } from '@/lib/chat-engine';
import { breadcrumbJsonLd } from '@/lib/structured-data';

export function SpainPage() {
  return (
    <>
      {/*
       * España es una landing de país como las demás —su canonical es
       * `/espana`, y es la de mayor prioridad del sitemap—, pero no usa
       * `CountryPage`: monta el chat. Sin esta línea era la única de las 34 sin
       * datos estructurados, que es justo la que más importa.
       */}
      <JsonLd data={breadcrumbJsonLd([SPAIN_ROUTE])} />
      <ChatView
        engine={chatEngine}
        isStub={chatEngineMode === 'stub'}
        canonicalPath={SPAIN_ROUTE.path}
        country={SPAIN_ROUTE}
      />
    </>
  );
}
