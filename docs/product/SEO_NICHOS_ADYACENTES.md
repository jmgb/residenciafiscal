# Nichos SEO adyacentes a residenciafiscal.org

> **Estado:** investigación, 3 de agosto de 2026. No es una decisión: la
> secuencia operativa vive como issue en
> [`docs/project/TASKS.md`](../project/TASKS.md), sección «SEO y contenido».
> Basado en análisis de SERPs (composición de resultados, no volúmenes de
> keyword tool — no hay acceso a uno; los juicios de demanda son cualitativos).

## 0. Criterio de evaluación

Un nicho vale para este proyecto si cumple a la vez:

1. **El diferenciador aplica**: materia contencioso-intensiva donde existe
   jurisprudencia CENDOJ / doctrina DGT-TEAC verificable con texto literal.
   Frente a los despachos que dominan estas SERPs con guías comerciales sin
   fuentes, nadie ofrece corpus verificable con sentencia, página y extracto.
2. **Encaja en la plantilla** `/espana/{normativa,sentencias,doctrina}` sin
   romper la arquitectura internacional.
3. **Adyacencia temática real** con la residencia fiscal (refuerza la autoridad
   del cluster, enlazado interno natural).
4. Demanda de búsqueda apreciable y competencia batible en el ángulo
   «fuente primaria verificable».

## 1. Tier 1 — Mismas fuentes, mismo pipeline, máxima adyacencia

### 1.1 Art. 7p LIRPF — exención por trabajos en el extranjero ⭐ el mejor candidato

- **Qué es**: exención de hasta 60.100 €/año para residentes españoles que
  trabajan desplazados fuera. Es la **cara inversa exacta del corpus actual**:
  el corpus habla de quien deja (o dice dejar) de ser residente; el 7p, de
  quien sigue siéndolo pero trabaja fuera. Misma audiencia (expatriados,
  asesores), misma ley, mismos CDI.
- **Litigiosidad**: altísima y viva. El TS ha corregido a la AEAT varias veces
  (directivos y administradores, prorrateo, requisito de impuesto análogo);
  TEAC y TSJ producen doctrina continuamente. La AEAT deniega en masa y se
  recurre en masa → la gente busca sentencias, exactamente lo que el corpus
  ofrece.
- **SERP**: despachos (Martínez Cardós, KPMG alerts, blogs de asesorías) +
  la propia AEAT. Ninguno con fuentes verificables ancladas.
- **Encaje**: precepto art. 7p ya está dentro del XML de la LIRPF que el
  pipeline descarga; corpus CENDOJ nuevo con el mismo escalonado 1 → 5 → N;
  hub `/espana/doctrina/exencion-7p` + landing editorial.
- **Veredicto**: candidata a **segunda vertical** del corpus español, incluso
  por delante de la ley Beckham en volumen de litigio y de búsqueda. Ambas
  comparten además audiencia con la actual.

### 1.2 Ley Beckham / art. 93 — ya valorada

Issue creado en `docs/project/TASKS.md` («Producto y arquitectura»). No se
repite aquí. Nota de esta investigación: la SERP de nómadas digitales
desemboca en el art. 93 (el visado de la Ley 28/2022 se combina con el
régimen), así que la landing Beckham captura también parte de ese tráfico.

### 1.3 Doctrina del art. 9 aún no explotada (ya planificada)

Los 6 hubs de `/espana/doctrina/` de INTERNATIONAL_ARCHITECTURE.md §6.4
(183 días, ausencias esporádicas, centro de intereses…) son las páginas pilar
naturales del corpus existente y siguen sin publicar. Antes de abrir materia
nueva, esto es lo más barato: el corpus ya existe; faltan la revisión humana y
el cierre del gap de ausencias esporádicas.

## 2. Tier 2 — Fuentes nuevas, mismo patrón, cluster «salida de España»

### 2.1 Modelo 720 — declaración de bienes en el extranjero

- **Litigiosidad histórica enorme**: STJUE 27-1-2022 tumbó el régimen
  sancionador; el TS lleva desde entonces anulando sanciones. Ola de
  devoluciones y recursos aún viva.
- **Demanda recurrente y estacional**: obligación anual (Q1) → pico de tráfico
  cada enero-marzo, no solo contencioso.
- **Audiencia idéntica**: quien tiene bienes fuera es quien discute su
  residencia. Enlaza con las páginas de país (dónde están los bienes) y con
  las pruebas del corpus (cuentas y patrimonio en el extranjero como indicios).
- **Contras**: el pico contencioso (2022-2024) va pasando; la norma es la DA
  18ª LGT + orden ministerial, encaja en el pipeline normativo sin fricción.
- **Veredicto**: tercera vertical fuerte; su estacionalidad complementa.

### 2.2 Exit tax — art. 95 bis LIRPF

- Creciente con cada ola de salidas (Andorra, Portugal, EAU, EE. UU.). SERP de
  despachos con guías genéricas; poca jurisprudencia aún (régimen de 2015,
  primeros pleitos llegando ahora) pero mucha consulta DGT.
- Encaje perfecto de cluster: es literalmente «qué pasa cuando dejas de ser
  residente fiscal», el paso siguiente a todo el contenido actual. El precepto
  entra en el pipeline BOE trivialmente.
