# Histórico cerrado del proyecto

Hitos trasladados desde `TASKS.md` el 2026-11-15. No son tareas pendientes
ni sustituyen los contratos y guías operativas vigentes. Se conserva su texto
histórico porque documenta decisiones y evidencia; ninguna subtarea abierta
se ha movido aquí. El histórico específico del chat sigue en
[`TASKS_ARCHIVE_CHAT.md`](TASKS_ARCHIVE_CHAT.md).

## Prioridad alta

- [x] **Rotar el token de Sentry filtrado en la historia de git.** El token real
  commiteado dentro de `.mcp.json` el 2026-03-19 (commits `13dc89c` y
  `098e492`) se revocó y sustituyó el 2026-07-29. La variable canónica vigente
  es `SENTRY_TOKEN`.
  - Purgar la historia **no sustituye a rotar**: un force-push no borra el objeto
    del servidor, que sigue siendo alcanzable por su SHA. El secreto histórico
    permanece documentado como revocado.

- [x] Mantener un único `.env` en la raíz: `frontend/.env` ya no existe y Vite
  carga la configuración desde el directorio raíz.

- [x] Verificar el deploy público de `https://residenciafiscal.org/`: home y recursos
  públicos responden correctamente detrás de Netlify y Cloudflare, también desde EE. UU.

- [x] Implementar la ruta pública `/metodologia` con el método, el corpus de 106
  sentencias y sus limitaciones.

- [x] Añadir `/metodologia` a `frontend/public/sitemap.xml`
  y enlazarla desde `frontend/public/llms.txt`.

- [x] **P1 — Primera ampliación de rutas de país por presencia en el corpus**
  (1 de agosto de 2026). Se añadieron cinco: **Mónaco** (`/monaco`, sin
  convenio), **Marruecos**, **Rusia**, **Emiratos Árabes Unidos** y **Kuwait**.
  Son las jurisdicciones que más aparecen en las resoluciones y no tenían ruta.
  Cada una es una entrada en `countryRoutes.json` (`name`, `code`, `path`,
  `treatyBoeId`, `title`, `description`, `sitemap`); el bloque del convenio, el
  prerenderizado, los redirects y el sitemap salen solos. Contrato en
  [`COUNTRY_PAGES.md`](../product/COUNTRY_PAGES.md).

  **Dos correcciones al criterio que estaba escrito aquí**, ambas medidas:

  1. **La saga de becarios infla el recuento por menciones.** 31 de las 106
     sentencias son el mismo pleito —becas ICEX y ausencias esporádicas— y en
     ellas el país es el destino de la beca, no la jurisdicción en disputa. Eso
     descarta Kenia, Taiwán, Irán, Túnez, Egipto, Corea del Sur, Ucrania,
     Noruega, Rumanía, Israel, China, Turquía, Arabia Saudí, Dinamarca y
     Bélgica: una sentencia cada uno, misma doctrina, sin análisis de su
     convenio. El campo fiable es `judgment.countries`, no contar el nombre del
     país en el texto.
  2. **Una ruta nueva no trae hoy ni una sentencia a la página.** El bloque «lo
     aplican N sentencias» de `TaxTreaty.tsx` sale de `normativa.json`, y solo
     cuatro preceptos de convenio tienen sentencias enlazadas: Reino Unido (4),
     Suiza (2), EE. UU. (1) y el CDI argentino de 1992 (1). Mientras 41 de las
     106 no citen ningún artículo en su registro estructurado, una página nueva
     es el articulado del convenio y nada más.

  Quedan fuera y necesitan trabajo previo, no una entrada en JSON: **Gibraltar**
  (el acuerdo fiscal de 2019 no está en `normativa/es/`), **Guinea Ecuatorial**
  (sin convenio) y **Ucrania** (solo existiría el convenio con la URSS de 1986,
  `BOE-A-1986-25055`, y aplicárselo hay que verificarlo, no deducirlo).

