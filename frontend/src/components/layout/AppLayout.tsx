import { PanelLeft, PanelLeftClose } from 'lucide-react';
import { useEffect, useRef } from 'react';
import { Outlet, useLocation } from 'react-router';
import { JsonLd } from '@/components/seo/JsonLd';
import { getJurisdictionRoute } from '@/data/countryRoutes';
import { organizationJsonLd, websiteJsonLd } from '@/lib/structured-data';
import { Button } from '@/shared/components/ui/button';
import { AppSidebar } from './AppSidebar';
import { AppUpdateBanner } from './AppUpdateBanner';
import { GoogleAnalytics } from './GoogleAnalytics';
import { MobileNavigation } from './MobileNavigation';
import { PostHogAnalytics } from './PostHogAnalytics';
import { useSidebarCollapsed } from './useSidebarCollapsed';

const SIDEBAR_ID = 'app-sidebar';

/**
 * Shell de dos columnas: sidebar persistente en desktop, drawer por debajo de
 * `lg`, y columna de contenido con un único scroll vertical.
 *
 * Portado del `PrivateLayout` de Presupuestor, conservando su barra fina sticky
 * y el reset de scroll + foco a11y al navegar (el `<main>` es un contenedor de
 * scroll independiente, así que el scroll del documento no sirve).
 */
export function AppLayout() {
  const { collapsed, toggle } = useSidebarCollapsed();
  const location = useLocation();
  const selectedCountry = getJurisdictionRoute(location.pathname);
  const mainRef = useRef<HTMLElement>(null);
  const hasMountedRef = useRef(false);

  // `location.pathname` es la dependencia DISPARADORA del efecto (resetear scroll y foco
  // al navegar) aunque su valor no se lea dentro: quitarla lo dejaría ejecutándose solo
  // en el montaje.
  // biome-ignore lint/correctness/useExhaustiveDependencies: disparador intencionado.
  useEffect(() => {
    const isInitialMount = !hasMountedRef.current;
    hasMountedRef.current = true;
    const main = mainRef.current;
    if (!main) return;
    if (typeof main.scrollTo === 'function') {
      main.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      main.scrollTop = 0;
    }
    if (isInitialMount) return;
    main.focus({ preventScroll: true });
  }, [location.pathname]);

  return (
    <div className='flex h-screen supports-[height:100dvh]:h-dvh overflow-hidden bg-canvas'>
      {/* Identidad del sitio para el buscador: se emite aquí, una vez para
          todas las rutas, y dentro del árbol de React para que el HTML
          prerenderizado y la SPA no puedan divergir. */}
      <JsonLd data={websiteJsonLd()} />
      <JsonLd data={organizationJsonLd()} />
      <AppSidebar id={SIDEBAR_ID} collapsed={collapsed} className='hidden lg:flex' />

      <div className='flex min-w-0 flex-1 flex-col'>
        {/* Fuera del `main`, que es el contenedor de scroll: el aviso no debe
            desaparecer al desplazar la conversación. */}
        <AppUpdateBanner />

        <main
          ref={mainRef}
          tabIndex={-1}
          aria-label='Contenido principal'
          className='flex min-h-0 flex-1 flex-col overflow-hidden focus:outline-none'
        >
          <div className='sticky top-0 z-30 flex shrink-0 items-center gap-3 border-b border-border bg-canvas/95 px-4 py-2 backdrop-blur supports-[backdrop-filter]:bg-canvas/80'>
            <MobileNavigation />
            <Button
              type='button'
              variant='ghost'
              size='icon'
              onClick={toggle}
              aria-controls={SIDEBAR_ID}
              aria-expanded={!collapsed}
              aria-label={collapsed ? 'Expandir menú lateral' : 'Colapsar menú lateral'}
              className='hidden lg:inline-flex'
            >
              {collapsed ? (
                <PanelLeft className='h-4 w-4' aria-hidden='true' />
              ) : (
                <PanelLeftClose className='h-4 w-4' aria-hidden='true' />
              )}
            </Button>
            <span className='truncate font-heading text-sm font-semibold text-foreground'>
              Residencia Fiscal{selectedCountry ? ` en ${selectedCountry.name}` : ''}
            </span>
          </div>

          <div className='flex min-h-0 flex-1 flex-col'>
            <Outlet />
          </div>
        </main>

        <GoogleAnalytics />
        <PostHogAnalytics />
      </div>
    </div>
  );
}
