# Frontend (residenciafiscal.org)

SPA React en `frontend/`, desplegada en Netlify. Chatbot que consulta el corpus
de sentencias en lenguaje natural.

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

| Ruta | Por qué importa |
|---|---|
| `src/lib/chat-engine.ts` | Punto **único** de selección del motor. Es el fichero a cambiar al conectar el backend |
| `src/lib/corpus.ts` | Degrada a corpus vacío si falla la carga, en vez de romper la app |
| `scripts/build-corpus.mjs` | Genera `public/data/corpus.json` desde `output/analisis_*.jsonl` en el prebuild |

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

## Estado del motor

El chat funciona hoy con un **stub**. `chatEngineMode` en
`src/lib/chat-engine.ts` vale `'stub'`, lo que activa el aviso de contenido
simulado en la UI. Al conectar el backend real hay que cambiarlo a `'live'`,
que apaga el aviso automáticamente.

**El backend ya está decidido, diseñado y con la plataforma validada**: una
Netlify Edge Function en `/api/chat` que recupera por facetas del corpus y
streamea por SSE resolviendo marcadores `[S<n>]` a ROJ reales en el servidor.
No sigue abierta la elección entre FastAPI, file_search o pgvector.

- Diseño: `docs/superpowers/specs/2026-07-29-chat-backend-design.md`
- Plan de ejecución: `docs/superpowers/plans/2026-07-29-chat-backend.md`
- Límites de plataforma medidos: [`docs/operations/NETLIFY_EDGE.md`](../docs/operations/NETLIFY_EDGE.md)

Si vas a escribir la edge function, lee primero el último: tiene tres trampas
que cuestan un deploy cada una. La más cara es que **todo `.ts` en la raíz de
`netlify/edge-functions/` es un endpoint** —el prefijo `_` no exime—, así que
los módulos compartidos van en `lib/`.

Está **bloqueado en la fase 0b**: el mecanismo de cuotas y presupuesto necesita
una decisión, porque el compare-and-swap de Netlify Blobs no es atómico. Ver
`docs/tasks.md`.

Las dependencias del backend (`openai`, `zod`, `@netlify/blobs`,
`@netlify/edge-functions`) ya están instaladas y verificadas en Deno.
`netlify-cli` **no** está y no debe añadirse: no arranca contra el TypeScript 7
del repositorio.

## Despliegue y analítica

`netlify.toml` en la raíz del repo (`base = "frontend"`, `publish = "dist"`),
con Cloudflare por delante del dominio. Configuración de DNS, TLS, WAF y
verificación en [`docs/operations/NETLIFY.md`](../docs/operations/NETLIFY.md) y
[`docs/operations/CLOUDFLARE.md`](../docs/operations/CLOUDFLARE.md). Integración
de Google Analytics 4 documentada en [`docs/ANALYTICS.md`](../docs/ANALYTICS.md).

Al conectar el backend real hay que ampliar `connect-src` en la CSP de
`netlify.toml` con el origen de la API.
