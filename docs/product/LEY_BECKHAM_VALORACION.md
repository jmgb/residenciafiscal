# Ley Beckham: ¿sitio nuevo (leybeckham.es) o sección de residenciafiscal.org?

> **Estado:** valoración, no decisión. Fecha: 3 de agosto de 2026. La decisión
> es del propietario del proyecto; el issue operativo está en
> [`docs/project/TASKS.md`](../project/TASKS.md), sección «Producto y
> arquitectura», y el plan alternativo (repo y dominio propios) en
> [`docs/project/TASKS_LEY_BECKHAM.md`](../project/TASKS_LEY_BECKHAM.md).

## 0. Resumen ejecutivo

**Recomendación: integrarlo en residenciafiscal.org.** No como `/ley_beckham`
(violaría la política de slugs y la plantilla por jurisdicción), sino como
contenido de España dentro de la arquitectura ya cerrada:
`/espana/normativa/<art-93-lirpf>`, sentencias del régimen en
`/espana/sentencias/`, un hub temático y, si se quiere la keyword exacta como
puerta de entrada, una landing `/espana/ley-beckham` (con redirect de cortesía
`/ley-beckham → /espana/ley-beckham`).

Clonar el repositorio con dominio propio es la peor variante de la opción
«sitio separado»: duplica toda la operación (Netlify, Supabase, backups del
VPS, Sentry ×3, UptimeRobot, CI, informe semanal, página de privacidad) y crea
dos codebases que divergen desde el día uno. Si algún día un producto separado
tuviera sentido (ver §6), la forma correcta sería **mismo repo, segundo
deploy**, nunca un clon.

## 1. Qué es la «ley Beckham» y cómo se relaciona con el corpus actual

El nombre coloquial designa el **régimen especial de trabajadores desplazados a
territorio español, art. 93 LIRPF** (impatriados): personas que *adquieren* la
residencia fiscal española pero optan por tributar por IRNR durante 6
ejercicios. Es decir:

- **Misma ley** que el corpus actual (LIRPF; el corpus hoy gira sobre el
  art. 9).
- **Mismo público en gran parte**: quien busca «ley Beckham» está decidiendo o
  gestionando un cambio de residencia fiscal hacia España; quien busca
  «residencia fiscal 183 días» a menudo está en el movimiento inverso o en el
  mismo. Son dos caras de la misma decisión vital/fiscal.
- **Mismas fuentes y mismo pipeline**: sentencias del CENDOJ (SAN/TSJ/TS sobre
  el art. 93 y el modelo 151), normativa del BOE (art. 93 LIRPF, arts. 113–120
  RIRPF), y previsiblemente consultas vinculantes de la DGT (fuente nueva, pero
  el patrón manifest + literalidad + verificación es idéntico).
- **Es contenido exclusivamente español**: no existe «ley Beckham de Francia».
  Encaja de forma natural bajo `/espana`, no exige tocar la arquitectura
  internacional.

Conclusión previa: temáticamente no es un producto distinto; es la **segunda
vertical del corpus español**.

## 2. Opción A — Sitio nuevo: clonar el repo + dominio leybeckham.es

### 2.1 A favor

- **Keyword exacta en el dominio.** «ley beckham» tiene volumen alto y intención
  comercial fuerte (dominada por despachos). Un dominio exacto es memorable y
  transmite foco.
- **Posicionamiento comercial separado.** Un sitio monotemático puede tener un
  tono más orientado a captación (lead-gen para despachos, afiliación) sin
  contaminar el registro sobrio/verificable de residenciafiscal.org.
- **Activo vendible por separado** si algún día se quisiera monetizar o traspasar.
- **Opción English-first.** La audiencia natural («Beckham law Spain») busca
  mucho en inglés; residenciafiscal.org es «solo español, sin hueco para i18n»
  por decisión D3. Un sitio nuevo no arrastra esa decisión.

### 2.2 En contra

- **SEO: se parte dos veces de cero.** residenciafiscal.org tiene hoy autoridad
  ≈0 (primera semana: 81 usuarios GA4, 1 en PostHog). Dividir el esfuerzo crea
  **dos dominios débiles** en lugar de uno que acumule autoridad temática en
  «fiscalidad de la residencia en España». El dominio de concordancia exacta
  dejó de ser una ventaja de ranking hace años; la autoridad temática
  consolidada sí pesa. «Ley Beckham» y «residencia fiscal» comparten intención
  y entidades (LIRPF, AEAT, 183 días, CDI): el contenido de una refuerza a la
  otra *solo si viven en el mismo dominio*.
