# Arquitectura internacional de URLs y posts por sentencia

> **Estado:** diseño revisado. **Fases A y C1 ejecutadas** el 2 de agosto de
> 2026; B, C2, D y E siguen pendientes. Fecha del diseño: 2 de agosto de 2026.
>
> Lo que ya existe en el repositorio: el catálogo de jurisdicciones y su schema,
> el registro bilateral de las 92 contrapartes con periodos, el normalizador de
> `judgment.countries`, el sidecar de roles de las 106 sentencias, las
> proyecciones del frontend, la proyección pública con allowlist y manifiesto, y
> el renderer del índice y las fichas en preview privado. **No se ha publicado
> ninguna URL nueva**: los 67 candidatos siguen en `internal_preview` y en
> producción devuelven 404. Detalle al final, en «Estado de ejecución».
>
> Las cifras del apartado 2 salen del repositorio y son reproducibles. Lo que
> **no** está verificado se marca explícitamente como «sin verificar». La
> revisión cerró las decisiones técnicas de la sección 10; la autorización
> jurídica/editorial para publicar análisis sigue siendo un gate externo, no
> una decisión de arquitectura.

### Resultado de la revisión

El diseño se conserva, pero con cinco correcciones que cambian su ejecución:

1. Internacionalización normativa y publicación jurisprudencial son dos líneas
   de trabajo independientes. Comparten catálogos y enlazado, pero ninguna
   bloquea a la otra.
2. Jurisdicciones y relaciones bilaterales son datos de dominio compartidos;
   no pueden tener su fuente de verdad dentro de `frontend/`.
3. No se duplicará el texto del convenio entre una página de país, una página
   bilateral y una ficha normativa. El articulado completo seguirá teniendo una
   única URL.
4. `AGENT_REVIEWED` no autoriza publicación. Se puede construir y probar el
   renderer con los 67 candidatos, pero el sitemap público solo admite casos
   cuyos elementos publicados estén `HUMAN_APPROVED`.
5. Mover ahora `sentencias/` y `knowledge/jurisprudencia-v3/` sería churn sin un
   segundo corpus jurisprudencial real. Se aplaza a una migración separada,
   justo antes de incorporar ese segundo corpus.

**Segunda pasada (misma fecha), sin reabrir decisiones.** Se añadió lo que el
borrador daba por supuesto pero no fijaba: la raíz `/` es hoy un redirect de
cliente y debe materializarse como 301 de servidor, quedando marcada como
revisable si algún día nace una portada internacional (§5.1); un contrato SEO
de plantilla —metadatos únicos derivados del dato, enlazado estructural en el
HTML prerenderizado, filtros fuera del índice y 404/`noindex` fail-closed
también en HTTP— (§5.5); el JSON-LD que **sí** emiten los posts (§6.3); y la
medición por subárbol apoyada en la vigilancia semanal de Search Console que ya
existe (§12.1).

**Tercera pasada (misma fecha).** No hay revisor humano disponible, así que la
fase C2 queda **aplazada sin fecha y marcada como opcional**: ninguna otra fase
depende de ella y el gate de `HUMAN_APPROVED` no se rebaja — simplemente no se
programa. La vía realista para contenido jurisprudencial indexable mientras
tanto es la ficha documental sin análisis de §6.3.

---

## 1. Qué problema resuelve este plan

Hoy el sitio está construido sobre un supuesto implícito: **España es el centro
y los demás países son su contraparte**. Se ve en tres sitios:

- `/francia` no es todavía una página con corpus francés: publica sobre todo el
  **convenio España–Francia** desde el BOE. Francia aparece como el «otro» de
  España. `/peru`, donde no hay convenio en vigor, es hoy una invitación a
  contribuir, no una red peruana.
- El corpus normativo vive en `normativa/es/` y solo habla con el BOE. Un
  convenio Perú–Japón no existe en el repositorio ni puede existir hoy.
- El corpus jurisprudencial (`sentencias/`, 106 PDF del CENDOJ) está en un
  directorio plano sin jurisdicción, a diferencia de la normativa.

El encargo cambia el marco: **el sitio es internacional, no español con anexos**.
`/peru` debe hablar de la red completa de convenios de Perú con el mundo, no solo
de su convenio con España. Y el activo diferencial —106 sentencias analizadas—
debe salir del chat y publicarse como contenido indexable, un post por sentencia,
organizado por doctrina.

Son dos líneas de producto con un denominador común: **la clave de
jurisdicción**. Por eso comparten este diseño y un catálogo, pero tienen
backlogs, gates y métricas separados. La red normativa puede avanzar sin
publicar una sentencia; el renderer jurisprudencial puede prepararse sin mover
la arquitectura internacional.

---

## 2. Estado medido del repositorio (2 de agosto de 2026)

Todas estas cifras se comprobaron ejecutando código, no leyendo documentación.

### 2.1 Frontend y rutas

| Dato | Valor | Fuente |
|---|---|---|
| Rutas de país | **34** | `frontend/src/data/countryRoutes.json` |
| …con `treatyBoeId` (publican convenio) | **27** | idem |
| …sin convenio en vigor | **6** | Mónaco, Guatemala, Haití, Honduras, Nicaragua, Perú |
| …España (no tiene convenio consigo misma) | 1 | `/espana` |
| Rutas de país indexables | **34 / 34** | `indexable: true` en todas |
| Fichas de precepto `/espana/normativa/<slug>` | **110** | `frontend/public/data/normativa.json` |
| …de las cuales son artículo de residencia de un CDI | **97** | 95 `cdi` + 2 `cdi_derogado` |
| URLs en el sitemap | **149** | `frontend/public/sitemap.xml` |

Las rutas se registran en `frontend/src/App.tsx`; hoy el árbol es plano salvo
`/espana/fuentes`, `/espana/normativa` y `/espana/normativa/:slug`.

El pipeline de publicación ya es data-driven y no habrá que reinventarlo:

- `frontend/scripts/prerender.mjs` escribe un HTML real por ruta, leyendo
  `countryRoutes.json` + `staticRoutes.json` + `public/data/normativa.json`.
- `frontend/scripts/build-sitemap.mjs` genera el sitemap solo con lo indexable.
- `frontend/scripts/build-netlify-redirects.mjs` genera `public/_redirects`.

**Consecuencia operativa:** añadir un subárbol nuevo de URLs es, en lo mecánico,
añadir una fuente de datos y tres `map()`. El coste real de este plan no está en
el frontend.

### 2.2 Corpus normativo

| Dato | Valor |
|---|---|
| Jurisdicciones con corpus normativo | **1** (`normativa/es/`, fuente BOE) |
| Normas en `normativa/es/manifest.json` | 106 |
| …con `grupo: cdi` o `cdi_derogado` | **100** |
| Preceptos publicados en `knowledge/normativa/es/preceptos/` | 110 |

Tres normas del grupo `cdi` **no** tienen ficha de artículo de residencia y hay
que mirarlas antes de construir nada encima:

- `BOE-A-1996-28330` — Ley 10/1996 de doble imposición **interna**. No es un
  convenio internacional: está mal clasificada como `cdi`.
- `BOE-A-1989-2339` — Venezuela, 1989.
- `BOE-A-1983-5313` — Argentina, 1983.

**Hallazgo bloqueante para `/espana/convenios/<pais>`.** Las 95 fichas de CDI
vivo corresponden a **92 países distintos**: Japón, Rumanía y China tienen
**dos convenios cada uno, ambos con `derogada: false`**.

| País | Convenio antiguo | Convenio moderno |
|---|---|---|
| Japón | `BOE-A-1974-1930` (1974) | `BOE-A-2021-2977` (2021) |
| Rumanía | `BOE-A-1980-21211` (1980) | `BOE-A-2020-15493` (2021) |
| China | `BOE-A-1992-14734` (1992) | `BOE-A-2021-4911` (2021) |

