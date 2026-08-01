# Analítica del frontend

El sitio mide con **dos** analíticas a la vez: Google Analytics 4 (propiedad
`G-XKX3N9KVJH`) y PostHog (proyecto «Residencia Fiscal», organización europea).
No es redundancia: cuentan cosas distintas y su divergencia es el dato. En la
primera semana GA4 vio 81 usuarios y PostHog 1, porque GA4 registra bots que
ejecutan JavaScript y PostHog apenas los ve. Por eso el informe semanal publica
una línea por analítica y no las promedia
([`operations/WEEKLY_TRAFFIC_REPORT.md`](../operations/WEEKLY_TRAFFIC_REPORT.md)).

## Integración global

| Fichero | Qué hace |
|---------|----------|
| `frontend/src/components/layout/GoogleAnalytics.tsx` | Instala `gtag.js` una sola vez y registra los cambios de ruta de la SPA |
| `frontend/src/components/layout/PostHogAnalytics.tsx` | Instala `array.js`, registra `$pageview` por ruta y expone `trackEvent()` |
| `frontend/src/lib/analytics-optout.ts` | Exclusión permanente de un navegador mediante `?no_analytics=1` |
| `frontend/tests/PostHogAnalytics.test.tsx` | Comprueba la puerta de activación, el proyecto europeo y la vista inicial |

Las dos se montan **una sola vez** dentro de `AppLayout`, bajo el Router: ambas
usan la ruta actual para enviar la vista de página cuando cambia la navegación
interna. Ninguna página individual debe montarlas ni repetir el snippet.

### Una sola puerta de activación

`isGoogleAnalyticsEnabled` decide por las dos —`isPostHogEnabled` es esa misma
función reexportada, no una copia—. Deja fuera:

- todo lo que no sea `residenciafiscal.org` o `www.residenciafiscal.org`
  (localhost y deploy previews incluidos);
- las visitas con `?synthetic_monitor=1`, que son las del monitor externo;
- los navegadores marcados con `?no_analytics=1`, que es como se excluyen las
  visitas propias. La marca vive en `localStorage`, no en una lista de IP,
  porque la IP doméstica es dinámica y no cubre los datos móviles.
  `?no_analytics=0` la retira.

**Al tocar una analítica hay que tocar esa función, no duplicar la condición**,
o las dos divergirán sin que nadie se entere.

### Vistas de página

Las dos desactivan el pageview automático del SDK y lo emiten desde el efecto de
ruta. En una SPA el automático solo vería la carga inicial y perdería toda la
navegación interna. PostHog usa además `person_profiles: 'identified_only'`, así
que un visitante anónimo no genera perfil.

## Variables de entorno

**El frontend no lee ninguna.** El identificador de GA4 y la clave de proyecto de
PostHog están en el código porque son públicos por diseño: viajan en el bundle y
cualquiera puede leerlos en el navegador. Ponerlos en un `VITE_*` daría una falsa
sensación de secreto sin ocultar nada.

Las variables `POSTHOG_*` del `.env` son de **servidor** y no participan en la
captura: las usa el informe semanal de tráfico para consultar la API de PostHog.

| Variable | Ámbito | Nota |
|----------|--------|------|
| `POSTHOG_QUERY_HOST` | Informe semanal | Host de consulta (`https://eu.posthog.com`), distinto del de ingesta |
| `POSTHOG_PROJECT_ID` | Informe semanal | Proyecto sobre el que se consulta |
| `POSTHOG_PERSONAL_API_KEY` | Informe semanal | Credencial de lectura. **Nunca** con prefijo `VITE_` |

## Verificación

Desde `frontend/`:

```bash
npm test -- tests/PostHogAnalytics.test.tsx
npm run fast-check
```

En producción, comprobar en DevTools → Network que se cargan:

- `https://www.googletagmanager.com/gtag/js?id=G-XKX3N9KVJH` y peticiones a
  `www.google-analytics.com`;
- `https://eu.i.posthog.com/static/array.js` y peticiones a `eu.i.posthog.com`.

Si Netlify aplica una CSP, `script-src` debe permitir
`https://www.googletagmanager.com` y `https://eu.i.posthog.com`; `connect-src`,
`https://www.google-analytics.com` y `https://eu.i.posthog.com`.

## Consentimiento

Si se incorpora un banner de consentimiento, la instalación de las dos analíticas
debe quedar detrás de él. Están aisladas en sus componentes y comparten puerta,
así que el gate se añade en un único punto sin tocar las páginas.

## Explotación de los datos

Este documento cubre la **captura** en el navegador. El informe semanal que lee
esos datos y los manda por Telegram cada lunes está en
[`operations/WEEKLY_TRAFFIC_REPORT.md`](../operations/WEEKLY_TRAFFIC_REPORT.md).