## Producto y arquitectura

- [x] Diseñar las landings por país con un modelo de datos reutilizable, URLs canónicas
  ASCII (`/espana`, `/portugal`, etc.) y redirecciones para variantes con caracteres especiales.
  Cerrado el 2 de agosto de 2026 con `countryRoutes.json`, constructores compartidos,
  prerender, sitemap y redirects generados; el enriquecimiento editorial queda separado.

- [x] Definir el contrato del endpoint de chat, manejo de errores, cancelación de peticiones,
  límites de uso y estrategia de fallback del proveedor LLM. Cerrado en las secciones 5 y 6
  del diseño: eventos SSE, los dos `429` (el del limitador nativo llega sin ejecutar la
  función y no es SSE), `502` antes del primer token frente a `event: error` a mitad de
  stream, cancelación por `AbortSignal` y degradación a búsqueda léxica si el router falla.

## Corpus normativo

- [x] **Completar la tabla país → convenio** (cerrada por otra vía; verificado el
  12 de agosto de 2026). La entrada describía un problema real —`CONVENIOS_POR_PAIS`
  mapeaba a mano 16 de los 98 convenios, así que el «art. 4 CDI» de una sentencia
  sobre Portugal o Italia no habría resuelto—, pero el registro bilateral lo
  resolvió sin que nadie lo marcara aquí: la tabla **ya no se cura a mano**, se
  deriva de `src/treaty_relations_es.json` (`src/normativa_citas.py:112`,
  commit `9ed452e`). Medido hoy: 110 grafías → **97 convenios alcanzables**.
  - El test de cierre que esta entrada exigía —«ningún convenio publicado sin
    alias»— también existe:
    `test_el_registro_cubre_todos_los_convenios_generales` en
    `tests/test_treaty_relations.py:77`, que compara el registro con el
    manifiesto y falla ante cualquier hueco.
  - **Sigue rigiendo la regla que motivaba la tabla curada**: el país sale del
    campo `titulo` de `normativa/es/manifest.json`, verificado uno a uno, nunca
    deducido con una regex — los convenios escriben el país de trece formas
    distintas y equivocarlo enlazaría una sentencia con el derecho de otro
    Estado. Lo que cambió es dónde vive esa curación, no que se pueda automatizar.
  - Los países con convenio antiguo y moderno se resuelven por el rango de
    ejercicios de `ConvenioPais`, igual que antes.

- [x] **Guardarraíl contra la pérdida silenciosa de una norma al redescargar.**
  `descargar_normativa.py` reescribe `manifest.json` desde cero y descubre los
  convenios vigentes filtrando por título el índice del BOE. Si España denuncia
  un convenio, la siguiente descarga simplemente lo omite, `export_normativa`
  publica un precepto menos y **el test de «corpus al día» pasa**, porque compara
  la salida con la entrada nueva. La pérdida no la ve nadie.
  - Implementado el 4 de agosto de 2026: una descarga completa compara el
    manifiesto anterior y falla antes de sobrescribirlo ante cualquier
    desaparición no declarada. Si la norma sigue citándose se añade a
    `CDI_DEROGADO`; si deja de ser necesaria se registra con motivo en
    `BAJAS_DECLARADAS`.
  - Cubierto por `tests/test_descargar_normativa.py` (10 tests verdes).

## SEO y contenido

- [x] **La raíz `/` servía una página en blanco y no era canónica de nada**
  (medido y resuelto el 1 de agosto de 2026). `dist/index.html` conserva el
  `<div id="root">` **vacío** —el prerenderizado escribe una copia por ruta en su
  subdirectorio, pero no toca la shell—, declaraba `canonical` hacia sí misma y
  no está en el sitemap: la home era una URL sin contenido que no apuntaba a
  `/espana`. Ahora `netlify.toml` la redirige con un `301` a `/espana`, que es la
  que el sitemap publica con prioridad `1.0`. `force` es imprescindible, porque
  el fichero existe y Netlify lo serviría antes que la redirección;
  `tests/test_frontend_cache_policy.py` lo fija junto al orden respecto al
  fallback `/*`.
  - [x] **Verificado el 4 de agosto de 2026**: el monitor `803628459` de
    UptimeRobot está `UP` y la raíz responde `301` hacia `/espana` con el
    User-Agent del monitor ([`UPTIMEROBOT.md`](../operations/UPTIMEROBOT.md)).

