# Caché y versiones desplegadas

Cómo se garantiza que un navegador —sobre todo un móvil— acabe ejecutando la
última versión publicada, y por qué antes no lo hacía.

Piezas: `netlify.toml`, `frontend/scripts/build-version.mjs`,
`frontend/src/lib/app-version.ts`, `frontend/src/lib/useAppVersionGuard.ts`,
`frontend/src/lib/module-preload-recovery.ts`.
Gates: `tests/test_frontend_cache_policy.py`, `frontend/tests/app-version.test.ts`,
`frontend/tests/app-release.test.ts`, `frontend/tests/useAppVersionGuard.test.ts`,
`frontend/tests/module-preload-recovery.test.ts`, `frontend/tests/app-activity.test.ts`.

## El problema

Un móvil conserva la pestaña abierta durante días y la restaura desde el
back/forward cache sin volver a pedir el HTML. Una SPA, mientras esa pestaña
viva, sigue ejecutando el bundle con el que se cargó: no existe ningún momento
en el que se entere de que hay un deploy nuevo.

A eso se sumaban tres defectos de configuración medidos en producción el
2026-07-31:

1. **Un chunk borrado devolvía `200` con la shell HTML y cabeceras
   `immutable`.** El fallback `/* → /index.html` capturaba también `/assets/*`,
   y el bloque de cabeceras de `/assets/*` marcaba la respuesta cacheable un
   año. El navegador guardaba HTML disfrazado de JavaScript y la app quedaba
   rota en ese dispositivo hasta que caducase la caché.
2. **La regla de no-cachear el HTML no se aplicaba nunca.** Netlify hace match
   por la ruta pedida, no por el fichero servido: `for = "/index.html"` no cubre
   a quien entra por `/`, que es todo el mundo. El default de Netlify
   (`public,max-age=0,must-revalidate`) salvaba la situación por accidente.
3. **`/data/corpus.json` se servía con `max-age=3600`**, es decir, hasta una hora
   de corpus viejo garantizada después de cada deploy.

## Reglas de caché

| Ruta | Cache-Control | Por qué |
|---|---|---|
| `/`, `/index.html` | `public, max-age=0, must-revalidate` | El HTML decide qué bundle se carga. Sin `no-store`, que desactivaría el bfcache del móvil |
| `/assets/*` | `public, max-age=31536000, immutable` | Llevan hash en el nombre |
| `/data/*` | `public, max-age=0, must-revalidate` | No llevan hash y se regeneran en cada build. Tienen ETag: revalidar cuesta un 304 vacío |
| `/version.json` | `no-store` | Es lo que delata el deploy nuevo; cachearlo lo inutiliza |

Y dos redirecciones **antes** del fallback (que desde agosto de 2026 ya no
sirve la shell: devuelve `404.html` con 404 para que una URL inexistente no sea
un soft 404; `/consulta` y `/c/*` conservan su regla 200 propia):

```toml
[[redirects]]
  from = "/assets/*"
  to = "/404.html"
  status = 404
```

…y la equivalente para `/data/*`. Netlify solo aplica una redirección si el
fichero no existe, así que los assets reales se siguen sirviendo. `404.html` es
estático y sin JavaScript: se publica desde `frontend/public/`.

## Detección de versión en runtime

`build-version.mjs` publica `dist/version.json` con la revisión del despliegue.
La misma revisión se compila en el bundle como `__APP_RELEASE__`; las dos salen
de `frontend/scripts/release.mjs`, y `frontend/tests/app-release.test.ts` falla si
divergen. **El manifiesto no lleva fecha de build a propósito**: cambiaría en
cada compilación del mismo commit y provocaría recargas sin motivo.

`useAppVersionGuard`, montado en `AppLayout`, compara ambos valores al arrancar,
al recuperar el foco la pestaña (`visibilitychange`) y al volver del bfcache
(`pageshow` con `persisted`), con un intervalo mínimo de 30 s entre
comprobaciones.

Cuando hay versión nueva:

- **sin nada en curso** → recarga silenciosa;
- **con algo en curso** → `AppUpdateBanner` avisa y decide el usuario.

«Algo en curso» lo define `hasWorkInProgress()`: una respuesta todavía llegando
(`isStreaming`, incluidas las respuestas comparadas activas) o el foco en un campo
editable, porque el borrador del composer vive solo en su estado local.

Todo fallo se traduce a «no hay nada nuevo»: una falsa alarma recarga la página
en la cara del usuario y, si el manifiesto no fuese fiable, se repetiría en
bucle. Por eso también se descarta una respuesta cuyo `Content-Type` no sea JSON
—sería el `404.html` del fallback— y no se compara nada cuando el release es `local`,
que es lo que devuelve el cálculo fuera de un despliegue.

## Red de seguridad: `vite:preloadError`

Si el HTML es viejo y pide un chunk que ya no existe, Vite emite
`vite:preloadError` y la vista se queda a medias. `installModulePreloadRecovery`
—instalado en `main.tsx` antes de montar React— recarga una vez y solo una por
bundle: la marca vive en `sessionStorage`, de modo que si tras recargar vuelve a
fallar, el problema es otro e insistir sería un bucle de recargas.

## Comprobar en producción

