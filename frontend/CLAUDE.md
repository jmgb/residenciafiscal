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
| `src/lib/normativa.ts` | Corpus normativo: índice ligero + articulado bajo demanda, un fichero por precepto |
| `scripts/build-normativa.mjs` | Genera `public/data/normativa.json` y `public/data/preceptos/*.json` desde `knowledge/normativa/es/` |
| `src/lib/contribution.ts` | Fuente **única** de la invitación a contribuir: URL del repo, correo de contacto, ruta `/colaborar` y los seis `EXPERT_PROFILES`. Los comparten `/colaborar` y las páginas de país sin corpus, y `tests/test_contribucion_perfiles.py` ata los perfiles a la tabla de `CONTRIBUTING.md` |
| `src/data/countryRoutes.json` | Fuente única de jurisdicciones: `corpusStatus` gobierna disponibilidad, `indexable` gobierna solo SEO y `legalReferences` conserva citas, fuentes oficiales y `reviewedAt`. La fecha refleja una comprobación editorial real, nunca la fecha del build |
| `src/data/staticRoutes.{json,ts}` | Metadatos SEO de las rutas de contenido estático (`/manifiesto`, `/metodologia`, `/espana/fuentes`, `/colaborar`, `/privacidad`). Los leen la página, `scripts/prerender.mjs` y `scripts/build-sitemap.mjs`, para que el bot y la SPA no puedan discrepar. `/espana/fuentes` es contenido de país (fuentes + normativa de España); la metodología es común a todas las jurisdicciones |

## Corpus normativo

El frontend sirve también el texto de la ley, no solo las sentencias. Dos
niveles a propósito: `normativa.json` es el índice de los 108 preceptos (~100 KB)
y `preceptos/<slug>.json` el articulado literal de uno solo. Cargar los 108
juntos serían ~480 KB para que alguien lea el artículo 9 LIRPF.

**El articulado es texto legal literal.** No se recorta, une ni reformatea en
ninguna capa del frontend: `tests/normativa.test.ts` comprueba que cada párrafo
publicado aparece tal cual en el Markdown de origen. Si hay que abreviar para la
UI, se abrevia con CSS, no tocando la cadena.

La fuente se regenera desde la raíz con `make export-normativa` y
`make enlazar-normativa`; `build-normativa.mjs` corre en el `prebuild` y, si no
encuentra `knowledge/normativa/es/`, conserva lo versionado y avisa por stderr en
lugar de romper el build. Contrato y decisiones:
[`docs/normativa/NORMATIVA.md`](../docs/normativa/NORMATIVA.md).

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

Producción funciona hoy con un **stub**. `src/lib/chat-engine.ts` es el selector
único: solo `VITE_CHAT_MODE=live` elige el cliente real; cualquier valor ausente
o inesperado conserva el stub. El modo real mantiene un aviso de investigación
experimental, privacidad y revisión de fuentes; no reutiliza el aviso de
contenido simulado.

### Contrato de fuentes

`src/types/chat.ts` define `ChatSourceV2`: cada cita nueva debe incluir
`sourceId`, cuestión jurídica, anclaje, página física, página impresa opcional,
extracto literal, fidelidad, SHA-256 del PDF y estado de revisión técnica y
jurídica. `src/lib/chat-source.ts` es el validador canónico del navegador.

La persistencia usa schema interno 3 y conserva los historiales previos como
`LegacyChatSource`. No se deben rellenar sus campos ausentes por inferencia: la
UI los rotula como fuentes históricas sin anclaje v2. El stub solo produce ese
tipo legado porque sus extractos son resúmenes simulados.

El protocolo 2 conserva compatibilidad con la respuesta individual anterior y
añade el modo comparativo estricto A → B: `answer_start`, tokens y fuentes con
`strategy`, `answer_done` con coste decimal y un único terminal global. Las
fuentes comparativas usan `ChatStrategySource` —estrategia, sentencia, página,
hash y cita exacta—; no se convierten artificialmente en `ChatSourceV2` porque B
no dispone de cuestión y anclaje canónicos. `ChatMessage.answers` mantiene los
dos bloques y el schema 3 apaga cualquier streaming huérfano al rehidratar.