- [x] Marcar con `BreadcrumbList` las rutas estáticas indexables `/manifiesto`,
  `/metodologia` y `/colaborar`, además de `/espana/fuentes`, que cuelga de
  España. `/privacidad` queda fuera por ser `noindex`: los datos estructurados
  son para el buscador. `tests/entry-server.test.tsx` recorre las rutas
  indexables y comprueba además que lo `noindex` no emite nada.

- [x] Añadir metadatos, canonical, Open Graph y enlaces internos específicos para cada
  landing de país (1 de agosto de 2026): `title` y `description` propios en
  `countryRoutes.json`, prerenderizados por ruta y con las 34 en el sitemap.
  El marcado `schema.org` queda cerrado en la tarea siguiente.

- [x] Marcar cada landing de país con datos estructurados (`schema.org`) (1 de agosto de
  2026): `BreadcrumbList` en `CountryPage` y en `SpainPage` —`/espana` monta el chat y
  no la plantilla compartida, así que se quedaba fuera siendo la landing de mayor
  prioridad— y `Legislation` en `TaxTreaty`, este último solo cuando el convenio de
  **esa** página está resuelto: al navegar entre países, el render previo al efecto
  llegaba a declarar el convenio de la jurisdicción anterior. Sin `FAQPage` ni
  `Article`. Se componen en
  `frontend/src/lib/structured-data.ts`, se emiten desde el árbol de React —así el HTML
  prerenderizado y la SPA no divergen— y `tests/entry-server.test.tsx` comprueba que
  llegan al HTML servido. La fecha se publica como `legislationDateVersion`, nunca como
  `legislationDate`: el corpus conoce la redacción vigente, no la firma del convenio.
  Contrato en [`COUNTRY_PAGES.md`](../product/COUNTRY_PAGES.md).

- [x] Mostrar en cada landing las fuentes legales del convenio con España: título oficial,
  artículo de residencia, redacción vigente, texto literal y enlace al BOE, o la
  declaración explícita de que no hay convenio en vigor. Todo sale del corpus normativo
  versionado, así que el «proceso editorial» es regenerarlo (`make export-normativa`).
  Alcance y limitaciones siguen en la propia página: no hay jurisprudencia de ese país.

## Colaboración internacional

- [x] **Crear la etiqueta `corpus` en el repositorio** y añadirla a
  `labels:` de la plantilla (4 de agosto de 2026). La plantilla aplica ahora
  `help wanted` y `corpus`; cambio publicado en `f39ba835a64dab7a4901b17213238b1b5949901e`.

## Seguridad y datos

- [x] Añadir validación automática del schema del corpus, detección de duplicados y
  trazabilidad de cada criterio hasta su sentencia de origen.

## Calidad y despliegue

- [x] Configurar CI con lint, typecheck, tests y build del frontend y la API.

- [x] Documentar y automatizar el pipeline reproducible de actualización del corpus y su deploy.

- [x] **Corregir `CLAUDE.md`, desfasado respecto al código.** Ya documenta los
  siete resultados finales y marca como desfasada la tabla histórica de costes;
  las tarifas vigentes proceden exclusivamente del catálogo versionado de
  `llm_gateway`.

## SEO y operación