```bash
curl -sI https://residenciafiscal.org/ | grep -i cache-control
curl -sI https://residenciafiscal.org/assets/no-existe.js | grep -iE '^(HTTP|cache-control)'
curl -s  https://residenciafiscal.org/version.json
```

Lo esperado: `max-age=0, must-revalidate` en el HTML, **404** en el asset
inexistente (no un 200 con HTML) y un JSON con la revisión desplegada.

## Trampas

- Los headers de Netlify se resuelven por **ruta pedida**. Añadir una regla para
  un fichero (`/algo/index.html`) no cubre la URL por la que entra la gente.
- No poner `Cache-Control` en el bloque `/*`: coincidiría con `/assets/*` y el
  resultado de dos reglas que definen la misma cabecera no está garantizado.
- `no-store` en el HTML desactiva el back/forward cache en varios navegadores.
  No hace falta: la comprobación en runtime cubre ese caso sin penalizar la
  navegación atrás.
- Cloudflare está por delante y sirve el HTML como `DYNAMIC` (no lo cachea). Si
  algún día se activase caché de HTML ahí, habría que purgarla en cada deploy.


## Prerenderizado: el HTML se sirve con contenido

> Movido desde `frontend/CLAUDE.md` el 2026-11-10 (allí queda un resumen con enlace aquí).

## Prerenderizado: el HTML se sirve con contenido

`npm run build` genera **dos** bundles. El de siempre para el navegador y uno de
servidor (`npm run build:ssr` → `dist-ssr/entry-server.js`, no versionado) que
`scripts/prerender.mjs` usa en el `postbuild` para renderizar cada ruta pública
a HTML y escribirla dentro de `<div id="root">`.

Antes el HTML era la shell vacía: sin JavaScript no había una sola línea de
texto, así que un buscador que no ejecute el bundle indexaba páginas en blanco.
Ahora `/francia` se sirve con su `h1`, el convenio, el artículo literal y el
enlace al BOE —unos 8 KB de texto— y en el navegador se monta encima la misma
aplicación de siempre.

Cuatro cosas que conviene saber antes de tocarlo:

- **No hay hidratación.** `main.tsx` sigue usando `createRoot`, que descarta el
  markup y vuelve a pintar. Es deliberado: `hydrateRoot` exigiría que el primer
  render del cliente coincidiera con el del build, y los datos que llegan por
  `fetch` no coinciden nunca.
- **Los efectos no corren en el build.** Cualquier contenido que dependa de un
  `useEffect` sale como su estado de carga. Por eso el convenio se pasa resuelto
  vía `TreatyPreloadContext` (`src/lib/treaty-preload.ts`), y viaja embebido en
  un `<script type="application/json">` para que el navegador no lo repida ni el
  visitante lo vea desaparecer al montar.
- **Un módulo que toque `window` al importarse rompe el build**, no la página:
  el árbol entero se ejecuta en Node. `tests/entry-server.test.tsx` lo detecta
  sin necesidad de build.
- **El `preload` de las fuentes se inyecta antes de prerenderizar.** Las dos
  familias se autoalojan (`@fontsource-variable/*` en `main.tsx`) y vite emite
  sus woff2 con hash, así que `index.html` no puede declararlas a mano:
  `scripts/inject-font-preload.mjs` las lee del CSS compilado y escribe las
  etiquetas en `dist/index.html`. Va **antes** de `prerender.mjs` en el
  `postbuild` porque cada copia por ruta se saca de esa shell; invertir el orden
  deja las ~150 páginas sin `preload` y solo lo delata una auditoría de LCP.
- **`vite.config.ts` desactiva el plugin de Sentry en el build SSR**
  (`isSsrBuild`): ese bundle no se despliega, así que subir sus sourcemaps sería
  publicar un artefacto que ningún error puede mencionar.


## Caché y versión desplegada (frontend)

> Movido desde `frontend/CLAUDE.md` el 2026-11-10 (allí queda un resumen con enlace aquí).

## Caché y versión desplegada

Una SPA no vuelve a pedir el HTML mientras la pestaña viva, y un móvil conserva
la pestaña días. Por eso el shell monta `AppUpdateBanner`, que compara
`__APP_RELEASE__` con `/version.json` al arrancar, al recuperar el foco y al
volver del back/forward cache: recarga sola si no hay nada en curso y avisa si
lo hay. `main.tsx` instala además la recuperación de `vite:preloadError`, que
recarga **una vez por bundle** cuando falta un chunk del deploy anterior.

Dos trampas antes de tocar `netlify.toml`: sus cabeceras se aplican por **ruta
pedida** (una regla para `/index.html` no cubre `/`), y el fallback `/*` **ya no
sirve la shell**: devuelve `404.html` con 404, porque toda ruta pública tiene
fichero prerenderizado y una URL inexistente servida con 200 era un soft 404
(la shell además es `noindex`). Las únicas rutas sin fichero físico —`/consulta`
y `/c/*`— tienen su propia regla 200 antes del fallback; si añades otra ruta
solo-SPA, necesita la suya o morirá con 404. Contrato completo, tabla de rutas y
verificación en producción:
[`docs/operations/CACHE_AND_RELEASES.md`](CACHE_AND_RELEASES.md).
