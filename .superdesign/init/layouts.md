# Shared layouts

The application uses a full-height two-column shell. The sidebar is persistent on desktop and a sheet on mobile. The content column includes a sticky top bar and a footer fixed below the main content area.

### `frontend/src/components/layout/AppLayout.tsx`

```tsx
import { PanelLeft, PanelLeftClose } from 'lucide-react';
import { useEffect, useRef } from 'react';
import { Outlet, useLocation } from 'react-router';
import { getCountryRoute } from '@/data/countryRoutes';
import { Button } from '@/shared/components/ui/button';
import { AppSidebar } from './AppSidebar';
import { MobileNavigation } from './MobileNavigation';
import { SiteFooter } from './SiteFooter';
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
  const selectedCountry = getCountryRoute(location.pathname);
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
    <div className='flex h-screen supports-[height:100dvh]:h-dvh overflow-hidden bg-background'>
      <AppSidebar id={SIDEBAR_ID} collapsed={collapsed} className='hidden lg:flex' />

      <div className='flex min-w-0 flex-1 flex-col'>
        <main
          ref={mainRef}
          tabIndex={-1}
          aria-label='Contenido principal'
          className='flex min-h-0 flex-1 flex-col overflow-hidden focus:outline-none'
        >
          <div className='sticky top-0 z-30 flex shrink-0 items-center gap-3 border-b border-border bg-background/95 px-4 py-2 backdrop-blur supports-[backdrop-filter]:bg-background/80'>
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

        {/*
         * El pie común va FUERA de `<main>` y como último hijo de la columna de
         * contenido, no dentro del área desplazable:
         *  - `<main>` es `overflow-hidden` y la vista de chat se lleva todo el
         *    alto disponible; un pie dentro quedaría empujado fuera y recortado.
         *  - así el pie conserva su landmark `contentinfo` (un `<footer>` dentro
         *    de `<main>` deja de serlo) y no lo alcanzan ni el reset de scroll
         *    ni el `focus()` de navegación del `<main>`.
         *  - `shrink-0` garantiza que la banda no se comprima y que el composer
         *    del chat, anclado abajo dentro del `<main>`, quede justo encima.
         * Se monta una sola vez por página, dentro del router, porque
         * `SiteFooter` monta `GoogleAnalyticsFooter` (usa `useLocation`).
         */}
        <div className='shrink-0'>
          <SiteFooter />
        </div>
      </div>
    </div>
  );
}
```

### `frontend/src/components/layout/AppSidebar.tsx`

```tsx
import { cn } from '@/shared/lib/utils';
import { SidebarBrand, SidebarFooter, SidebarNavigation } from './SidebarContent';

export interface AppSidebarProps {
  collapsed: boolean;
  /** `id` del landmark, enlazado desde el toggle mediante `aria-controls`. */
  id?: string;
  className?: string;
}

export function AppSidebar({ collapsed, id, className }: AppSidebarProps) {
  return (
    <aside
      id={id}
      data-collapsed={collapsed}
      className={cn(
        'flex h-full shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground',
        'transition-[width] duration-200 motion-reduce:transition-none',
        collapsed ? 'w-16' : 'w-64',
        className
      )}
    >
      <SidebarBrand collapsed={collapsed} />
      <div className='min-h-0 flex-1 overflow-y-auto py-4'>
        <SidebarNavigation collapsed={collapsed} />
      </div>
      <SidebarFooter collapsed={collapsed} />
    </aside>
  );
}
```

### `frontend/src/components/layout/MobileNavigation.tsx`

```tsx
import { Menu } from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/shared/components/ui/button';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetTitle,
  SheetTrigger,
} from '@/shared/components/ui/sheet';
import { SidebarBrand, SidebarFooter, SidebarNavigation } from './SidebarContent';

const SHEET_CONTENT_ID = 'mobile-navigation';

/**
 * Drawer de navegación por debajo de `lg`. Reutiliza exactamente las mismas
 * piezas que el sidebar desktop, siempre en modo expandido.
 */
export function MobileNavigation() {
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button
          type='button'
          variant='ghost'
          size='icon'
          className='lg:hidden'
          aria-label='Abrir menú de navegación'
          aria-controls={SHEET_CONTENT_ID}
        >
          <Menu className='h-5 w-5' aria-hidden='true' />
        </Button>
      </SheetTrigger>

      <SheetContent
        id={SHEET_CONTENT_ID}
        side='left'
        className='flex w-[min(20rem,88vw)] flex-col gap-0 border-sidebar-border bg-sidebar p-0 text-sidebar-foreground sm:max-w-none'
      >
        <div className='sr-only'>
          <SheetTitle>Navegación</SheetTitle>
          <SheetDescription>Menú de navegación de la aplicación</SheetDescription>
        </div>

        <SidebarBrand onNavigate={close} />
        <div className='min-h-0 flex-1 overflow-y-auto py-4'>
          <SidebarNavigation onNavigate={close} />
        </div>
        <SidebarFooter onNavigate={close} />
      </SheetContent>
    </Sheet>
  );
}
```