El corpus **sí** sabe marcar esto —Reino Unido 1975 y Argentina 1992 están como
`cdi_derogado`— pero no lo ha hecho con estos tres, probablemente porque el
índice consolidado del BOE no los marca (la derogación la produce el propio
convenio nuevo). Una página bilateral por país tiene que elegir cuál publica y
con qué rango de ejercicios, y hoy el dato no lo dice. `ConvenioPais` en el
backend ya contiene el patrón de rangos para Reino Unido y Argentina —y el
límite final del convenio japonés antiguo—, pero no el catálogo bilateral
completo. Ese patrón debe migrarse al registro compartido, no duplicarse.

`docs/normativa/NORMATIVA.md#una-jurisdicción-por-directorio` ya fijó el contrato
para añadir una jurisdicción: un lector que deje la fuente en `normativa/<iso>/`
con su `manifest.json` (`id`, `grupo`, `titulo`, `texto_sha256`) y una entrada en
`JURISDICCIONES`. No debería cambiar el invariante de literalidad ni el
renderizador común; sí harán falta un lector de fuente y proyecciones/rutas de
frontend para la nueva jurisdicción. Ese contrato es el que hace viable este
plan.

### 2.3 Corpus jurisprudencial

| Dato | Valor |
|---|---|
| Casos canónicos v3 | **106** (`knowledge/jurisprudencia-v3/cases/*.case.json`) |
| Perfiles OKF/3 en Markdown | **106** (`knowledge/jurisprudencia-v3/perfiles/*.md`) |
| Casos con `is_tax_residence_case: true` | **67** |
| Casos fuera de ámbito | **39** |
| Rango de fechas | 2015-02-18 → 2025-12-11 |
| Revisión jurídica | **1.620 elementos `AGENT_REVIEWED`, 0 `HUMAN_APPROVED`**; la política agregada es `AGENT_REVIEWED_ONLY` y los perfiles llevan `status: draft` |

Distribución de `issue_type` (cuestiones, no sentencias): `TAX_RESIDENCE` 67,
`OTHER` 39, `TAX_ASSESSMENT` 4, `PENALTY` 2, `UNEXPLAINED_CAPITAL_GAIN` 1.

Distribución de criterios aplicados (`criterion_ids`, catálogo de 7 en
`src/config.py`):

| Criterio | Cuestiones |
|---|---|
| `CRIT_183_DIAS` | 65 |
| `CRIT_AUSENCIAS_ESPORADICAS` | 52 |
| `CRIT_CENTRO_INTERESES_ECONOMICOS` | 28 |
| `CRIT_PRESUNCION_FAMILIA` | 24 |
| `CRIT_CENTRO_INTERESES_VITALES` | 17 |
| `CRIT_CDI_TIEBREAKER` | 16 |
| `CRIT_OTRO` | 8 |

Resultados (`holdings[].outcome`, catálogo de 7 en `VALID_RESULTADO_FINAL`;
por cuestión, no por sentencia — por eso suman 113): `OTROS` 39,
`GANA_CONTRIBUYENTE` 38, `GANA_AEAT` 31, `RETROACCION` 3, `PARCIAL` 2.

**El perfil OKF/3 ya tiene la forma de un post.** `san-1210-2023.md` trae
frontmatter completo (`roj`, `ecli`, `organo`, `sala`, `fecha_resolucion`,
`ejercicios_afectados`, `paises`, `criterios_detectados`,
`resultados_por_cuestion`, `technical_review`, `legal_review`, hashes de origen) y
un cuerpo con secciones estables por cuestión: hechos, pruebas valoradas, normas
y doctrina, carga de la prueba, cronología y CDI, conclusión, anclajes literales.
No hay que inventar un formato: hay que renderizarlo.

**Trampa medida, ya anotada en `TASKS.md:100`:** `judgment.countries` es texto
libre sin normalizar. En el corpus conviven `Mónaco` y `Principado de Mónaco`,
`España-Colombia`, `España - Emiratos Árabes Unidos`. Cualquier cruce
país ↔ sentencia que se construya sobre ese campo sin normalizar producirá
enlaces falsos.

---

## 3. Decisiones ya tomadas

Las tomó el propietario del proyecto el 2 de agosto de 2026. **No están abiertas
a revisión**; lo que sí se puede revisar es cómo se implementan y qué riesgos
arrastran.

### D1 — Esquema de URL: slug legible + subárbol

```
/peru                      jurisdicción Perú (hub)
/peru/convenios            índice futuro de la red de convenios de Perú
/peru/convenios/japon      ejemplo ilustrativo; no verificado ni publicable hoy
/espana/convenios/francia  convenio España–Francia (fuente BOE)
/espana/normativa/<slug>   ficha de articulado literal — sin cambios
```

Se descartaron el prefijo ISO (`/pe/convenios/jp`) y la ruta bilateral única
(`/convenios/espana-peru`). Razón: el prefijo ISO exige 301 sobre 34 URLs que
Search Console lleva midiendo desde el 1 de agosto, y `/es` es ambiguo entre país
e idioma; la ruta bilateral única impide que dos jurisdicciones publiquen su
propio texto oficial del mismo tratado.

Los slugs siguen la política vigente: **ASCII, minúsculas, guion medio**
(`/estados-unidos`, no `/estados_unidos`; `/espana`, no `/España`).

### D2 — Fuente: una página de convenio existe solo si su texto está en el repo

Una URL `/<pais>/convenios/<otro>` se publica **únicamente** cuando el texto
literal de ese tratado está versionado en `normativa/<iso>/`, descargado del
boletín oficial de esa jurisdicción y con su `texto_sha256`. Hasta entonces la
URL no existe: ni vacía, ni con metadatos, ni en `noindex`.

Es una condición necesaria, no suficiente. La página debe añadir contexto
propio de la jurisdicción fuente —aplicabilidad, versiones, implementación o
relaciones aprobadas— y no limitarse a duplicar el mismo articulado bajo otra
ruta.

Esto es coherente con el invariante de literalidad del proyecto y con
`SEO_AUDIT.md:288` («no ampliar a los ~98 convenios» sin contenido único). Y
tiene una consecuencia dura que hay que decir en voz alta: **hoy solo existe
`normativa/es/`, así que en el momento de implantar este plan no nace ni una sola
página de convenio no español.** El valor inmediato es estructural; el contenido
llega con la primera jurisdicción importada.

### D3 — Solo español, sin reservar hueco para i18n

No hay prefijo de idioma, ni `hreflang`, ni `x-default`. El sitio es y será en
español mientras no se decida lo contrario.

> **Concern declarado, decisión del propietario respetada.** Si algún día hay una
> versión en inglés habrá que migrar todas las URLs con 301, incluidas las que
> este plan crea. Se asume el coste diferido a cambio de simplicidad hoy.
> La revisión no reabre esta decisión. Solo separa código, nombre y slug y
> centraliza la construcción de rutas; no añade prefijos configurables, locales
> ni ramas inactivas que nadie consume.

### D4 — Destino de URLs: 67 candidatos, con hubs de doctrina fuera de la URL

```
/espana/sentencias                      índice filtrable
/espana/sentencias/san-1210-2023        un post por sentencia
/espana/doctrina/ausencias-esporadicas  hub temático (52 cuestiones)
/espana/doctrina/183-dias               hub temático (65)
/espana/doctrina/cdi-tiebreaker         hub temático (16)
```

La doctrina **no** entra en la URL de la sentencia. Una sentencia aplica varios
criterios (`san-1210-2023` aplica cuatro); meterla bajo uno sería arbitrario y
obligaría a redirigir cuando el análisis cambie. Los hubs son páginas de
categoría que enlazan a los posts; la relación es N:M y vive en el dato.