- **Coste operativo duplicado y permanente.** El repo no es solo un frontend:
  son pipelines de corpus con gates, verificación de citas, backups diarios con
  timers systemd en el VPS, tres proyectos Sentry, monitores UptimeRobot,
  Netlify Function del chat con Supabase, informe semanal GA4/PostHog, política
  de privacidad mantenida afirmación-a-afirmación contra el código. Un clon
  duplica **todo eso** y, peor, lo bifurca: cada fix del pipeline habría que
  portarlo a mano al otro repo. La experiencia universal con clones es que
  divergen en semanas.
- **Contradice la arquitectura recién cerrada.** INTERNATIONAL_ARCHITECTURE.md
  acaba de fijar (2 de agosto) que España es la primera instancia de una
  plantilla por jurisdicción y que todo contenido español vive bajo `/espana`.
  Sacar la segunda vertical española a otro dominio vacía esa decisión.
- **Riesgo del propio dominio.** «Beckham» es el apellido y marca registrada de
  una persona viva con marcas activas. Cientos de despachos usan el término, y
  el riesgo práctico es probablemente bajo, pero un activo cuyo nombre depende
  de la marca de un tercero es frágil (UDRP/oposición, o simple imposibilidad
  de registrar marca propia). El nombre oficial del régimen ni siquiera
  contiene «Beckham».
- **Segunda página de privacidad, segundo responsable de tratamiento efectivo,
  segundo aviso legal LSSI** — todo el trabajo jurídico-operativo de
  `/privacidad` se repite.

## 3. Opción B — Integración en residenciafiscal.org

### 3.1 Encaje concreto en la arquitectura vigente

La plantilla cerrada por jurisdicción es
`/<pais>/{fuentes,normativa,convenios,sentencias,doctrina}`. La ley Beckham
encaja así **sin abrir la plantilla**:

| Pieza | Ruta | Estado del pipeline |
|---|---|---|
| Precepto art. 93 LIRPF | `/espana/normativa/<slug>` | El pipeline BOE ya publica preceptos por artículo; añadirlo es extender la selección en `descargar_normativa.py`/exportación |
| Arts. 113–120 RIRPF | `/espana/normativa/<slug>` | Ídem (el RIRPF ya está entre las 106 normas o se añade) |
| Sentencias sobre el régimen | `/espana/sentencias/<slug>` | Mismo pipeline v3 (CENDOJ → verbatim → caso → proyección pública); sería un **segundo corpus temático español**, con sus propios gates |
| Hub temático | `/espana/doctrina/regimen-impatriados` (o similar) | El patrón de hubs por criterio ya existe; requeriría criterios propios del art. 93 en el catálogo |
| Landing para la keyword | `/espana/ley-beckham` + redirect `/ley-beckham` → 301 | Página editorial nueva; única pieza que no existe como patrón |

Decisiones de diseño que sí habría que tomar (ninguna bloquea):

1. **Dónde vive la landing.** `/espana/ley-beckham` respeta la jerarquía;
   `/ley-beckham` en la raíz es más corta para la keyword pero rompe la
   gramática «todo lo español bajo `/espana`». Un 301 de la corta a la larga
   da ambas cosas.
2. **Ámbito del corpus.** Hoy `is_tax_residence_case` separa 67/39. Un corpus
   art. 93 introduce un segundo `issue_type` de primera clase; hay que decidir
   si comparte catálogo de criterios (`src/config.py`) o añade uno propio
   (`CRIT_DESPLAZAMIENTO_PREVIO`, `CRIT_OPCION_PLAZO`, etc.).
3. **Slug**: siempre `ley-beckham` con guion medio; `/ley_beckham` viola la
   política de slugs del proyecto (ASCII, minúsculas, guion medio).

### 3.2 A favor

- **Toda la infraestructura ya existe y ya está vigilada**: un solo deploy,
  un solo backup, un solo Sentry, una sola página de privacidad que ya cubre
  el chat.