### `frontend/src/components/layout/SidebarContent.tsx`

```tsx
import { BookOpen, Compass, Globe2, MessageSquarePlus, Trash2, Users } from 'lucide-react';
import { useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router';
import { COUNTRY_ROUTES, getCountryRoute, SPAIN_ROUTE } from '@/data/countryRoutes';
import { Button } from '@/shared/components/ui/button';
import { cn } from '@/shared/lib/utils';
import { useConversations } from '@/stores/useConversations';

export interface SidebarContentProps {
  /** Modo rail: solo iconos. Nunca se activa en el drawer móvil. */
  collapsed?: boolean;
  /** El drawer lo usa para cerrarse al navegar. */
  onNavigate?: () => void;
}

export function SidebarBrand({ collapsed = false, onNavigate }: SidebarContentProps) {
  return (
    <div
      className={cn(
        'flex shrink-0 items-center gap-3 border-b border-sidebar-border py-4',
        collapsed ? 'justify-center px-2' : 'px-4'
      )}
    >
      <Link
        to={SPAIN_ROUTE.path}
        onClick={onNavigate}
        aria-label='Ir al inicio'
        className='flex shrink-0 items-center rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring'
      >
        <img src='/favicon.svg' alt='' className='h-9 w-9' />
      </Link>
      {!collapsed && (
        <div className='min-w-0'>
          <div className='truncate font-heading text-sm font-semibold'>Residencia Fiscal</div>
          <div className='truncate text-xs text-muted-foreground'>Art. 9 LIRPF</div>
        </div>
      )}
    </div>
  );
}

export function SidebarNavigation({ collapsed = false, onNavigate }: SidebarContentProps) {
  const navigate = useNavigate();
  const { conversationId } = useParams();
  const conversations = useConversations((state) => state.conversations);
  const deleteConversation = useConversations((state) => state.deleteConversation);
  const [showAllCountries, setShowAllCountries] = useState(false);

  // La conversación se crea de forma perezosa en `ChatView` con el primer
  // mensaje, así que «Nueva consulta» solo navega a la raíz.
  const handleNew = () => {
    onNavigate?.();
    navigate('/consulta');
  };

  const handleDelete = (id: string) => {
    if (!window.confirm('¿Borrar esta conversación? Esta acción no se puede deshacer.')) return;
    deleteConversation(id);
    if (id === conversationId) navigate('/');
  };

  const location = useLocation();

  return (
    <>
      <nav
        aria-label='Conversaciones'
        className={cn('flex flex-col gap-1', collapsed ? 'px-2' : 'px-3')}
      >
        <Button
          type='button'
          onClick={handleNew}
          className={cn('mb-2 w-full', collapsed && 'px-0')}
          aria-label='Nueva consulta'
          title='Nueva consulta'
        >
          <MessageSquarePlus className='h-4 w-4 shrink-0' aria-hidden='true' />
          {!collapsed && <span>Nueva consulta</span>}
        </Button>

        {!collapsed && conversations.length === 0 && (
          <p className='px-2 py-4 text-xs text-muted-foreground'>
            Todavía no has hecho ninguna consulta.
          </p>
        )}

        {!collapsed &&
          conversations.map((conversation) => {
            const isActive = conversation.id === conversationId;
            return (
              <div
                key={conversation.id}
                className={cn(
                  'group flex items-center gap-1 rounded-lg pr-1 transition-colors',
                  isActive
                    ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                    : 'hover:bg-sidebar-accent/60'
                )}
              >
                <Link
                  to={`/c/${conversation.id}`}
                  onClick={onNavigate}
                  aria-current={isActive ? 'page' : undefined}
                  className='min-w-0 flex-1 truncate rounded-lg px-2 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring'
                  title={conversation.title}
                >
                  {conversation.title}
                </Link>
                <button
                  type='button'
                  onClick={() => handleDelete(conversation.id)}
                  aria-label={`Borrar conversación: ${conversation.title}`}
                  className='shrink-0 rounded p-1 text-muted-foreground opacity-0 transition-opacity hover:text-destructive focus-visible:opacity-100 group-hover:opacity-100'
                >
                  <Trash2 className='h-3.5 w-3.5' aria-hidden='true' />
                </button>
              </div>
            );
          })}
      </nav>

      <nav
        aria-label='Países'
        className={cn('mt-6 flex flex-col gap-1', collapsed ? 'px-2' : 'px-3')}
      >
        {collapsed ? (
          <Link
            to={SPAIN_ROUTE.path}
            onClick={onNavigate}
            aria-label='Países'
            title='Países'
            className='flex justify-center rounded-lg p-2 text-muted-foreground outline-none hover:bg-sidebar-accent focus-visible:ring-2 focus-visible:ring-sidebar-ring'
          >
            <Globe2 className='h-4 w-4' aria-hidden='true' />
          </Link>
        ) : (
          <>
            <h2 className='flex items-center gap-2 px-2 pb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground'>
              <Globe2 className='h-3.5 w-3.5' aria-hidden='true' />
              Países
            </h2>
            {(showAllCountries ? COUNTRY_ROUTES : COUNTRY_ROUTES.slice(0, 3)).map((country) => {
              const isActive = getCountryRoute(location.pathname)?.path === country.path;
              return (
                <Link
                  key={country.path}
                  to={country.path}
                  onClick={onNavigate}
                  aria-current={isActive ? 'page' : undefined}
                  className={cn(
                    'truncate rounded-lg px-2 py-1.5 text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-sidebar-ring',
                    isActive
                      ? 'bg-sidebar-accent font-semibold text-sidebar-accent-foreground'
                      : 'text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-foreground'
                  )}
                >
                  {country.name}
                </Link>
              );
            })}
            {!showAllCountries && (
              <button
                type='button'
                onClick={() => setShowAllCountries(true)}
                className='rounded-lg px-2 py-1.5 text-left text-sm font-medium text-muted-foreground outline-none transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus-visible:ring-2 focus-visible:ring-sidebar-ring'
              >
                Mostrar más
              </button>
            )}
          </>
        )}
      </nav>
    </>
  );
}

export function SidebarFooter({ collapsed = false, onNavigate }: SidebarContentProps) {
  if (collapsed) {
    return (
      <div className='shrink-0 border-t border-sidebar-border px-2 py-3'>
        <Link
          to='/manifiesto'
          onClick={onNavigate}
          aria-label='Manifiesto'
          title='Manifiesto'
          className='flex justify-center rounded-lg p-2 text-muted-foreground outline-none hover:bg-sidebar-accent focus-visible:ring-2 focus-visible:ring-sidebar-ring'
        >
          <Compass className='h-4 w-4' aria-hidden='true' />
        </Link>
        <Link
          to='/metodologia'
          onClick={onNavigate}
          aria-label='Metodología'
          title='Metodología'
          className='flex justify-center rounded-lg p-2 text-muted-foreground outline-none hover:bg-sidebar-accent focus-visible:ring-2 focus-visible:ring-sidebar-ring'
        >
          <BookOpen className='h-4 w-4' aria-hidden='true' />
        </Link>
        <Link
          to='/colaborar'
          onClick={onNavigate}
          aria-label='Colaborar'
          title='Colaborar'
          className='flex justify-center rounded-lg p-2 text-muted-foreground outline-none hover:bg-sidebar-accent focus-visible:ring-2 focus-visible:ring-sidebar-ring'
        >
          <Users className='h-4 w-4' aria-hidden='true' />
        </Link>
      </div>
    );
  }

  return (
    <div className='shrink-0 border-t border-sidebar-border px-3 py-3 text-xs'>
      <Link
        to='/manifiesto'
        onClick={onNavigate}
        className='block rounded px-2 py-1.5 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-sidebar-ring'
      >
        Manifiesto
      </Link>
      <Link
        to='/metodologia'
        onClick={onNavigate}
        className='block rounded px-2 py-1.5 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-sidebar-ring'
      >
        Metodología
      </Link>
      <Link
        to='/metodologia#corpus'
        onClick={onNavigate}
        className='block rounded px-2 py-1.5 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-sidebar-ring'
      >
        Corpus analizado
      </Link>
      <Link
        to='/colaborar'
        onClick={onNavigate}
        className='block rounded px-2 py-1.5 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-sidebar-ring'
      >
        Colaborar
      </Link>
    </div>
  );
}
```

