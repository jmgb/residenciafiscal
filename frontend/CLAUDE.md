# Frontend (residenciafiscal.org)

SPA React en `frontend/`, desplegada en Netlify. Chatbot que consulta el corpus
de sentencias en lenguaje natural.

## Rutas por jurisdicción

España es la primera instancia de la arquitectura común
`/<pais>/{fuentes,normativa,convenios,sentencias,doctrina}`. Los componentes y
generadores reutilizables reciben el código de jurisdicción y obtienen el slug
del catálogo mediante `jurisdictionPath()` o `jurisdictionSectionPath()`; no
concatenan `"/espana"` como regla. Una sección futura sin corpus publicable no se
materializa y devuelve 404. Decisión cerrada y gates:
[`docs/product/INTERNATIONAL_ARCHITECTURE.md`](../docs/product/INTERNATIONAL_ARCHITECTURE.md).

> Este fichero solo se carga al trabajar dentro de `frontend/`. Las reglas
> generales del repositorio (gates de CI, ficheros públicos, cross-review con
> Codex) están en el `CLAUDE.md` de la raíz.

## Trampas del stack

- El paquete de rutas es **`react-router`** v8, **no** `react-router-dom`:
  importar de `react-router-dom` falla, no está instalado.
- La gestión de dependencias es con `npm`. **No hay Makefile de frontend**; el de
  la raíz solo cubre la parte Python.
- Gate antes de commitear: `npm run fast-check` (lint + typecheck + tests),
  análogo al `make fast-check` de la raíz. El resto de scripts están en
  `package.json`.

## Puntos de entrada no evidentes

Cómo encontrar la documentación: el detalle vive en su `.md`; sigue el enlace de la línea-disparador o busca con `grep -ril "<tema>" ../docs/` (índice en [`docs/README.md`](../docs/README.md)).

- **Al tocar el motor del chat:** `src/lib/chat-engine.ts` es el punto **único** de selección del motor y solo `VITE_CHAT_MODE=live` elige el cliente real (cualquier otro valor conserva el stub). `src/lib/chat-answer-status.ts` es la fuente **única** de etiquetas de estado; `completa` **no se rotula** a propósito. El coste **no se pinta** en la interfaz. Para modificar el proxy Edge conservado: **todo `.ts` en la raíz de `netlify/edge-functions/` es un endpoint** (módulos compartidos en `lib/`); **`netlify-cli` no está y no debe añadirse**. Contrato de fuentes (`ChatSourceV2`), protocolo, V1 y Supabase: [`docs/operations/CHAT_DEPLOYMENT.md`](../docs/operations/CHAT_DEPLOYMENT.md#frontend-estado-del-motor-del-chat-y-contrato-de-fuentes).
- **Al tocar rutas, países, normativa, sentencias o SEO estático:** `src/data/jurisdictions.{json,ts}` y `treatyRelations.json` son proyecciones **generadas** por `src/export_frontend_projections.py` (editarlas a mano no sirve); `countryRoutes.json` ya no guarda `name` ni `treatyBoeId`; `contribution.ts` es la fuente única de la invitación a contribuir; el JSON-LD se emite dentro del árbol de React. Tabla completa de ficheros de entrada: [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md#frontend-puntos-de-entrada-no-evidentes).
- **Al tocar el corpus normativo en el frontend:** el articulado es texto legal literal; no se recorta, une ni reformatea en ninguna capa (si hay que abreviar, con CSS). Detalle: [`docs/normativa/NORMATIVA.md`](../docs/normativa/NORMATIVA.md#corpus-normativo-en-el-frontend).
- **Al tocar build, prerender, `netlify.toml` o caché:** **no hay hidratación** (`createRoot`); un módulo que toque `window` al importarse rompe el build; `inject-font-preload.mjs` va **antes** de `prerender.mjs` en el `postbuild`; el fallback `/*` devuelve `404.html` con 404 y toda ruta solo-SPA necesita su propia regla 200; las cabeceras se aplican por ruta pedida. Detalle: [`docs/operations/CACHE_AND_RELEASES.md`](../docs/operations/CACHE_AND_RELEASES.md#prerenderizado-el-html-se-sirve-con-contenido) y [§Caché y versión desplegada](../docs/operations/CACHE_AND_RELEASES.md#caché-y-versión-desplegada-frontend).

## Marca

La marca está documentada y tiene gate automático. Antes de producir cualquier
pieza visual o copy, consultar:

- [`docs/brand/brand-guidelines.md`](../docs/brand/brand-guidelines.md) — brandbook
  canónico: isotipo, color (tabla de contraste), tipografía, voz y vetos.
- [`docs/brand/manifiesto.md`](../docs/brand/manifiesto.md) — narrativa y manifiesto
  (versiones íntegra, corta y de una línea, con reglas de uso).

Fuentes únicas: `frontend/src/index.css` (tokens), `frontend/public/favicon.svg`
(isotipo), `frontend/src/assets/logo.svg` (lockup), `frontend/og/og-image.html`
(imagen OG). `favicon.ico`, `apple-touch-icon.png` y `og-image.png` son
**artefactos generados** (`npm run favicon` / `npm run og`): no editarlos a mano;
si cambia un token, regenerarlos en el mismo commit. El gate
`frontend/tests/brand-tokens.test.ts` (en `fast-check`) recalcula contrastes y
vigila HEX sueltos, escalas inexistentes y clases `control-*` sin definir.

`frontend/biome.json` necesita `css.parser.tailwindDirectives: true` (el CSS usa
`@theme`/`@apply` de Tailwind 4) y `css.formatter.quoteStyle: "single"` (coherente con
el JS). Sin lo primero biome aborta el parseo del CSS y el lint no revisa 6 de los 15
ficheros. Ojo: `biome.json` **no admite comentarios** `//`, aunque sea JSONC en otros
contextos.

## Despliegue y analítica

`netlify.toml` en la raíz del repo (`base = "frontend"`, `publish = "dist"`),
con Cloudflare por delante del dominio. Configuración de DNS, TLS, WAF y
verificación en [`docs/operations/NETLIFY.md`](../docs/operations/NETLIFY.md) y
[`docs/operations/CLOUDFLARE.md`](../docs/operations/CLOUDFLARE.md). Integración
de Google Analytics 4 documentada en [`docs/product/ANALYTICS.md`](../docs/product/ANALYTICS.md).

GA4 y PostHog comparten **una sola puerta**, `isGoogleAnalyticsEnabled`: hosts
canónicos, sin `?synthetic_monitor` y sin la marca de exclusión que deja
`?no_analytics=1` (`src/lib/analytics-optout.ts`). Al tocar cualquiera de las
dos analíticas, cambiar esa función y no duplicar la condición, o divergirán sin
que nadie se entere. El informe semanal que las lee está en
[`docs/operations/WEEKLY_TRAFFIC_REPORT.md`](../docs/operations/WEEKLY_TRAFFIC_REPORT.md).

El navegador llama al endpoint same-origin `/api/chat`. La V1 no necesita añadir
otro origen a `connect-src`; la alternativa futura Edge → FastAPI tampoco lo
expone directamente al navegador.
