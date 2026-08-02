import { ChatView } from '@/components/chat/ChatView';
import { SpainLandingContent } from '@/components/country/SpainLandingContent';
import { JsonLd } from '@/components/seo/JsonLd';
import { SPAIN_ROUTE } from '@/data/countryRoutes';
import { chatEngine, chatEngineMode } from '@/lib/chat-engine';
import { breadcrumbJsonLd } from '@/lib/structured-data';

interface SpainPageProps {
  showLandingContent?: boolean;
}

export function SpainPage({ showLandingContent = true }: SpainPageProps) {
  return (
    /*
     * España es una landing de país como las demás —su canonical es `/espana`,
     * y es la de mayor prioridad del sitemap—, pero no usa `CountryPage`:
     * monta el chat. El wrapper con scroll propio deja que el chat ocupe
     * exactamente el alto visible, como siempre, y que debajo viva la sección
     * estática indexable: al cargar no cambia nada y al hacer scroll aparece
     * el contenido que lee el buscador.
     */
    <div className='flex min-h-0 flex-1 flex-col overflow-y-auto'>
      {/* Sin esta línea era la única de las 34 rutas sin datos estructurados,
          que es justo la que más importa. */}
      {showLandingContent && <JsonLd data={breadcrumbJsonLd([SPAIN_ROUTE])} />}
      <div className='flex h-full shrink-0 flex-col'>
        <ChatView
          engine={chatEngine}
          isStub={chatEngineMode === 'stub'}
          canonicalPath={SPAIN_ROUTE.path}
          country={SPAIN_ROUTE}
        />
      </div>
      {showLandingContent && <SpainLandingContent />}
    </div>
  );
}