- [x] Configurar Sentry para la API y el frontend y documentar sus variables de
  entorno (`c0fb582`), reflejado en `README.md` y `CLAUDE.md` el 1 de agosto de
  2026 con la tabla de variables. El límite que describía esta entrada —«la
  Netlify Function del chat no está instrumentada»— **ya no rige**: la Function
  manda a su propio proyecto `residencia-fiscal-chat` desde el 1 de agosto y
  quedó activada en producción el 2 de agosto
  ([`CHAT_OBSERVABILITY.md`](../operations/CHAT_OBSERVABILITY.md)).

- [x] Configurar PostHog para el frontend y documentar sus variables de entorno.
  Estaba implementado (`PostHogAnalytics.tsx`, montado una vez en `AppLayout`, con
  su suite) y sin documentar; documentado el 1 de agosto de 2026 en
  [`ANALYTICS.md`](../product/ANALYTICS.md) junto a GA4. **El frontend no lee
  ninguna variable**: el ID de GA4 y la clave de proyecto de PostHog son públicos
  por diseño y viajan en el bundle; las `POSTHOG_*` del `.env` son de servidor y
  las usa el informe semanal. La puerta de activación es única
  (`isGoogleAnalyticsEnabled`) para las dos analíticas.

- [x] Tras un deploy correcto, comprobar que `robots.txt`, `sitemap.xml` y `llms.txt`
  devuelven `200` desde `https://residenciafiscal.org/`.

- [x] **Autoalojar Space Grotesk e Inter** (2 de agosto de 2026, punto 8 de
  [`SEO_AUDIT.md`](../product/SEO_AUDIT.md)). Salían de Google Fonts: dos
  conexiones a un tercero y una hoja de estilo bloqueante delante del primer
  pintado, más dos excepciones en la CSP. Ahora vienen de
  `@fontsource-variable/*` (`src/main.tsx`) y la CSP queda en `font-src 'self'`
  y `style-src 'self' 'unsafe-inline'`.
  - **Un fichero por familia, no uno por peso.** Son las versiones variables
    (`wght` 100–900 y 300–700): 48 KB de Inter y 22 KB de Space Grotesk cubren
    los siete pesos del brandbook. Los otros seis subconjuntos viajan en el
    deploy, pero su `unicode-range` los deja sin pedir.
  - **El `preload` no puede escribirse en `index.html`**: el woff2 emitido lleva
    hash de contenido. Lo inyecta `scripts/inject-font-preload.mjs` leyendo el
    CSS ya compilado, y va **antes** de `prerender.mjs` en el `postbuild` porque
    de esa shell salen las ~150 copias por ruta. Solo precarga los dos
    subconjuntos `latin`, que son los que pinta el castellano.
  - **No se afirma mejora de LCP**: sin datos de campo de Core Web Vitals solo
    consta que desaparecen las dos conexiones externas y el CSS bloqueante.
    Comprobado en Chromium contra el build: 0 peticiones a Google Fonts y
    exactamente los 2 woff2 precargados.
  - Queda fuera a propósito `frontend/og/*.html`, que sí sigue pidiendo Google
    Fonts: es el generador local del PNG (`npm run og`), no se sirve a nadie y no
    toca la CSP. Migrarlo obligaría a regenerar los dos PNG en el mismo commit.
  - **El cambio de CSP exige redeploy**; hasta entonces rige la anterior, que era
    compatible por más permisiva.

- [x] Generar los redirects de Netlify desde `countryRoutes.json` para evitar mantener una
  segunda lista manual en `netlify.toml`.

## Plan de arquitectura internacional y posts de sentencias (2026-08-02)

- [x] **Cerrar una única arquitectura SEO para todos los países** (2 de agosto
  de 2026). España es la primera instancia de
  `/<pais>/{fuentes,normativa,convenios,sentencias,doctrina}`. La plantilla,
  constructores de ruta, canonicales, breadcrumbs, prerender, sitemap y gates
  se reutilizan para cada jurisdicción; las ramas sin corpus suficiente no se
  materializan y devuelven 404. Alineados el diseño rector, `CLAUDE.md`,
  arquitectura, estructura del repositorio, páginas de país, normativa y esta
  auditoría/backlog.