El runtime V1 implementado es una Netlify Function TypeScript autosuficiente.
Ejecuta A y B en paralelo, conserva el orden visual A → B, mantiene Luna `high`
y cancela antes del límite de 60 s. Python sigue preparando el corpus offline.
El prototipo Edge → FastAPI no se borra y se conserva como evolución futura si
hacen falta llamadas de más de 60 s o mayor control operativo. Código y operación:
[`docs/operations/CHAT_DEPLOYMENT.md`](../docs/operations/CHAT_DEPLOYMENT.md).

La estrategia de recuperación se debe medir con dos respuestas independientes:
la actual, basada en el corpus v3 estructurado, y Gemini File Search sobre los
PDF de la muestra. Cada respuesta mantiene sus propias fuentes, errores,
métricas y coste visible en USD. No se ha adoptado `pgvector`; una unión futura
de candidatos con reranking local solo se evaluará después de esta comparación.

- Diseño: `docs/superpowers/specs/2026-07-29-chat-backend-design.md`
- Plan de ejecución: `docs/superpowers/plans/2026-07-29-chat-backend.md`
- Contrato de la comparación:
  [`docs/jurisprudence/CHAT_RETRIEVAL_STRATEGY_COMPARISON.md`](../docs/jurisprudence/CHAT_RETRIEVAL_STRATEGY_COMPARISON.md)
- Límites de plataforma medidos: [`docs/operations/NETLIFY_EDGE.md`](../docs/operations/NETLIFY_EDGE.md)

Si vas a modificar el proxy Edge conservado, lee primero el último: tiene tres
trampas que cuestan un deploy cada una. La más cara es que **todo `.ts` en la
raíz de `netlify/edge-functions/` es un endpoint** —el prefijo `_` no exime—,
así que sus módulos compartidos van en `lib/`. No extrapoles automáticamente
esas reglas al directorio de Functions estándar de la V1.

La V1 usa Supabase/Postgres mediante dos RPC transaccionales y bloqueo de fila;
no usa el compare-and-swap no atómico de Blobs. `private.chat_messages` conserva
la pregunta y una respuesta por estrategia, incluidas citas y costes, sin IP ni
user-agent. Solo la Function usa `SUPABASE_SECRET_KEY`; el navegador no accede a
Supabase. Contrato: `docs/operations/SUPABASE_CHAT.md`. La activación productiva
sigue condicionada por el Deploy Preview y la política legal de `TASKS.md`.

El prototipo Edge está conservado en `netlify/prototypes/`. La Function estándar
y sus adaptadores viven en `netlify/functions/chat/`; devuelve el protocolo SSE
2 como cuerpo bufferizado, no como `ReadableStream`.
`netlify-cli` **no** está y no debe añadirse: no arranca contra el TypeScript 7
del repositorio.

## Caché y versión desplegada

Una SPA no vuelve a pedir el HTML mientras la pestaña viva, y un móvil conserva
la pestaña días. Por eso el shell monta `AppUpdateBanner`, que compara
`__APP_RELEASE__` con `/version.json` al arrancar, al recuperar el foco y al
volver del back/forward cache: recarga sola si no hay nada en curso y avisa si
lo hay. `main.tsx` instala además la recuperación de `vite:preloadError`, que
recarga **una vez por bundle** cuando falta un chunk del deploy anterior.

Dos trampas antes de tocar `netlify.toml`: sus cabeceras se aplican por **ruta
pedida** (una regla para `/index.html` no cubre `/`), y el fallback `/*` captura
también `/assets/*`, de modo que sin una regla de 404 previa un chunk borrado se
cachea un año como HTML. Contrato completo, tabla de rutas y verificación en
producción: [`docs/operations/CACHE_AND_RELEASES.md`](../docs/operations/CACHE_AND_RELEASES.md).

## Despliegue y analítica

`netlify.toml` en la raíz del repo (`base = "frontend"`, `publish = "dist"`),
con Cloudflare por delante del dominio. Configuración de DNS, TLS, WAF y
verificación en [`docs/operations/NETLIFY.md`](../docs/operations/NETLIFY.md) y
[`docs/operations/CLOUDFLARE.md`](../docs/operations/CLOUDFLARE.md). Integración
de Google Analytics 4 documentada en [`docs/product/ANALYTICS.md`](../docs/product/ANALYTICS.md).

El navegador llama al endpoint same-origin `/api/chat`. La V1 no necesita añadir
otro origen a `connect-src`; la alternativa futura Edge → FastAPI tampoco lo
expone directamente al navegador.