### `frontend/src/components/layout/SiteFooter.tsx`

```tsx
import { GoogleAnalyticsFooter } from './GoogleAnalyticsFooter';

export { GOOGLE_ANALYTICS_ID } from './GoogleAnalyticsFooter';

export const SiteFooter = () => (
  <footer className='border-t border-border bg-background px-6 py-4 text-sm text-muted-foreground'>
    <div className='mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-x-4 gap-y-1'>
      <span>Residencia Fiscal</span>
      <span>Jurisprudencia tributaria sobre el art. 9 LIRPF</span>
      <span>Información orientativa. No determina oficialmente tu residencia fiscal.</span>
      <span>
        Contacto:{' '}
        <a
          href='mailto:info@residenciafiscal.org'
          className='text-foreground underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2'
        >
          info@residenciafiscal.org
        </a>
      </span>
    </div>
    <GoogleAnalyticsFooter />
  </footer>
);
```

### `frontend/src/components/layout/GoogleAnalyticsFooter.tsx`

```tsx
import { useEffect, useRef } from 'react';
import { useLocation } from 'react-router';

export const GOOGLE_ANALYTICS_ID = 'G-XKX3N9KVJH';

const GOOGLE_ANALYTICS_SCRIPT_ID = 'google-analytics-script';
const GOOGLE_ANALYTICS_SCRIPT_SRC = `https://www.googletagmanager.com/gtag/js?id=${GOOGLE_ANALYTICS_ID}`;
const GOOGLE_ANALYTICS_HOSTNAMES = new Set(['residenciafiscal.org', 'www.residenciafiscal.org']);