El conjunto candidato contiene **67**, las que tienen
`is_tax_residence_case: true`. Las 39 fuera de ámbito no entran en este producto:
su `issue_type` es `OTHER` y su análisis no habla de residencia fiscal.

Esta decisión fija la arquitectura de URLs y el universo que puede revisar una
persona; **no autoriza indexar los 67 borradores**. La publicación es incremental
por sentencia y exige el gate vigente de `JURISPRUDENCE_PHASE_E0.md`: todos los
elementos jurídicos que exponga esa ficha deben estar `HUMAN_APPROVED`. Una
decisión general de producto o un descargo visible no sustituyen la aprobación
por caso.

---

## 4. Modelo de datos

### 4.1 La pieza que falta: un catálogo de jurisdicciones compartido

Hoy `countryRoutes.json` mezcla identidad, estado del corpus y metadatos SEO.
Separar esos conceptos es correcto, pero colocar el catálogo canónico dentro de
`frontend/` invertiría la dependencia: Python, los importadores y los validadores
jurídicos pasarían a depender de una aplicación de presentación.

Propuesta revisada:

- `src/jurisdiction_catalog.json`: valores canónicos compartidos;
- `schemas/residenciafiscal-jurisdictions-v1.schema.json`: contrato versionado;
- `src/jurisdictions.py`: carga y validación para Python;
- una proyección generada para el frontend durante `build`, sin segunda edición
  manual.

```jsonc
{
  "schema_version": "residenciafiscal-jurisdictions/1",
  "jurisdictions": [
    { "code": "pe", "name": "Perú", "slug": "peru", "aliases": ["Peru"] },
    { "code": "es", "name": "España", "slug": "espana", "aliases": [] },
    { "code": "jp", "name": "Japón", "slug": "japon", "aliases": ["Japon"] }
  ]
}
```

Reglas:

- `code` es **ISO 3166-1 alfa-2 en minúscula** y es la única clave de cruce.
  Cualquier territorio futuro sin código estándar exige una decisión explícita;
  no se inventa un código silenciosamente.
- `slug` es presentación y puede cambiar mediante una migración de URL. Nunca se
  usa para enlazar artefactos.
- `aliases` solo normaliza grafías. No decide por sí solo si una jurisdicción es
  parte de la controversia, el país de una prueba o una mera mención.
- Se añaden solo jurisdicciones necesarias para rutas o relaciones versionadas.
  No se precargan 200 países ni gentilicios que ningún consumidor usa.
- `countryRoutes.json` conserva únicamente configuración de producto/SEO y
  referencia el catálogo por `code`; `name`, `slug` y alias dejan de duplicarse.

`normativaFichas.json.paises` —97 entradas `boeId → nombre común`, 92 países— es
la semilla curada del catálogo, no otra fuente permanente. La migración debe
producir un informe de correspondencias y fallar si un `boeId` queda sin código.
Tras verificarlo, ese bloque se elimina o se genera desde el nuevo contrato.

### 4.2 Convenios: una relación bilateral curada y una vista derivada

Hoy la relación se expresa como `treatyBoeId` dentro de la página de país. Eso
solo funciona mientras España sea la contraparte implícita. La revisión corrige
además una contradicción del borrador: la contraparte y la aplicabilidad no se
pueden «derivar» con seguridad del corpus si a la vez se prohíbe inferir el país
del título.

Propuesta: un registro curado y validado, por ejemplo
`src/treaty_relations_es.json`, con forma
`(jurisdicción fuente, contraparte, periodo) → norma`. Los índices para Python y
frontend sí se derivan de este registro:

```jsonc
{
  "source_jurisdiction": "es",
  "relations": [
    {
      "counterpart": "jp",
      "instruments": [
        { "id": "BOE-A-1974-1930", "effective_to_tax_year": 2020,
          "status": "superseded" },
        { "id": "BOE-A-2021-2977", "effective_from_tax_year": 2021,
          "status": "current" }
      ]
    }
  ]
}
```

- La **jurisdicción fuente** es la que aporta el texto oficial. Cuando exista
  `normativa/pe/`, tendrá su propio registro. Dos fuentes oficiales del mismo
  tratado no garantizan por sí solas dos páginas útiles: el segundo lado solo se
  indexa si añade contexto jurisdiccional sustantivo, no por cambiar el dominio
  de procedencia del mismo texto.
- El mapeo `boeId → país` **debe ser curado, no deducido con una regex**. Es una
  advertencia ya escrita en `TASKS.md:449`: los 98 convenios escriben el país de
  trece formas distintas y un país equivocado publicaría el derecho de otro
  Estado bajo el nombre correcto. `normativaFichas.json.paises` ya hizo ese
  trabajo para 97; hay que verificarlo, no rehacerlo.
- La aplicabilidad temporal vive en esta relación y se valida para que no haya
  solapes ni huecos no declarados. `CONVENIOS_POR_PAIS` y `treatyBoeId` pasan a
  ser consumidores o proyecciones; no conservan copias editables.
- `grupo: cdi_derogado` describe hoy también cómo se obtiene la fuente desde el
  BOE. No se debe cambiar ese grupo solo para resolver SEO. Japón, Rumanía y
  China requieren metadatos explícitos `current`/`superseded`, rango y
  `replaced_by`; después se decide si el modelo normativo debe separar estado
  jurídico de formato de descarga.
- Una única URL bilateral estable publica el instrumento actual y los
  históricos aplicables por ejercicio. No se crea una URL por versión.

### 4.3 Sentencias: tipar el papel de cada jurisdicción antes de cruzar nada

`judgment.countries` es texto libre (§2.3). Antes de que una página de país pueda
decir «estas N sentencias mencionan tu jurisdicción» hace falta:

1. Normalización determinista `texto libre → ISO alfa-2`, con alias curados
   (`Principado de Mónaco` → `mc`, `España-Colombia` → `["es", "co"]`).
2. Un test que falle ante todo valor desconocido.
3. Un sidecar versionado por sentencia que asigne un papel a cada código, como
   `residence_claimed`, `treaty_applied`, `evidence_location` o
   `mentioned_only`. La normalización propone candidatos; no puede decidir ese
   papel jurídico.
4. A medio plazo, esos papeles pasan al schema canónico siguiente. No se edita a
   mano ninguno de los 106 casos generados para introducirlos.

`TASKS.md:59` ya midió el caso que justifica esta separación: 31 sentencias son
la saga de becarios ICEX, donde el país puede ser destino de la beca y no la
jurisdicción cuya residencia se discute. Toda cifra pública «sentencias sobre
X» usa solo roles permitidos y datos aprobados por una persona.

Este punto es prerequisito de las secciones 5 y 6 y es donde está el trabajo
jurídico real del plan.

---

## 5. Arquitectura de URLs objetivo

### 5.1 Árbol completo

```
/                              → 301 a /espana
/espana                        chat + contenido de España (sin cambios)
/espana/fuentes                (sin cambios)
/espana/normativa              índice de 110 fichas de precepto (sin cambios)
/espana/normativa/<slug>       ficha de articulado literal (sin cambios)
/espana/convenios              índice de la red española de convenios      ← NUEVO
/espana/convenios/<pais>       relación bilateral España–<país>            ← NUEVO
/espana/sentencias             índice de las sentencias aprobadas          ← NUEVO
/espana/sentencias/<slug>      un post por sentencia                       ← NUEVO
/espana/doctrina/<tema>        hub temático                                ← NUEVO
/<pais>                        hub de jurisdicción (34 rutas actuales)
/<pais>/convenios              índice de su red        ← NUEVO, solo con normativa/<iso>/
/<pais>/convenios/<otro>       bilateral desde su óptica ← NUEVO, solo con normativa/<iso>/
/manifiesto /metodologia /colaborar /privacidad   (sin cambios)
/consulta /c/:id               (sin cambios, noindex)
```

