# Auditoría SEO — 1 de agosto de 2026

> **Decisión posterior cerrada (2 de agosto de 2026):** España es la primera
> instancia de una arquitectura común por jurisdicción:
> `/<pais>/{fuentes,normativa,convenios,sentencias,doctrina}`. Las conclusiones
> históricas de esta auditoría sobre las URLs españolas siguen vigentes, pero
> cualquier expansión reutiliza la misma jerarquía, canonicales, breadcrumbs,
> prerender y gates; no se diseña un árbol reducido para otros países. Una rama
> sin corpus publicable no existe y devuelve 404. Contrato:
> [`INTERNATIONAL_ARCHITECTURE.md`](INTERNATIONAL_ARCHITECTURE.md).

> **Estado (1 de agosto de 2026, mismo día):** aplicadas las mejoras 1–4 del
> orden sugerido.
>
> - **GSC operativa**: propiedad `sc-domain:residenciafiscal.org` verificada por
>   DNS (TXT `google-site-verification` en Cloudflare) y sitemap enviado y
>   descargado el mismo día: 38 URLs, 0 errores. La verificó la service account
>   de doctor (única con Site Verification API habilitada) y delegó la
>   propiedad a la cuenta personal y a la service account que usa el skill
>   `google-search-console` de este repo (`GSC_SITE_URL` ya está en `.env`).
> - **Contenido**: sección estática indexable en `/espana`
>   (`SpainLandingContent`, de ~1.100 a ~3.000 caracteres visibles) con título
>   propio («Residencia fiscal en España: jurisprudencia del art. 9 LIRPF»).
> - **Soft 404 eliminado**: shell `noindex`, fallback `/*` → `404.html` con 404
>   y reglas 200 explícitas para `/consulta`, `/c/*` y `/privacidad`; en
>   runtime solo la ruta canónica vuelve a `index`.
>
> - **Fichas por precepto publicadas** (también el 1 de agosto de 2026): 110
>   fichas (`/espana/normativa/<slug>`) más su índice (`/espana/normativa`),
>   prerenderizadas con el texto literal del BOE y título por jurisdicción
>   (catálogo y registro bilateral proyectados al frontend),
>   JSON-LD `Legislation` + `BreadcrumbList`, y enlazadas desde las páginas de
>   país y `/espana/fuentes`. El sitemap pasa de 38 a 149 URLs.
>
> - **Renderer jurisprudencial privado** (2 de agosto de 2026): 67 candidatas
>   con proyección allowlist, hashes, índice y ficha en Deploy Preview. Todas
>   siguen en `internal_preview`, fuera del sitemap y con `noindex`; producción
>   materializa cero porque aún no existe revisión humana.
>
> - **Fuentes autoalojadas** (2 de agosto de 2026): Inter y Space Grotesk salen
>   del mismo origen vía `@fontsource-variable/*`, con `preload` del subconjunto
>   latino inyectado en el `postbuild`. La CSP pierde sus dos excepciones para
>   Google Fonts (punto 8).
>
> - **Enlace GSC ↔ GA4 activo** (2 de agosto de 2026, manual en la UI con la
>   cuenta administradora de GA4, que ya era propietaria delegada en GSC).
> - **Vigilancia y quick wins** (2 de agosto de 2026): el informe semanal de
>   Telegram añade la línea de Search Console —clicks, impresiones, CTR y
>   posición media, sobre dos semanas completas desplazadas por el retraso de
>   la API, con fallo declarado y nunca silencioso—; el layout emite JSON-LD
>   `WebSite` + `Organization` en todas las rutas; y la ofuscación de e-mails
>   de Cloudflare está desactivada (los `mailto:` vuelven a ser legibles para
>   bots). El punto 6 (`lastmod`) se cierra en sentido contrario al propuesto:
>   no hay fecha fiable de modificación de página (la vigencia jurídica no lo
>   es), así que **no se emite** y un test lo fija.
>
> Pendientes: Bing Webmaster Tools (manual, cuenta de Miguel), países sin
> convenio y fichas por sentencia (ambos tras el gate de GSC de 4-6 semanas).

