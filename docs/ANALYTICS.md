# Analítica del frontend

El frontend usa Google Analytics 4 con la propiedad `G-XKX3N9KVJH`.

## Integración global

La integración vive en:

- `frontend/src/components/layout/GoogleAnalyticsFooter.tsx`: instala `gtag.js` una sola vez y registra los cambios de ruta de la SPA.
- `frontend/src/components/layout/SiteFooter.tsx`: footer común que monta el helper.
- `frontend/tests/SiteFooter.test.tsx`: comprueba que el script no se duplica y que se configura el ID correcto.

Todas las páginas deben renderizarse bajo `AppLayout`. El layout debe incluir
`<SiteFooter />` una sola vez, después de `<Outlet />`. Las páginas individuales
no deben importar `GoogleAnalyticsFooter` ni repetir el snippet.

```tsx
import { SiteFooter } from './SiteFooter';

// Dentro de AppLayout, bajo el Router:
<Outlet />
<SiteFooter />
```

El helper necesita estar dentro de un `react-router-dom` Router porque usa la
ruta actual para enviar `page_view` cuando cambia la navegación interna.

## Verificación

Desde `frontend/`:

```bash
npm test -- tests/SiteFooter.test.tsx
npm run typecheck
npx biome check .
```

En producción, comprobar en DevTools → Network que se cargan:

- `https://www.googletagmanager.com/gtag/js?id=G-XKX3N9KVJH`
- peticiones a `www.google-analytics.com` al abrir y navegar por el sitio.

Si Netlify aplica una CSP, `script-src` debe permitir
`https://www.googletagmanager.com` y `connect-src` debe permitir
`https://www.google-analytics.com`.

## Consentimiento

Si se incorpora un banner de consentimiento, `installGoogleAnalytics()` debe
llamarse únicamente después del consentimiento para analítica. La propiedad y
el componente están aislados para poder añadir ese gate sin modificar las
páginas.