**Nota sobre la raíz.** El objetivo ya estaba materializado antes de esta
implementación: `_redirects` contiene `/ /espana 301!`, generado y cubierto por
test. La fase B hereda esa señal de consolidación y no necesita recrearla. Se
mantiene una reserva: si el producto llega a ser realmente internacional, la
raíz es el hueco natural de una portada global de jurisdicciones. El 301 se
trata como decisión revisable al abrir la fase D, no como permanente.

### 5.2 Migración sin dos URLs indexables para el mismo contenido

`/francia` ilustra el problema: las 27 rutas con `treatyBoeId` publican contenido
español que el árbol objetivo colocaría en `/espana/convenios/<pais>`. `/peru`
solo ilustra el destino futuro del árbol, no una duplicación actual.

**Hoy** `/francia` sirve el texto del convenio España–Francia desde el BOE. Bajo
el marco nuevo eso es contenido **de España** viviendo en la página **de
Francia**. La URL de la relación pasa a ser `/espana/convenios/francia`, mientras
el articulado íntegro permanece en su ficha normativa.

Si se crea `/espana/convenios/francia` y `/francia` conserva el mismo texto, son dos
URLs con el mismo contenido: canibalización, exactamente lo que el proyecto ha
evitado hasta ahora. Si se mueve el contenido, **27 páginas indexadas se quedan
casi vacías** justo cuando Search Console empieza a medirlas.

La revisión descarta publicar primero el duplicado y «diferenciarlo después».
La secuencia es:

1. Crear el catálogo, la relación temporal y `/espana/convenios` sin nuevas
   bilaterales indexables.
2. Pilotar tres bilaterales que aporten una diferencia comprobable: convenio
   histórico y actual, ejercicios, y —solo cuando estén aprobadas— sentencias
   que realmente lo aplican.
3. En el mismo cambio, retirar de las tres páginas `/<pais>` el articulado
   completo. Esas rutas pasan a ser hubs de jurisdicción/colaboración y enlazan
   la relación con España. Si todavía no tienen contenido propio suficiente, se
   mantienen accesibles pero `noindex` hasta que lo tengan.
4. Cada URL usa canonical a sí misma. Nunca se usa canonical cruzado para
   declarar equivalentes páginas que pretenden responder a intenciones
   diferentes.
5. Ampliar el patrón solo si el piloto no produce canonicales elegidas por
   Google distintas de las declaradas, duplicados o páginas rastreadas sin
   indexar por falta de valor.

No hacen falta 301 porque `/<pais>` conserva su identidad y cambia de contenido;
pero «cero 301» no es un objetivo absoluto. Si en el futuro una URL deja de
tener una intención propia, una redirección es preferible a mantener una página
artificial. Google trata redirect y `rel=canonical` como señales fuertes de
consolidación, y el sitemap solo como señal débil; por eso no se usa el sitemap
para intentar resolver duplicados:
[documentación oficial de canonicalización](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls).

### 5.3 Tres niveles sobre el mismo tratado: cómo no canibalizar

Después de este plan hay tres URLs que hablan del convenio España–EE. UU.:

| URL | Qué publica | Qué **no** publica |
|---|---|---|
| `/espana/normativa/cdi-boe-a-1990-30940-a4` | El artículo 4 completo, literal del BOE | Análisis, sentencias, contexto |
| `/espana/convenios/estados-unidos` | La relación bilateral: qué convenio rige, qué ejercicios, qué sentencias del corpus lo aplican, extracto del art. 4 con enlace a la ficha | El articulado completo |
| `/estados-unidos` | La jurisdicción: su marco, su corpus (hoy inexistente), la invitación a contribuir | El texto del convenio, una vez exista la página bilateral |

La regla que las mantiene separadas: **el texto literal completo del articulado
vive en una sola URL, la ficha de precepto.** La bilateral publica
aplicabilidad, versiones y relaciones verificadas; el hub de país publica el
estado de esa jurisdicción en el producto. Ambas pueden citar un extracto breve
literal y enlazar la ficha. Si la bilateral no tiene nada más que ese extracto,
no se publica. Si esta regla no se sostiene, se fusionan superficies en lugar de
añadir canonicales cruzados.

`/espana/convenios` y `/espana/normativa` también se conservan separados:
responden a «qué relaciones bilaterales tiene España» y «qué preceptos contiene
el corpus». Deben cruzarse y evitar listados duplicados, pero una faceta única
mezclaría dos entidades y dos intenciones distintas.

### 5.4 Escala y la regla dura contra el thin content

Una matriz de jurisdicciones es combinatoria: 200 × 200 son 40.000 URLs. El
proyecto no puede publicarlas y no debe intentarlo.

**Regla:** una URL indexable existe si y solo si tiene contenido propio,
verificable y distinto de las otras superficies. Una fuente oficial o una
sentencia aprobada son prerequisitos posibles, no una licencia para duplicar
plantillas. No hay páginas generadas «por completitud». Esta regla ya está
implícita en el diseño actual (`indexable` es una decisión editorial separada de
`corpusStatus`) y aquí se hace explícita y comprobable por test.

Con el corpus de hoy, el inventario máximo candidato es:

- `/espana/convenios/<pais>`: hasta **92**, pero solo las que superen el contrato
  de contenido diferencial; no se presupone que las 92 lo hagan.
- `/espana/sentencias/<slug>`: **67 candidatas internas**; públicamente, tantas
  como casos hayan superado revisión humana.
- `/espana/doctrina/<tema>`: hasta **6**, solo con masa crítica de casos ya
  publicables y sin gaps de datos abiertos para ese tema.
- `/<pais>/convenios/*`: **0** hasta que exista la segunda jurisdicción.