- **Veredicto**: página pilar editorial ya (poco corpus que construir), corpus
  DGT/TEAC después. Poco coste, muy buena adyacencia.

### 2.3 Cuarentena fiscal — art. 8.2 LIRPF (traslado a paraísos)

- Nicho pequeño pero casi sin competencia de calidad (la SERP son PDF
  académicos y AEAT). Audiencia: deportistas, creadores, grandes patrimonios —
  el corpus actual ya contiene casos de deportistas de élite.
- Enlaza con jurisdicciones concretas (EAU, Gibraltar, y el histórico de
  Andorra pre-2011). Precepto trivial de añadir.
- **Veredicto**: no es pilar por volumen, pero es doctrina diferencial barata
  que completa el cluster de salida. Un hub o ficha doctrinal, no una vertical.

## 3. Tier 3 — Demanda alta pero diferenciador más débil

### 3.1 Certificado de residencia fiscal — top-of-funnel con un ángulo único

- Volumen alto, intención procedimental; la AEAT domina la SERP y el how-to
  puro no nos diferencia. **Pero hay un ángulo que solo este proyecto puede
  dar**: el valor probatorio del certificado extranjero en juicio. Las
  sentencias del corpus discuten una y otra vez si un certificado de residencia
  emitido por otro país prueba algo frente al art. 9 y los CDI. Una página
  pilar «certificado de residencia fiscal: qué prueba y qué no, según los
  tribunales» convierte una keyword transaccional en puerta al corpus.
- **Veredicto**: una landing editorial, coste bajo, hacerla cuando existan los
  hubs de doctrina que debe enlazar.

### 3.2 Teletrabajo internacional / trabajar para empresa extranjera

- Volumen alto y creciente; mayormente consultas DGT, poca sentencia. Se solapa
  con Beckham (entrantes) y 7p (salientes): más que vertical propia, es una
  landing puente que reparte hacia ambas.

### 3.3 Pensiones extranjeras y CDI — ampliación de las páginas de país

- Jubilados retornados y extranjeros residentes; demanda estable. Lo
  interesante no es una vertical nueva sino que **reutiliza el pipeline
  existente**: cada CDI tiene artículo de pensiones (art. 18/19 OCDE) igual que
  tiene artículo de residencia (art. 4). Las fichas de convenio podrían crecer
  precepto a precepto (pensiones primero, dividendos después) multiplicando el
  contenido de las 97 fichas sin fuente nueva — solo más preceptos del mismo
  XML del BOE ya descargado.
- **Veredicto**: la vía de crecimiento más barata de todas en normativa; sin
  corpus jurisprudencial propio a corto plazo.

### 3.4 Descartados o aplazados

| Nicho | Motivo |
|---|---|
| IRNR / modelo 210 (alquileres de no residentes) | Materia distinta (obligación real), SERP con gestorías especializadas (IberianTax…), sin ángulo de corpus; a lo sumo una ficha «obligación personal vs real» |
| ISD no residentes (herencias) | Otra ley, controversia ya resuelta (Ley 11/2021), competencia notarial/despachos consolidada |
| Dividendos extranjeros / art. 80 | Audiencia inversor retail (Rankia, brokers); jurisprudencia TSJ emergente interesante pero lejos del cluster; revisar en 2027 |
| Residencia fiscal en Andorra/Portugal/Dubái («irse a») | Los buscan quienes se van; el contenido útil ya es nuestro (art. 9, exit tax, cuarentena, CDI). Se captura desde las páginas de país y el cluster de salida, no con guías de inmigración que no podemos verificar |

## 4. Recomendación de secuencia

1. **Publicar lo ya construido**: hubs de doctrina del art. 9 (necesitan
   revisión humana + gap de ausencias). Es la página pilar con mejor ratio
   esfuerzo/impacto y ya está en el roadmap.
2. **Art. 7p como segunda vertical de corpus** (valorar si antes que Beckham:
   más litigio, mismas fuentes ya integradas, cero riesgo de marca).
3. **Cluster «salida de España»**: landing exit tax + ficha cuarentena fiscal
   (baratas, editoriales) → corpus 720 después.
4. **Ampliar fichas de convenio con el artículo de pensiones** (pipeline
   existente, sin fuente nueva).
5. **Landings puente**: certificado de residencia (ángulo probatorio),
   teletrabajo internacional.

Todo bajo `/espana` y las reglas vigentes: sin thin content, corpus antes de
afirmar doctrina, revisión humana antes de publicar análisis, y «un precepto,
una URL».

## 5. Límites de esta investigación

- Sin datos de volumen de búsqueda (no hay keyword tool conectado); los juicios
  de demanda salen de la composición y densidad comercial de las SERPs.
- Las SERPs se observaron desde EE. UU. (la herramienta de búsqueda es
  US-only); posiciones exactas en Google España pueden variar, la composición
  de competidores no suele hacerlo.
- No se ha verificado el tamaño del corpus CENDOJ disponible para 7p ni 720;
  es el primer paso antes de comprometer cualquier vertical (mismo criterio
  que el issue de la ley Beckham).