type GoogleAnalyticsCommand =
  | ['js', Date]
  | ['config', string]
  | ['event', string, { page_path: string; page_title: string }];

declare global {
  interface Window {
    dataLayer?: IArguments[];
    gtag?: (...args: GoogleAnalyticsCommand) => void;
    __residenciaFiscalGoogleAnalyticsInitialized?: boolean;
  }
}

export const isGoogleAnalyticsEnabled = ({
  hostname,
  search,
}: Pick<Location, 'hostname' | 'search'>): boolean =>
  GOOGLE_ANALYTICS_HOSTNAMES.has(hostname.toLowerCase()) &&
  !new URLSearchParams(search).has('synthetic_monitor');

const installGoogleAnalytics = () => {
  if (!isGoogleAnalyticsEnabled(window.location)) return;

  window.dataLayer = window.dataLayer ?? [];
  if (!window.gtag) {
    window.gtag = function gtag() {
      // biome-ignore lint/complexity/noArguments: gtag.js requires the Arguments object.
      window.dataLayer?.push(arguments);
    };
  }

  if (!window.__residenciaFiscalGoogleAnalyticsInitialized) {
    window.gtag('js', new Date());
    window.gtag('config', GOOGLE_ANALYTICS_ID);
    window.__residenciaFiscalGoogleAnalyticsInitialized = true;
  }

  if (document.getElementById(GOOGLE_ANALYTICS_SCRIPT_ID)) return;

  const script = document.createElement('script');
  script.id = GOOGLE_ANALYTICS_SCRIPT_ID;
  script.async = true;
  script.src = GOOGLE_ANALYTICS_SCRIPT_SRC;
  document.head.appendChild(script);
};

/** Installs GA4 once and records subsequent SPA route changes as page views. */
export const GoogleAnalyticsFooter = () => {
  const location = useLocation();
  const isInitialPage = useRef(true);

  useEffect(() => {
    installGoogleAnalytics();
  }, []);

  useEffect(() => {
    if (!isGoogleAnalyticsEnabled(window.location)) return;

    if (isInitialPage.current) {
      isInitialPage.current = false;
      return;
    }

    const pagePath = `${location.pathname}${location.search}${location.hash}`;
    window.gtag?.('event', 'page_view', {
      page_path: pagePath,
      page_title: document.title,
    });
  }, [location.hash, location.pathname, location.search]);

  return null;
};
```