- [x] **Confirmado que el sitemap registra 149 URLs y no 38** (2 de agosto de
  2026, por la API de Search Console, sin esperar al informe del lunes). Google
  descargó la versión antigua el 1 de agosto a las 19:38 —antes del deploy de
  normativa—; tras el reenvío del 2 de agosto, `sitemaps list` devuelve
  `submitted: 149`, `errors: 0` y `warnings: 0`, con `lastDownloaded` el mismo 2
  de agosto a las 11:36 UTC. `indexed: 0` es lo esperado en un sitemap recién
  descargado y no mide la indexación real.

- [x] **Materializar el 301 de la raíz.** Ya existía antes de esta ejecución:
  `/` → `/espana` como `301!` generado por `build-netlify-redirects.mjs`, con
  test. La fase B hereda esta base y no debe duplicarla (§5.1 del diseño).

- [x] **Gate A.** Verificado contra §9 del
  diseño: schemas válidos, cobertura completa, sin solapes de periodos, ningún
  `countries` desconocido, diff vacío al regenerar dos veces.

- [x] **Gate C1 técnico.** Build preview con `X-Robots-Tag: noindex`,
  404 real de toda ruta `internal_preview` en producción, allowlist sin fugas.
  Este gate no concede publicación.

- [x] **Actualizar los documentos de §13 del diseño con cada fase**, no al
  final: `COUNTRY_PAGES.md`, `SEO_AUDIT.md`, `NORMATIVA.md`, `ARCHITECTURE.md`
  y este backlog (las tareas absorbidas por el plan se marcan al implementarse).

- [x] **Limpieza menor de excepciones históricas** (2026-08-02). El diseño del
  chat backend se promocionó a
  [`docs/development/CHAT_BACKEND_DESIGN.md`](../development/CHAT_BACKEND_DESIGN.md)
  —seguía referenciado desde `NETLIFY_EDGE.md`, este backlog y
  `frontend/CLAUDE.md`— y el plan de ejecución se desversionó (queda como
  scratch local). `docs/superpowers/` ya no contiene ningún fichero versionado
  y la regla de `CLAUDE.md` se cumple sin excepciones.

## Migración del chat a Alfredo (2026-08-04) — pausada y mapeada

- [x] **Cerrar la deuda documental del fallback de modelo.** La política
  vigente deja `gpt-6-luna` + `high` como configuración primaria de A,
  `gemini-4-hydrogen` como fallback cross-provider explícito y `CHAT_MODEL`
  configurable por entorno. La cadena la ejecuta `neutral-llm-gateway`; no
  existe fallback cruzado entre A y B.

## Cierres operativos del 15 de noviembre de 2026

- El PR #72 se cerró sin fusionar el 2026-11-09. El pendiente de decidirlo
  se retira del índice operativo; no se ha sustituido el SDK de Gemini.
- Se documentó la actualización manual del informe semanal y se retiró la
  autoactualización del template de la unit. La pasada natural del 9 de
  noviembre confirmó el envío por Telegram con resultado correcto. Runbook:
  [`WEEKLY_TRAFFIC_REPORT.md`](../operations/WEEKLY_TRAFFIC_REPORT.md).
- Tras la subida de pypdf a 6.21.4 se reextrajeron los 106 PDF: las 1.312
  páginas no cambiaron. Se renovaron procedencia y hashes, conservando el
  contenido y las revisiones. El nuevo gate `make validate-verbatim-corpus`
  revalida el lote sin `output/` desde CI y permite quitar el ignore de
  Dependabot. La migración de procedencia sigue siendo opcional. Contrato:
  [`VERBATIM_CORPUS.md`](../jurisprudence/VERBATIM_CORPUS.md#versión-del-extractor).