- **Autoridad temática compuesta.** Cada sentencia del art. 93 refuerza el
  cluster completo. El enlazado interno es natural: la landing Beckham enlaza
  al precepto, a las sentencias y al hub de 183 días (la exclusión del régimen
  acaba discutiéndose en términos de residencia).
- **El diferenciador se mantiene**: frente a los despachos que dominan la SERP
  de «ley beckham» con contenido comercial, la propuesta de valor es la misma
  del sitio — corpus verificable, texto literal del BOE, sentencias con
  anclajes. Nadie más tiene eso para el art. 93.
- **El chat mejora gratis**: el mismo runtime conversacional puede responder
  sobre el régimen cuando exista corpus, sin segundo despliegue.

### 3.3 En contra

- La keyword no está en el dominio (irrelevante para ranking; relevante solo
  para branding/memorabilidad).
- El tono del sitio es sobrio/investigador; si el objetivo fuera lead-gen
  agresivo, habría tensión editorial (resoluble con una landing bien
  diferenciada, pero real).
- D3 (solo español) limita la captura del volumen en inglés de «Beckham law».
  Esa limitación existe igual para el resto del sitio y ya se asumió con coste
  diferido; la ley Beckham la hace algo más dolorosa porque su audiencia
  anglófona es proporcionalmente mayor.

## 4. Opción C (si algún día hiciera falta separar) — Mismo repo, segundo deploy

Si en el futuro se validara que conviene un producto separado (p. ej.
English-first para expats con marca propia), la forma correcta **no es clonar**:
es el mismo monorepo con una segunda configuración de sitio en Netlify
(build flags / segundo directorio de datos), compartiendo pipeline, gates y
tests. Coste marginal razonable, cero divergencia de código. Pero es una
optimización prematura hoy: no hay corpus art. 93, no hay tráfico que proteja
una marca, y el sitio principal tiene una semana de métricas.

## 5. Comparativa

| Criterio | A: clon + leybeckham.es | B: sección en residenciafiscal.org |
|---|---|---|
| SEO a 12–24 meses | Dos dominios débiles; sin herencia de señales | Un dominio que acumula autoridad temática |
| Coste de arranque | Alto (infra completa ×2) | Bajo (extender pipelines existentes) |
| Coste de mantenimiento | Muy alto y creciente (divergencia de clones) | Marginal |
| Riesgo legal del nombre | Marca de tercero en el dominio | Ninguno nuevo |
| Privacidad/LSSI | Segunda página legal completa | Ya cubierto |
| Branding para la keyword | Fuerte | Medio (resoluble con landing + redirect) |
| Mercado en inglés | Posible desde el día 1 | Bloqueado por D3 (decisión ya asumida) |
| Vendible por separado | Sí | No (pero es teórico hoy) |
| Coherencia con INTERNATIONAL_ARCHITECTURE.md | La contradice | La instancia |

## 6. Qué cambiaría la recomendación

Reconsiderar un sitio separado (siempre como opción C, nunca clon) solo si se
dieran **a la vez**:

1. El corpus art. 93 ya existe, está aprobado y demuestra tracción medible en
   residenciafiscal.org (la sección funciona antes de independizarla).
2. Se decide competir en inglés («Beckham law») como producto comercial, cosa
   que D3 impide dentro del sitio actual.
3. Hay un modelo de monetización que justifique la operación duplicada.

Mientras tanto, cada euro/hora invertido en leybeckham.es es un euro/hora que
no acumula autoridad en el único dominio que ya está en Search Console.

## 7. Primeros pasos si se aprueba la integración

1. Añadir art. 93 LIRPF (y arts. 113–120 RIRPF si procede) a la selección de
   preceptos del pipeline normativo → ficha en `/espana/normativa/`.
2. Búsqueda CENDOJ de sentencias del régimen (art. 93, modelo 151, exclusiones)
   y valoración del tamaño del corpus candidato antes de comprometer rutas.
3. Diseñar la landing `/espana/ley-beckham` (editorial, enlazando precepto y
   futuro corpus) y decidir el redirect corto.
4. Solo después, decidir si el schema v3 necesita criterios/issue_type propios
   — con el mismo orden de gates 1 → 5 → N que rigió el corpus del art. 9.