Revisión profunda del SEO de [residenciafiscal.org](https://residenciafiscal.org):
repositorio (`frontend/`), HTML servido en producción, redirecciones, Cloudflare,
GA4 y estado de Search Console. El objetivo del documento es una lista priorizada
de mejoras para conseguir tráfico orgánico; lo que ya está bien se deja constancia
para que nadie lo «arregle».

**Situación de partida.** GA4 registra **cero sesiones orgánicas** en los últimos
30 días (solo `(direct)` y `(not set)`). No es un fallo técnico: el sitio es
nuevo, las 34 rutas indexables se publicaron el 1 de agosto de 2026 y no existe
todavía propiedad en Google Search Console. La base técnica es notablemente
sólida; lo que falta es visibilidad en buscadores (alta y monitorización) y, sobre
todo, contenido indexable en la página principal y a partir del corpus.

## Lo que ya está bien (no tocar)

Verificado en producción el 1 de agosto de 2026:

- **Prerenderizado real por ruta**: cada URL pública sirve HTML con contenido,
  título, descripción, `canonical`, `robots` y OG propios (`scripts/prerender.mjs`),
  con fuente única de metadatos (`countryRoutes.json`, `staticRoutes.json`) que
  comparten bot y SPA.
- **Redirecciones canónicas correctas**: `/` → `/espana` (301), `www` → apex
  (301), `http` → `https` (301), rutas con acento → slug ASCII (301).
- **`robots.txt` completo** (crawlers clásicos + IA, `Disallow: /c/`, sitemap
  declarado) y **`llms.txt`** conforme a llmstxt.org.
- **Sitemap generado desde fuente única** (37 URLs, solo indexables).
- **JSON-LD honesto**: `BreadcrumbList` + `Legislation` emitidos dentro del árbol
  React; no se marca contenido inexistente.
- **Títulos y descripciones únicos por país** orientados a la búsqueda
  («Residencia fiscal Francia–España: convenio y jurisprudencia»).
- **Enlazado interno fuerte**: el HTML prerenderizado de cada país enlaza a las
  34 jurisdicciones y a las páginas institucionales.
- **Rendimiento del servidor**: TTFB ~200 ms, cabeceras de caché correctas,
  HSTS, CSP. La imagen OG (1200×630) responde 200.
- El WAF de Cloudflare deja pasar a Googlebot, bingbot, GPTBot, ClaudeBot y
  PerplexityBot (solo bloquea User-Agents genéricos tipo `curl`, vigilado ya en
  `TASKS.md`).

## Mejoras priorizadas

### P0 — Sin esto no hay tráfico que medir

#### 1. Crear y verificar la propiedad de Google Search Console

No existe propiedad de `residenciafiscal.org`: la service account del proyecto
solo ve `sc-domain:presupuestor.com`, así que el sitemap nunca se ha enviado y no
hay ningún dato de cobertura. Es la tarea ya bloqueada en
[`TASKS.md`](../project/TASKS.md).

- Crear la propiedad **de dominio** (`sc-domain:residenciafiscal.org`) con el
  registro TXT en Cloudflare DNS (2 minutos, mismo panel que ya se usa).
- Añadir la service account del proyecto como *User* en *Settings → Users and
  permissions* para que el skill `google-search-console` pueda leer datos y
  enviar el sitemap.
- Enviar `https://residenciafiscal.org/sitemap.xml` y revisar la primera
  descarga y los errores de cobertura.
- Enlazar GSC ↔ GA4 para tener consultas orgánicas dentro de Analytics.
- Alta también en **Bing Webmaster Tools** (importa la propiedad de GSC en un
  clic): Bing alimenta además a ChatGPT/Copilot, relevante para un sitio que ya
  cuida a los crawlers IA.

Sin esto, el gate de las 4-6 semanas definido en `TASKS.md` («medir antes de
ampliar») no puede evaluarse.

#### 2. Dar contenido indexable a `/espana`, la página de prioridad 1.0

`/espana` es la home real del sitio y la única candidata a rankear por las
consultas principales («residencia fiscal España», «residencia fiscal 183
días»...), pero su HTML prerenderizado tiene **~1.100 caracteres visibles**: el
`h1` de marca, el formulario del chat y las sugerencias. Compárese con las
páginas de país (~5.400) o `/colaborar` (~5.400). Un buscador no tiene casi nada
que indexar en la URL más importante del sitio.

Propuesta: mantener el chat arriba y añadir debajo una sección de contenido
estático real (renderizable en el build, sin efectos), por ejemplo:

- Qué decide el art. 9 LIRPF y los tres criterios que aplican los tribunales
  (permanencia 183 días y ausencias esporádicas, centro de intereses económicos,
  presunción familiar) — el copy puede salir de material ya redactado para
  `/metodologia` y `/espana/fuentes`, enlazando el precepto literal del corpus
  normativo.
- Cifras del corpus con enlace a `/espana/fuentes` (106 resoluciones TS/AN,
  2015–2025, 67 recuperables).
- Preguntas de ejemplo que ya existen como sugerencias, convertidas en texto
  visible.

Límite del proyecto a respetar: el análisis lo genera un modelo y **no se afirma
revisión humana**; el contenido nuevo debe salir de los textos literales
(preceptos, extractos verificados) y del copy institucional existente.

Complemento menor: el título de `/espana` es hoy idéntico al de la shell.
Valorar uno más específico («Residencia fiscal en España: jurisprudencia del
art. 9 LIRPF») y un `h1` que contenga «residencia fiscal» (el actual es el lema
«Decide con las sentencias en la mano»).

### P1 — Corregir señales confusas y explotar el activo real

#### 3. Eliminar los soft 404 del fallback SPA

Cualquier ruta inexistente (`/ruta-inexistente`) devuelve **200** con la shell
vacía, `robots: index, follow` y `canonical` hacia `https://residenciafiscal.org/`
— que a su vez es un 301 a `/espana`. Google lo tratará como soft 404 y ensucia
la cobertura justo cuando se quiere empezar a medirla.

Dos arreglos compatibles, de menos a más:

- **Marcar la shell como `noindex`**. Desde que `/` redirige a `/espana`, la
  shell `dist/index.html` ya no es ninguna página pública: solo la sirven el
  fallback y las rutas de aplicación (`/consulta`, `/c/*`). Puede llevar
  `noindex` sin coste — el prerenderizado ya reescribe la meta `robots` por
  ruta, así que las páginas reales no se ven afectadas. Un solo cambio en
  `frontend/index.html`.
- **Devolver 404 real en el fallback**: en `netlify.toml`, reglas 200 explícitas
  para las rutas de aplicación (`/consulta`, `/c/*`) y cambiar el fallback final
  a `status = 404` sirviendo la misma shell (la SPA puede montar encima su
  página de «no encontrado»). Requiere test de que todas las rutas públicas
  siguen sirviendo su fichero físico prerenderizado.

#### 4. Publicar el corpus como páginas indexables (renderer hecho; gate pendiente)

El activo diferencial del proyecto —106 sentencias verbatim verificadas y 110
preceptos literales del BOE— ya tiene páginas indexables para normativa y un
renderer privado para jurisprudencia. Las 67 candidatas de sentencias **no
tienen ninguna página pública ni indexable** hasta superar el gate humano y el
lote editorial. Es exactamente el tipo de contenido long-tail que un despacho
busca en Google, pero el potencial no rebaja ese gate:

- **Ficha por sentencia** (`/espana/sentencias/<ecli-o-slug>`): órgano, fecha,
  ECLI, resultado del catálogo canónico, criterios aplicados, cuestiones
  jurídicas y extractos literales ya verificados por el pipeline de citas, con
  el rótulo de estado de revisión que ya usa el chat. El inventario máximo son
  67 candidatas dentro de ámbito, más un índice `/espana/sentencias` filtrable;
  el número publicado será el del lote expresamente aprobado.
- **Página por precepto** (`/espana/normativa/<slug>`): ya publicada para 110
  preceptos con texto literal del BOE y test de identidad.

Captura consultas del tipo «STS residencia fiscal 2024», «artículo 9 LIRPF
texto», «sentencia becarios ICEX residencia fiscal», y da a las páginas de país
algo real que enlazar (las sentencias que citan su convenio).

**Coherencia con el gate vigente**: `TASKS.md` fija medir las 34 rutas actuales
4-6 semanas antes de ampliar formato. Este punto no salta ese gate: puede
diseñarse ya (rutas, contrato, qué campos del caso v3 se publican) y ejecutarse
cuando GSC confirme que el formato país indexa. Lo que sí conviene decidir ya es
la URL, para no migrar después.

#### 5. Diferenciar las seis páginas de país sin convenio

Mónaco, Guatemala, Haití, Honduras, Nicaragua y Perú sirven ~3.100 caracteres en
los que casi todo es plantilla compartida (sidebar + invitación a contribuir);
el único contenido propio es «no hay convenio en vigor». Treinta y cuatro
páginas donde seis son casi idénticas entre sí es un patrón que Google puede
leer como doorway/thin content y arrastrar al resto.

Mínimo razonable por página: explicar qué significa la ausencia de convenio
(solo rige el art. 9 LIRPF y la doble imposición se mitiga por el art. 80
LIRPF), y —cuando exista la ficha por sentencia— enlazar las resoluciones del
corpus que mencionan esa jurisdicción (Mónaco es de las más citadas). Si a las
4-6 semanas GSC las muestra excluidas como duplicadas, valorar devolverlas a
`noindex` hasta que tengan contenido propio.

### P2 — Mejoras incrementales

#### 6. `lastmod` en el sitemap

`build-sitemap.mjs` no emite `<lastmod>`. Google ignora `changefreq`/`priority`
pero **sí usa `lastmod`** si es fiable. Emitirlo solo cuando refleje un cambio
real (p. ej. `reviewedAt` de `legalReferences`, o la fecha del último commit que
tocó la fuente de la ruta); nunca la fecha del build, que lo convertiría en
ruido.

#### 7. JSON-LD de sitio: `WebSite` + `Organization`

Hoy solo hay `BreadcrumbList` y `Legislation`. Añadir en el layout un bloque
`WebSite` (nombre, URL) y `Organization`/`Brand` con el logo ayuda al panel de
marca y al nombre del sitio en resultados. En `/espana/fuentes`, el corpus
encaja como `Dataset` (es un dataset real, versionado y con licencia de fuente
documentada) — mismo criterio de honestidad: solo campos que el corpus sabe.

#### 8. Autoalojar las fuentes tipográficas — **hecho** (2 de agosto de 2026)

Inter y Space Grotesk se cargaban desde `fonts.googleapis.com`/`fonts.gstatic.com`:
dos conexiones externas y CSS render-blocking que penalizan LCP en móvil (Core
Web Vitals es factor de ranking).

Ya se sirven desde el mismo origen con `@fontsource-variable/inter` y
`@fontsource-variable/space-grotesk` (`src/main.tsx`), con `font-display: swap`
heredado del paquete:

- **Cero terceros en la ruta crítica.** Fuera los dos `preconnect` y el `<link>`
  a la hoja de estilo del CDN; la CSP queda en `style-src 'self' 'unsafe-inline'`
  y `font-src 'self'`, sin excepciones para Google.
- **Una petición por familia en vez de una por peso.** Los ficheros son
  variables (`wght` 100–900 y 300–700), así que los cuatro pesos de Inter y los
  tres de Space Grotesk salen de 48 KB + 22 KB. Los siete subconjuntos viajan en
  el deploy, pero el `unicode-range` deja sin pedir todo lo que no sea `latin`.
- **`preload` de los dos subconjuntos latinos.** El nombre del woff2 emitido
  lleva hash de contenido, así que no puede escribirse en `index.html`:
  `scripts/inject-font-preload.mjs` lo lee del CSS ya compilado y lo inyecta en
  el `postbuild` **antes** de `prerender.mjs`, de modo que las ~150 copias por
  ruta heredan la etiqueta. Sin él, el navegador descubriría la fuente solo tras
  aplicar el CSS: un viaje extra justo delante del texto que mide el LCP.
- `tests/self-hosted-fonts.test.ts` impide la vuelta al CDN (HTML, CSS y CSP) y
  cubre el inyector, que falla ruidosamente si el bundle deja de emitir una
  fuente.

Fuera de alcance a propósito: `frontend/og/*.html`, que sí siguen pidiendo
Google Fonts. Son el generador local de la imagen OG (`npm run og`, Chrome
headless con red), no se sirven a nadie y no tocan ni la CSP ni el LCP.

Queda por medir: sin datos de campo de Core Web Vitals no se puede afirmar la
mejora real de LCP, solo que desaparecen dos conexiones externas y una hoja de
estilo bloqueante.

#### 9. Ruido de Cloudflare en el HTML

*Email Address Obfuscation* está reescribiendo los `mailto:` del HTML
prerenderizado a `/cdn-cgi/l/email-protection#...` e inyectando un script. Para
un bot sin JavaScript, el correo de contacto de `/colaborar` no existe. Si el
correo ya es público a propósito, desactivar la función en Cloudflare
(*Scrape Shield*) deja el HTML limpio; revisar de paso que *Rocket Loader* esté
apagado (interferiría con el bundle y la CSP).

#### 10. Vigilancia continua (una vez exista GSC)

- Revisar cobertura semanalmente las primeras 6 semanas: qué indexa, qué queda
  en «Descubierta, no indexada» y si las páginas sin convenio caen en
  «Duplicada».
- Añadir las consultas GSC al informe semanal de Telegram
  ([`WEEKLY_TRAFFIC_REPORT.md`](../operations/WEEKLY_TRAFFIC_REPORT.md)) cuando
  la propiedad tenga datos: clicks, impresiones y posición media son la métrica
  del gate, no las visitas GA4 (que hoy mezclan bots).
- Revisar los eventos del WAF para confirmar que ningún crawler legítimo menor
  (Applebot, DuckDuckBot, monitores) recibe 403 (tarea ya abierta en `TASKS.md`).

## Qué NO hacer

- **No** añadir `FAQPage`/`Article`/`Review` schema sin que exista ese contenido
  de verdad: el criterio actual (solo marcar lo que la página tiene) es
  correcto y está documentado en `frontend/src/lib/structured-data.ts`.
- **No** presentar el corpus como revisado por expertos en ningún copy nuevo:
  las anotaciones siguen en `status: proposed` y el registro es profesional
  (límites de la sección «Un país, un corpus» del `CLAUDE.md` raíz).
- **No** ampliar a los ~98 convenios antes de que GSC confirme que el formato
  actual indexa y recibe impresiones; ni publicar fichas por sentencia sin
  `HUMAN_APPROVED` y lote editorial explícito (gates de `TASKS.md`).
- **No** tocar `changefreq`/`priority` esperando efecto: Google los ignora; el
  esfuerzo va en `lastmod` y en contenido.

## Orden de ejecución sugerido

| # | Acción | Esfuerzo | Impacto |
|---|--------|----------|---------|
| 1 | Propiedad GSC + sitemap + Bing + enlace GA4 | Muy bajo (manual, 15 min) | Imprescindible |
| 2 | `noindex` en la shell (mitiga el soft 404) | Muy bajo | Alto |
| 3 | Contenido indexable en `/espana` + title/h1 | Medio | Muy alto |
| 4 | Fallback 404 real en `netlify.toml` | Bajo | Medio |
| 5 | `lastmod`, JSON-LD `WebSite`/`Organization`, e-mail obfuscation (fuentes self-host: hecho) | Bajo | Bajo-medio |
| 6 | Diferenciar países sin convenio | Medio | Medio |
| 7 | Publicar por lotes fichas de sentencia tras revisión humana (renderer ya hecho) | Alto | El mayor a medio plazo |

Con 1–3 hechas, el sitio queda en condiciones de que el gate de las 4-6 semanas
mida algo real; la 7 es la que convierte el corpus en tráfico.