No se fija por tanto un total `+167`: confundir el inventario candidato con el
sitemap volvería inútiles los gates. Con menos de 500 URLs el problema no es el
presupuesto de rastreo; es la calidad, la duplicación y la autorización de cada
documento. El despliegue gradual sirve para detectar esos fallos, no para
«ahorrar crawl budget». Google sitúa su guía avanzada de crawl budget en órdenes
de magnitud muy superiores y considera «pequeño» un sitio de unas 500 páginas:
[crawl budget](https://developers.google.com/crawling/docs/crawl-budget) y
[sitemaps](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview).

### 5.5 Contrato SEO de plantilla: metadatos, enlazado y errores

Cada tipo de URL nuevo entra con el contrato que ya cumplen las rutas actuales
(`staticRoutes.json` + `prerender.mjs`) y lo amplía con cuatro reglas que el
borrador daba por supuestas:

1. **Metadatos únicos y derivados del dato.** El `title`, la `meta description`
   y el canonical de cada bilateral, post y hub salen de la proyección validada
   (nombre de la contraparte, ROJ, criterio, ejercicios), no de copy manual por
   página. Dos URLs con el mismo título o la misma descripción en el inventario
   hacen fallar el build. El patrón de título lleva la entidad primero
   («Convenio de doble imposición España–Japón…», «SAN 1210/2023: …») y la
   marca al final, como las fichas de normativa. No se generan imágenes OG por
   página en esta fase: se usa la de sitio.
2. **Lo que Google debe seguir vive en el HTML prerenderizado.** Los enlaces de
   §6.2, los índices y los breadcrumbs se emiten en el HTML de `prerender.mjs`;
   ningún enlace estructural ni redirección depende de JavaScript. Toda URL
   indexable nueva queda a ≤3 clics de `/espana` —la página de prioridad 1.0—,
   que enlaza los tres índices nuevos; y las fichas de precepto de CDI enlazan
   de vuelta a su bilateral cuando esta exista, para que la malla no sea
   unidireccional.
3. **Filtros y parámetros no generan URLs indexables.** El índice de sentencias
   filtra en cliente o con query params fuera del canonical; ninguna
   combinación de facetas entra en el sitemap ni en enlaces internos. Con 67
   candidatos no hay paginación; si algún día hace falta, su contrato se decide
   antes de construirla, no después.
4. **Fail-closed también en HTTP.** El fallback del sitio ya devuelve 404 real
   (`SEO_AUDIT.md`, punto 3): un slug de sentencia no publicado, una bilateral
   sin relación curada o un hub sin masa devuelven 404 en producción — nunca el
   shell de la SPA ni una página vacía. El `noindex` de `internal_preview` se
   emite como `<meta name="robots">` en el HTML prerenderizado, que es el patrón
   vigente, y los Deploy Previews añaden además `X-Robots-Tag: noindex` de
   cabecera, para que un preview con los 67 borradores no sea indexable aunque
   su URL se comparta.

---

## 6. Posts por sentencia

### 6.1 Fuente y contrato

La fuente es el **caso canónico v3** (`knowledge/jurisprudencia-v3/cases/*.case.json`),
no el Markdown. Razón: el JSON es el artefacto validado por el pipeline, el
Markdown es una vista derivada (`docs/jurisprudence/JURISPRUDENCE_DERIVATIVES_B4.md`).
Renderizar desde el JSON evita parsear Markdown y garantiza que el post no puede
decir algo que el caso no dice.

El frontend no debe recibir el caso completo. Un exportador Python crea una
**proyección pública con allowlist** y un manifiesto; valida hashes, literalidad,
estado de revisión y campos permitidos. `build-sentencias.mjs` verifica hashes e
identidad, materializa el estado editorial del manifiesto y escribe un índice
ligero y un fichero por sentencia, siguiendo el patrón de normativa. Así,
añadir un campo al caso canónico no lo publica por accidente.

El manifiesto distingue tres estados:

- `internal_preview`: renderizable localmente, siempre `noindex` y excluido del
  sitemap;
- `publishable`: todos los elementos proyectados cumplen el gate humano;
- `published`: además ha pasado el gate editorial/SEO del lote.

El build público falla cerrado si una ruta indexable no está en `published` o
si su hash no coincide. Un flag de frontend no puede ascender un caso.

Slug: derivado del ROJ, ya normalizado en los nombres de fichero
(`SAN 1210/2023` → `san-1210-2023`). Es estable, único y legible.

### 6.2 Estructura del post

Se hereda la del perfil OKF/3, que ya está validada:

1. **Identidad** — órgano, sala, fecha, ROJ, ECLI, ejercicios, países y enlace
   al buscador oficial del CENDOJ. El caso canónico actual no conserva una URL
   estable por documento, por lo que no se fabrica un enlace directo al PDF.
2. **Por cada cuestión jurídica** — pregunta, hechos relevantes, pruebas
   valoradas (con su categoría del catálogo de 12), normas y doctrina, carga de
   la prueba, cronología y CDI, conclusión estructurada y resultado.
3. **Anclajes literales** — solo los extractos aprobados y verificados contra el
   PDF, con página física y etiqueta impresa. Es lo único de la página que
   reproduce texto judicial.
4. **Enlaces** — a los hubs de doctrina aplicables, a las fichas de precepto que
   la sentencia cita y a `/espana/convenios/<pais>` cuando resuelva por CDI.

### 6.3 La aprobación humana es un gate, no un rótulo

Los 106 casos agregan 1.620 elementos `AGENT_REVIEWED`, ninguno
`HUMAN_APPROVED`; los perfiles están en `status: draft` y el build completo en
`AGENT_REVIEWED_ONLY`. `JURISPRUDENCE_PHASE_E0.md` fija dos gates distintos:
build técnico y publicación jurídica. El segundo exige aprobación humana de
todos los elementos jurídicos publicados en cada caso.

Requisitos, todos bloqueantes:

- Cada post declara visiblemente la procedencia automática y el estado real de
  revisión. En páginas públicas ese estado ya no puede ser solo
  `AGENT_REVIEWED`.
- La publicación puede avanzar caso por caso; no hace falta esperar a que los 67
  estén aprobados. Un primer lote pequeño debe incluir variedad de órgano,
  criterio, resultado y riesgo.
- **No** se emite JSON-LD `Article` ni `Review` ni `FAQPage`: no hay autor humano
  ni contrato editorial para ese marcado. Es una decisión del proyecto, no una
  afirmación de que Google prohíba universalmente `Article` sin firma personal;
  su documentación admite autor `Person` u `Organization` y no impone
  propiedades obligatorias:
  [Article structured data](https://developers.google.com/search/docs/appearance/structured-data/article).
  Lo que **sí** emite cada post es `BreadcrumbList`, como el resto del sitio.
  No existe un tipo de schema.org con soporte de Google para resoluciones
  judiciales, y `Legislation` queda reservado a las fichas que publican texto
  legal; el post no lo finge.
- El texto de la sentencia **no se reescribe, corrige ni parafrasea**. Los
  anclajes salen de subcadenas exactas del verbatim; el resto de la página es
  análisis estructurado y se rotula como tal.
- Un test debe impedir que «revisado por expertos» aparezca si el caso no lleva
  aprobación humana verificable; si se publica el estado, debe salir del
  manifiesto y no de copy escrito a mano.

Se puede implementar ya el exportador, el renderer y un Deploy Preview privado
con los 67 candidatos. Lo que no se puede hacer es usar un descargo para saltar
el gate. Si producto quiere una ficha pública antes de revisar el análisis,
deberá diseñar otro tipo documental limitado a metadatos primarios y citas
literales, y someter ese alcance a una decisión jurídica separada; no se llamará
«post analizado» ni reutilizará resultados, criterios o resúmenes del agente.

A fecha de esta revisión **no hay revisor humano disponible**, así que la
publicación con análisis (fase C2) queda aplazada sin fecha y el resto del plan
no depende de ella (§9). La ficha documental del párrafo anterior es la
alternativa realista si se quiere contenido jurisprudencial indexable antes de
contar con revisor.

### 6.4 Hubs de doctrina

Seis hubs, uno por criterio con masa suficiente:

| Ruta | Criterio | Cuestiones |
|---|---|---|
| `/espana/doctrina/183-dias` | `CRIT_183_DIAS` | 65 |
| `/espana/doctrina/ausencias-esporadicas` | `CRIT_AUSENCIAS_ESPORADICAS` | 52 |
| `/espana/doctrina/centro-intereses-economicos` | `CRIT_CENTRO_INTERESES_ECONOMICOS` | 28 |
| `/espana/doctrina/presuncion-familiar` | `CRIT_PRESUNCION_FAMILIA` | 24 |
| `/espana/doctrina/centro-intereses-vitales` | `CRIT_CENTRO_INTERESES_VITALES` | 17 |
| `/espana/doctrina/cdi-tiebreaker` | `CRIT_CDI_TIEBREAKER` | 16 |

`CRIT_OTRO` (8) no genera hub: no es un tema, es un cajón.

Cada hub publica: el precepto literal enlazado, qué sentencias **publicadas y
aprobadas** aplican el criterio y, solo cuando la muestra sea suficiente, cómo se
reparten sus resultados. Los conteos del rollout interno no se proyectan a la
web. Un hub no nace hasta tener contenido editorial propio y una masa mínima
definida antes de mirar sus métricas.

**Aviso sobre las ausencias esporádicas:** hay un gap de datos abierto y
documentado (`docs/experiments/CHAT_DATA_GAP_ABSENCES.md`) — falta cobertura
estructurada sobre esa doctrina, y existe una propuesta validada pero **aislada y
no aplicada** (`DAY-05`, verificable con `make validate-chat-absences-candidate`).
El hub con más tráfico potencial es justo el que peor dato tiene. La decisión
revisada es **esperar**: no se publica hasta cerrar el gap, aplicar y validar la
corrección por el flujo autorizado y contar con casos humanos aprobados. Un
aviso de limitación no convierte datos insuficientes en una síntesis doctrinal
fiable.

---

## 7. Cambios en el repositorio

### 7.1 No mover todavía `sentencias/`

`sentencias/` aparece en cientos de referencias de código, tests y documentos.
Moverlo no aporta nada a las nuevas URLs ni al renderer español y mezclaría una
migración física de alto churn con dos features de producto.

El cambio pasa a ser una migración independiente, con su propio diseño y diff,
que se ejecuta **después de aceptar una fuente jurisprudencial de una segunda
jurisdicción y antes de copiar su primer PDF**. Hasta entonces:

- los nuevos manifiestos y proyecciones declaran `jurisdiction: es`;
- ningún código nuevo asume que la ruta física implica jurisdicción;
- el importador futuro falla si intenta escribir una jurisdicción no española
  en el directorio plano.

### 7.2 No mover todavía `knowledge/jurisprudencia-v3/`

Rige la misma decisión. La ubicación vigente está fijada por manifiestos,
hashes, política de retención y numerosos consumidores; renombrarla no es un
prerequisito de publicación. El segundo corpus deberá definir primero el layout
objetivo y resolver la coexistencia con OKF/2 legado. Esa migración actualizará
de forma atómica rutas, hashes, restauración y reproducibilidad.

### 7.3 Qué **no** se toca

- `llm_gateway` y la política de modelos del chat.
- El pipeline de verificación de citas y los tests de literalidad.
- El runtime del chat en Netlify Functions y su persistencia en Supabase.
- `/privacidad` — salvo que se añada un encargado o cambie la retención.

---

## 8. Invariantes que este plan no puede romper

Lista de comprobación para implementar el diseño. Cada punto tiene su fuente.

1. **Literalidad.** El texto de una sentencia o de una norma no se reescribe,
   corrige, completa ni parafrasea. Una cita solo se publica desde una subcadena
   exacta del texto bruto extraído del PDF/XML. (`CLAUDE.md`, «Verificación de
   citas» y «Corpus normativo».)
2. **No normalizar a NFKC** el texto normativo: convierte `1.º` en `1.o`.
3. **No se publica análisis sin revisión humana.** `AGENT_REVIEWED` es borrador
   interno. Una ficha indexable solo proyecta elementos `HUMAN_APPROVED` y el
   estado procede del artefacto, no del copy.
4. **JSON-LD honesto.** Solo se marca lo que la página tiene. Nada de `FAQPage`,
   `Article` ni `Review`. (`frontend/src/lib/structured-data.ts`.)
5. **Sin `lastmod`** en el sitemap: no hay fecha de modificación fiable y hay un
   test que lo fija.
6. **Repositorio público.** Ninguna ruta absoluta (`/home/ubuntu/...`) en código
   ni documentación, salvo las units de systemd. Ningún workflow de CI con
   secrets configurados.
7. **`indexable` ≠ `corpusStatus`.** Son decisiones separadas y deben seguir
   siéndolo.
8. **El chat no cambia.** Este plan no toca la frontera Python/agente ni añade un
   analizador LLM de PDF ni un endpoint `/analizar`.
9. **Slugs ASCII con guion medio**, nombres visibles con ortografía española.
10. **`make fast-check` y `npm run fast-check`** verdes antes de cada commit;
    `npm run build` cuando cambie el prerender, el sitemap o los redirects.
11. **Una sola URL para el articulado completo.** Hubs y bilaterales enlazan la
    ficha normativa y no vuelven a publicar el texto íntegro.
12. **Publicación fail-closed.** El frontend no puede ascender un caso ni una
    relación mediante flags locales; consume manifiestos validados y con hash.

---

## 9. Fases y gates

### Fase A — Fundación de datos compartida (sin URLs nuevas)

- Catálogo canónico de jurisdicciones + JSON Schema + cargadores Python y
  frontend.
- Registro curado de relaciones España–contraparte con periodos de aplicación.
- Migración de `normativaFichas.json.paises`, `treatyBoeId` y
  `CONVENIOS_POR_PAIS` a proyecciones del registro, sin tres fuentes editables.
- Resolver las tres normas `cdi` sin ficha. `BOE-A-1996-28330` se reclasifica;
  Venezuela y Argentina se documentan como cobertura o incidencia explícita.
- Modelar Japón, Rumanía y China con instrumento actual y sustituido, rangos y
  `replaced_by`, sin usar `grupo` como atajo para SEO.
- Normalizador de grafías y sidecar de roles jurisdiccionales por sentencia.

**Gate A:** schemas válidos; cobertura completa; ninguna relación tiene periodos
solapados o huecos no declarados; ningún valor de `countries` queda desconocido;
ningún rol jurídico se infiere solo por alias; regenerar dos veces da diff vacío.

### Fase B — Red española, primero como piloto

- Crear `/espana/convenios` como índice de relaciones, no de preceptos.
- Construir tres páginas piloto que cubran: convenio único, sucesión de
  convenios y fuente vigente obtenida del diario en vez del consolidado.
- En el mismo lote, convertir sus `/<pais>` en hubs y retirar de ellos el
  articulado completo. Mantenerlos `noindex` si quedan sin contenido propio.
- `BreadcrumbList` en todas. `Legislation` se mantiene en la ficha que publica
  el texto legal; la bilateral no finge contener el articulado completo.

**Gate B:** una sola URL contiene cada articulado íntegro; canonical self; cero
duplicados inesperados en GSC; HTML prerenderizado útil sin JavaScript; todas las
rutas importantes enlazadas; `title` y `description` únicos en todo el
inventario; la raíz `/` redirige con 301 de servidor; sitemap solo con páginas
que cumplen el contrato de contenido diferencial. Después se amplía por lotes,
no automáticamente a 92.

### Fase C1 — Renderer jurisprudencial privado

- Exportador Python con allowlist, manifiesto y hashes.
- `build-sentencias.mjs`, índice, post, filtros y prerender de los 67 candidatos
  en `internal_preview`.
- `robots: noindex`, exclusión del sitemap y prueba de que un build público no
  puede ascender esos casos.
- Enlazado solo contra relaciones y roles tipados; nunca desde
  `judgment.countries` en bruto.

**Gate C1:** literalidad, páginas y hashes pasan; no se filtra ningún campo fuera
de la allowlist; Deploy Preview revisable y con `X-Robots-Tag: noindex`; toda
ruta `internal_preview` devuelve 404 real en producción; accesibilidad y build
frontend verificados. Este gate no concede publicación.

### Fase C2 — Primer lote jurisprudencial público (aplazada; opcional hasta que exista revisor)

> **Estado (2 de agosto de 2026): sin revisor humano disponible.** Esta fase no
> tiene fecha y ninguna otra depende de ella: A, B, C1 y D avanzan igual. El
> aplazamiento **no** rebaja el gate — los 67 candidatos permanecen en
> `internal_preview` indefinidamente hasta que una persona los apruebe; no se
> publica análisis `AGENT_REVIEWED` por falta de revisor. Mientras tanto, la
> palanca SEO del sitio son la normativa y las bilaterales (fase B). Si se
> quiere contenido jurisprudencial público antes de tener revisor, la única vía
> es la ficha documental sin análisis descrita en §6.3 —metadatos primarios y
> citas literales verificadas—, que exige su propia decisión jurídica pero no
> una revisión caso a caso del análisis del agente.

- Una persona revisa casos completos siguiendo el orden de E0 y registra
  `HUMAN_APPROVED` con identidad y fecha.
- El exportador selecciona un lote pequeño y diverso ya aprobado.
- Se publica el índice y solo las fichas del lote. Los hubs esperan masa crítica;
  el de ausencias esporádicas espera además el cierre de su gap de datos.

**Gate C2:** aprobación por caso; decisión jurídica/editorial de exposición;
reutilización y protección de datos revalidadas contra
`sentencias/AVISO_LEGAL.md`; GSC sin manual actions, canonicales inesperadas ni
patrones de duplicación. Las impresiones se observan, pero su ausencia por sí
sola no invalida la arquitectura de una URL factual nueva.

### Fase D — Segunda jurisdicción normativa

- Verificar primero fuente, condiciones de reutilización y alcance real; el
  ejemplo Perú–Japón sigue siendo solo ilustrativo.
- Implementar un lector específico que satisfaga el contrato común, sin una
  abstracción de proveedores prematura.
- Crear relaciones y páginas solo cuando añadan contexto propio de esa
  jurisdicción, no por duplicar el mismo tratado desde otra URL oficial.

**Gate D:** contrato de `NORMATIVA.md`, especialista comprometido, fuente
reutilizable y tests de aislamiento. Una segunda jurisdicción normativa no
obliga a mover todavía el corpus jurisprudencial.

### Fase E — Segunda jurisdicción jurisprudencial

Solo aquí se diseñan y ejecutan, como migración independiente, los movimientos
`sentencias/` → `sentencias/es/` y `knowledge/jurisprudencia-v3/` → layout por
jurisdicción. Deben preservar hashes, manifiestos, restauración, OKF/2 legado y
reproducibilidad antes de admitir el primer PDF nuevo.

---

## 10. Decisiones cerradas por esta revisión

1. **No se acepta solapamiento temporal como estrategia.** Las bilaterales se
   pilotan a la vez que sus páginas de país cambian de rol; nunca quedan dos
   URLs indexables publicando el mismo articulado completo.
2. **Se mantienen tres niveles.** La ficha normativa contiene el texto literal;
   la bilateral, aplicabilidad y relaciones; el país, estado y contenido de la
   jurisdicción. Una bilateral vacía no nace.
3. **Los dos índices no se fusionan.** Convenios y preceptos son entidades e
   intenciones distintas, aunque se enlacen y compartan filtros.
4. **No se publican los 67 `AGENT_REVIEWED`.** Se construyen en preview y se
   publican por caso tras `HUMAN_APPROVED`. Una eventual ficha documental sin
   análisis requiere otro contrato y otra autorización.
5. **No se añade infraestructura i18n.** El catálogo separa `name`, `code` y
   `slug`, y los generadores no concatenan rutas fuera de una función central;
   esa separación cuesta casi cero y evita acoplamiento, sin introducir hoy
   prefijos, locale ni `hreflang`.
6. **Ausencias esporádicas espera.** Primero se cierra el gap de datos y se
   aprueban casos suficientes; el potencial de tráfico no rebaja el gate.
7. **Perú–Japón sigue siendo ilustrativo.** No entra en datos, rutas ni tests
   hasta verificar la fuente peruana y sus condiciones de reutilización.
8. **No hay problema de crawl budget a esta escala.** Se escalona para validar
   calidad, canonicalización y operación, no para racionar rastreo. El sitemap
   contiene todas y solo las páginas realmente publicables de cada lote.
9. **Una URL bilateral, varias versiones.** Japón, Rumanía y China muestran el
   instrumento actual y los sustituidos con rango de ejercicios. La relación
   temporal curada, no la URL ni el estado del consolidado del BOE, decide cuál
   aplica.

---

## 11. Qué NO hacer

- **No** migrar las 34 rutas de país a códigos ISO ni a ningún otro esquema.
  Decisión D1, y Search Console lleva un día midiéndolas.
- **No** publicar una página de convenio sin texto literal versionado en el repo.
  Decisión D2.
- **No** deducir el país de un convenio con una regex sobre su título.
- **No** contar menciones de país en el texto de una sentencia como si fueran la
  jurisdicción en disputa.
- **No** consumir casos canónicos completos desde el frontend: solo la
  proyección pública validada.
- **No** emitir `Article`, `FAQPage` o `Review` en los posts de sentencia.
- **No** indexar elementos `AGENT_REVIEWED` ni presentar el corpus como revisado
  por expertos mediante copy.
- **No** tocar `changefreq`/`priority` esperando efecto SEO.
- **No** generar URLs por completitud combinatoria.
- **No** exponer URLs indexables de filtros, facetas o parámetros: el canonical
  de un índice es su URL base.
- **No** depender de JavaScript para redirecciones ni enlaces estructurales que
  Google deba seguir: viven en el HTML prerenderizado y en `_redirects`.
- **No** mover `sentencias/` ni `knowledge/jurisprudencia-v3/` dentro de estas
  features; esa migración pertenece a la Fase E.
- **No** conectar nada de esto al chat: es contenido estático prerenderizado.

---

## 12. Verificación exigida

Cada fase entrega tests, no solo código. Modelos que ya existen en el repo:

| Qué comprobar | Modelo a imitar |
|---|---|
| Catálogo y relaciones cumplen sus JSON Schema | validadores de `schemas/` y tests del corpus v3 |
| Toda contraparte tiene jurisdicción y artículo resuelto | `test_todos_los_convenios_generales_tienen_su_articulo_de_residencia` |
| Periodos de instrumentos no se solapan ni quedan ambiguos | tests de `ConvenioPais.rige` y `tests/test_normativa_citas.py` |
| Todo valor de `judgment.countries` resuelve a ISO; todo enlace público tiene rol autorizado | tests de cobertura exhaustiva del corpus |
| Una única URL contiene cada articulado íntegro | `frontend/tests/normativa.test.ts` + test de inventario de rutas |
| El manifiesto público rechaza cualquier elemento no `HUMAN_APPROVED` | gates de publicación de `JURISPRUDENCE_PHASE_E0.md` |
| La proyección pública solo contiene campos de la allowlist y hashes válidos | validadores de derivados v3 |
| El HTML servido lleva su JSON-LD | `frontend/tests/entry-server.test.tsx` |
| El copy no se degrada (fórmulas prohibidas) | `frontend/tests/CountryPage.test.tsx` |
| Sitemap solo con indexables y sin `lastmod` | `tests/test_frontend_seo_assets.py` |
| Redirects y fallback 404 correctos | `tests/test_frontend_cache_policy.py` |
| Identidad literal del texto publicado con la fuente | `tests/test_normativa_boe.py` |
| La relación bilateral apunta al convenio del país correcto | evolución de `tests/test_country_tax_treaties.py` |
| Ningún slug colisiona entre subárboles (país, estático, normativa, sentencias, doctrina) | test de inventario global de rutas sobre las fuentes del prerender |
| `title` y `description` únicos y derivados del dato en todo el inventario | tests de `prerender.mjs` |
| Rutas no publicadas devuelven 404 real, no el shell | `tests/test_frontend_cache_policy.py` + `SEO_AUDIT.md` punto 3 |

`ci.yml` no ignora `frontend/**` a propósito: hay tests de pytest que leen
ficheros del frontend. Si se añade un test Python que lea una ruta nueva, hay que
comprobar que no cae en `paths-ignore`.

### 12.1 Medición por subárbol

La vigilancia semanal de Search Console ya existe: el informe de los lunes
(`scripts/weekly_ga4_telegram.py`) consulta la API de GSC. Al abrir cada
subárbol se añade su prefijo (`/espana/convenios/`, `/espana/sentencias/`,
`/espana/doctrina/`) como segmento observado: cobertura —indexadas frente a
«rastreada, actualmente sin indexar»—, canonicales elegidas por Google y
consultas que traen impresiones. Los criterios de ampliación o parada del
piloto (§5.2, paso 5) se evalúan sobre esos segmentos, nunca sobre el agregado
del sitio, que los diluiría. Si el inventario llega a superar con holgura las
~150 URLs actuales, dividir el sitemap por subárbol es una herramienta de
diagnóstico de cobertura en GSC — no una optimización de rastreo, que a esta
escala no existe (§5.4).

---

## 13. Documentos que habrá que actualizar

- `docs/product/COUNTRY_PAGES.md` — deja de describir «la contraparte de España».
- `docs/product/SEO_AUDIT.md` — los puntos 4 y 5 quedan resueltos o replanteados.
- `docs/project/TASKS.md` — las tareas de las líneas 78, 93, 440 y 489 quedan
  absorbidas o reordenadas por este plan.
- `docs/normativa/NORMATIVA.md` — el contrato de jurisdicción pasa de teórico a
  ejercido.
- `docs/ARCHITECTURE.md` — catálogo compartido, proyecciones públicas y gates.
- `docs/jurisprudence/JURISPRUDENCE_PHASE_E0.md` — no cambia el gate; solo se
  enlaza el nuevo manifiesto de publicación cuando exista.
- `docs/REPOSITORY_STRUCTURE.md` — solo en la futura Fase E que mueva rutas, no
  durante las fases A–D.
- `CLAUDE.md` — mantener la frontera y los invariantes; actualizar la
  descripción del sitio solo cuando el producto internacional esté realmente
  publicado.


---

## 14. Estado de ejecución (2 de agosto de 2026)

### Fase A — ejecutada

| Pieza | Dónde |
|---|---|
| Catálogo de 105 jurisdicciones + schema | `src/jurisdiction_catalog.json`, `src/jurisdictions.py` |
| Registro bilateral de 92 contrapartes + schema | `src/treaty_relations_es.json`, `src/treaty_relations.py` |
| Normalizador de `judgment.countries` | `src/jurisdiction_normalization.py` |
| Sidecar de roles de las 106 sentencias | `knowledge/jurisprudencia-v3/jurisdicciones/`, `src/jurisdiction_roles.py` |
| Proyecciones del frontend | `frontend/src/data/jurisdictions.json`, `treatyRelations.json` |
| Gate ejecutable | `tests/test_gate_fase_a.py` |

Cinco decisiones que el diseño dejaba abiertas y ha habido que cerrar:

1. **Checoslovaquia y la URSS entran con código ISO 3166-3** (`cshh`, `suhh`).
   Sus convenios siguen en el corpus y no tienen alfa-2; inventarles uno habría
   fabricado una clave que ningún otro sistema reconoce. No se declara sucesión:
   qué Estado hereda cada convenio es criterio jurídico sin verificar.
2. **Los rangos de Japón, Rumanía y China salen de la cláusula de entrada en
   vigor de cada convenio nuevo**, citada en `source_note`. Los tres coinciden:
   el instrumento moderno surte efecto desde el ejercicio 2022 y el anterior
   rige hasta 2021. La tabla previa daba 2020 para Japón; ninguna sentencia del
   corpus enjuicia ejercicios posteriores a 2019, así que el enlazado no cambia.
3. **Las tres normas `cdi` sin ficha se reclasifican en el descargador**
   (`RECLASIFICACION`), no editando el manifiesto: así una descarga nueva
   produce el mismo grupo. `cdi` pasa de 98 a 95, y aparecen `cdi_sectorial` (2)
   e `interna_no_cdi` (1).
4. **Los roles se derivan de campos tipados del caso**, con `derived_from` por
   cada uno. El resultado es conservador a propósito: 78 apariciones se quedan
   en `mentioned_only`, que no autoriza ningún enlace público.
5. **`countryRoutes.json` pierde `name` y `treatyBoeId`.** El tipo
   `CountryRoute` los sigue exponiendo, compuestos desde las proyecciones, así
   que ningún componente cambió. `normativaFichas.json` pierde sus 97 países.

Efecto medido sobre lo publicado: **ninguno**. Las 34 rutas, las 149 URL del
sitemap, los 110 preceptos y los 122 enlaces de citas son idénticos.

### Fase C1 — ejecutada

| Pieza | Dónde |
|---|---|
| Proyección con allowlist + estado calculado | `src/public_judgment_projection.py` |
| Manifiesto con hashes y lotes | `src/export_public_judgments.py`, `knowledge/jurisprudencia-v3/publico/` |
| Build al frontend | `frontend/scripts/build-sentencias.mjs` |
| Índice y ficha | `frontend/src/pages/Sentencias*.tsx`, `components/sentencias/` |
| Gate ejecutable | `tests/test_gate_fase_c1.py`, `make verify-public-judgments` |

- Los **67 candidatos** están en `internal_preview`; `LOTES_PUBLICADOS` está
  vacío y declarar ahí un caso sin aprobar **rompe el build**.
- Un build de producción no materializa ninguna ficha: sin fichero ni regla en
  `_redirects`, el fallback devuelve 404 real. El sitemap sigue con 149 URL.
- El Deploy Preview las construye con `SENTENCIAS_PREVIEW=1`, cada ficha lleva
  `noindex` en su HTML y el contexto añade `X-Robots-Tag: noindex, nofollow`.
- **897 extractos literales verificados** contra sus 67 PDF, sin un solo fallo
  (`make verify-public-judgments`, unos 50 s; la suite comprueba una muestra
  fija de cinco).
- Los 67 títulos y las 67 descripciones son únicos y derivados del dato.

Hallazgos de la ejecución, todos corregidos:

- **El convenio enlazado era el vigente hoy, no el del ejercicio enjuiciado.**
  `SAN 1226/2021` juzga 2011 con el Reino Unido y la ficha apuntaba al convenio
  de 2013. La proyección resuelve ahora el instrumento por los ejercicios del
  caso —varios si los cruza— y sin ejercicios no declara ninguno. Lo detectó la
  revisión cruzada con Codex; es el error que el registro con periodos existe
  para hacer imposible, y aun así se coló por llamar al resolutor sin ejercicio.
- **Los `steps` del análisis de convenio filtraban notas internas de revisión**
  mientras se proyectaban como diccionario crudo, no contaban para el gate de
  publicación y sus anclajes propios se descartaban. Los tres fallos venían del
  mismo sitio: un `dict[str, Any]` dentro de una allowlist deja de ser allowlist.
- **El estado `published` vivía solo en el manifiesto.** El build copiaba la
  proyección todavía marcada `publishable`, lo que habría reactivado banner de
  borrador y `noindex` en una publicación futura. Ahora materializa el ascenso
  editorial únicamente después de validar hash, identidad y estado previo.
- **La navegación SPA no restauraba una ficha precargada.** Al volver desde
  otra ruta quedaba en «Cargando» porque el efecto detectaba la precarga pero no
  la reponía en estado. La transición está cubierta por test.
- **Solo `treaty_applied` autoriza un enlace bilateral.** Una residencia alegada
  o una mera mención ya no puede presentar como aplicado un convenio que el
  tribunal no usó para resolver.
- **La interfaz omitía detalle estructurado permitido.** Ya muestra categoría
  de prueba, conclusión y respuesta sobre carga, semántica del recuento de
  presencia y pasos del desempate por CDI, sin ampliar la allowlist.
- **El presupuesto de artefactos medía el síntoma.** `knowledge/jurisprudencia-v3`
  pasó de 761 a 935 ficheros —el 93 % del límite de 1.000— con el árbol todavía
  al 36 % de su presupuesto de peso. El recuento total solo decía cuántas
  sentencias hay; el gate pasa ahora a vigilar **derivados por documento** (hoy
  9 de 10 permitidos), que es lo que se multiplica al añadir uno nuevo o un
  segundo corpus. Detalle en `JURISPRUDENCE_ARTIFACT_POLICY.md`.

### Lo que sigue pendiente

Fase B (bilaterales; el 301 de la raíz ya existe), fase C2 (sin revisor humano
disponible), fase D y fase E, tal como quedan descritas en §9. El gate C1 **no
concede publicación**.
