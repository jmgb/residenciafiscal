# Corpus normativo

El proyecto tenía las sentencias pero no la ley. Los análisis del corpus citan
el art. 9 LIRPF, el art. 105 LGT y el art. 4 de una decena de convenios sin que
ninguno de esos textos estuviera en el repositorio: el chat podía mostrar una
sentencia que interpreta el art. 9 pero no el art. 9.

Este documento describe cómo se incorpora la normativa. La arquitectura es
deliberadamente **distinta** de la del pipeline jurisprudencial, por una razón
que conviene tener presente antes de tocar nada.

## Por qué no es el pipeline de sentencias

| | Sentencias | Normativa |
|---|---|---|
| Fuente | PDF del CENDOJ | XML del BOE |
| Estructura | Ninguna: texto corrido | El BOE ya delimita cada precepto |
| Extracción | `pypdf` + marcadores de página | Parseo del XML |
| Análisis | LLM (extrae criterios, pruebas, razonamiento) | **Ninguno** |
| Verificación | Localización difusa + fidelidad literal | Innecesaria: no hay generación |
| Unidad publicada | Una sentencia entera | Un **artículo** |

Una sentencia hay que analizarla e interpretarla; una norma hay que tenerla
íntegra y sin tocar. Por eso aquí no hay llamadas LLM, ni umbrales, ni citas
pendientes de revisión: no hay nada que un modelo pueda equivocarse en generar.

La verificación de citas del pipeline jurisprudencial existe porque un LLM
propone `frases_clave` que pueden no estar en el PDF. Aquí el texto se copia de
un XML estructurado, así que el equivalente es un test que comprueba que cada
párrafo publicado es una cadena idéntica a la del origen.

## Alcance

**Se publica el artículo, no la ley.** La LIRPF tiene 270 bloques y la LGT 446;
convertirlas enteras a Markdown llenaría el corpus de preceptos sobre
retenciones, deducciones autonómicas o procedimiento sancionador que no deciden
ninguna residencia. El criterio de selección es: *precepto que decide o
condiciona la residencia fiscal de una persona física, o la prueba de esa
residencia*.

Del núcleo estatal la lista está escrita a mano en `SELECCION_ESTATAL`
(`export_normativa.py`) porque la elección es jurídica. De los convenios se
publica su artículo de residencia, localizado automáticamente.

## Cómo se localiza el artículo de residencia de un CDI

La rúbrica no sirve. Los 98 convenios titulan ese precepto «Residente»,
«Residentes», «Residencia», «Residencia fiscal» o «Domicilio fiscal» según la
época: el CDI con Suiza de 1966 lo llama «Domicilio fiscal» y es el que aplican
cuatro sentencias del corpus.

Lo que sí es estable en todos los que siguen el Modelo OCDE es la **firma
sustantiva**: el artículo que plantea la doble residencia (`residente de ambos
Estados`) y la resuelve con la `vivienda permanente`. Esa conjunción identifica
un único bloque en 95 de los 98 convenios.

Los tres restantes están fijados a mano en `OVERRIDES_CDI`, cada uno con su
motivo:

| Convenio | Por qué falla la firma |
|---|---|
| Hong Kong (`BOE-A-2012-5039`) | Dice «Parte contratante», no «Estado contratante» |
| Polonia (`BOE-A-1982-14239`) | Redacta «residente de los dos Estados» |
| Bulgaria (`BOE-A-1991-18006`) | No tiene artículo 4: la residencia está en el ámbito subjetivo del art. 1 |

Y tres normas que el filtro por título recoge pero que **no tienen** regla de
residencia están declaradas en `SIN_PRECEPTO_RESIDENCIA`: dos convenios
sectoriales de navegación marítima y aérea (Venezuela y Argentina) y una ley
interna sobre doble imposición intersocietaria. No son un fallo del detector, y
por eso el informe las marca como esperadas.

Si algún día el detector deja de resolver un convenio, `make export-normativa`
sale con código 1 y lo lista como incidencia no esperada. Nunca inventa una
elección.

## Vigencia por ejercicio

Este era el problema que hacía temer un pipeline complicado, y el BOE lo resuelve
de origen: el texto consolidado trae **todas** las redacciones de cada precepto
con su fecha de vigencia.

```xml
<bloque id="a8" tipo="precepto" titulo="Artículo 8">
  <version id_norma="BOE-A-2006-20764" fecha_vigencia="20070101">
  <version id_norma="BOE-A-2015-11724" fecha_vigencia="20160101">
```

Cada precepto publicado renderiza la redacción vigente y, debajo, las
anteriores con la fecha desde la que rigieron. Dos consecuencias útiles:

- **El art. 9 LIRPF nunca se ha modificado** desde el 1-1-2007. Hay un test que
  lo comprueba: si algún día cambia, cambia la lectura de todo el corpus.
- Los ejercicios **2005 y 2006** del corpus son anteriores a la Ley 35/2006 y se
  rigen por el RDLeg 3/2004, derogado. Como una norma derogada sale de la base
  consolidada, se descarga su publicación original del diario del BOE, que es un
  XML plano sin bloques; `parsear_norma_diario()` lo segmenta por los
  `<p class="articulo">`.

## Invariante

El mismo que rige para las sentencias, y por el mismo motivo: **el articulado no
se reescribe, corrige, completa ni parafrasea**. La única transformación admitida
es de formato —colapsar espacios en blanco, incluido el espacio duro que el BOE
usa en las rúbricas, y separar los párrafos—.

**No normalizar a NFKC.** Es la trampa evidente al leer XML del BOE y rompe el
invariante sin que se note: convierte los ordinales `1.º` y `2.ª` en `1.o` y
`2.a`, y el art. 72 LIRPF y el art. 106 LGT los usan al citar otros preceptos.
`\s` en Python ya cubre el espacio duro y el espacio EM, así que la
normalización de espacios no necesita NFKC para nada. Cuidado también con los
tests: comparar origen y salida aplicando la *misma* función de normalización
oculta exactamente esta clase de fallo, por eso
`test_los_ordinales_del_boe_sobreviven_al_corpus_publicado` cuenta caracteres.

Las notas al pie del BOE («Redactado conforme a…», «Se modifica por…») son
anotación editorial, no articulado, y se publican en su propia sección.

Tres tests sostienen el invariante, y los tres están verificados por mutación
—se rompió a propósito el corpus para comprobar que fallan—:

| Test | Qué afirma |
|---|---|
| `test_cada_precepto_publicado_es_subcadena_literal_del_xml_de_origen` | Cada párrafo publicado es idéntico a uno **de ese bloque** |
| `test_las_notas_editoriales_del_boe_no_se_publican_como_articulado` | Ninguna nota del BOE se presenta como texto de la norma |
| `test_el_corpus_generado_esta_al_dia` | Los 111 ficheros coinciden byte a byte con lo que produce el renderizador |

Las dos precisiones importan más de lo que parece. Contrastar contra **el
bloque** y no contra el XML entero: si se compara con todos los párrafos del
fichero, cualquier texto del BOE pasa la prueba aunque pertenezca a otro
artículo. Y comparar **todos** los ficheros y no una muestra: validar solo
`lirpf-a9.md` dejaba sin gate el renderizado de los 95 convenios.

## Normas derogadas

Una sentencia aplica el derecho del ejercicio que enjuicia, no el de hoy, así que
el corpus incluye cuatro preceptos de normas ya sustituidas:

| Norma | Rige | Por qué está |
|---|---|---|
| RDLeg 3/2004, TR del IRPF (arts. 8 y 9) | ejercicios ≤ 2006 | Anterior a la Ley 35/2006 |
| CDI España-Argentina de 1992 (art. 4) | ejercicios ≤ 2012 | Denunciado en 2012 |
| CDI España-Reino Unido de 1975 (art. 4) | ejercicios ≤ 2013 | Sustituido en 2014 |

El BOE saca de la base consolidada lo que deroga, así que estas se bajan del
**diario**, que conserva la publicación original. Localizarlas tiene truco: la
API de consolidada no expone búsqueda por texto, y la de sumarios sí, así que se
piden por el día de publicación (`/api/boe/sumario/YYYYMMDD`) y se filtra el
título.

Dos trampas de esa vía:

- **El XML del diario no siempre marca los artículos.** El CDI con Argentina, en
  el BOE de 1994, está entero en `class="parrafo"` sin una sola marca
  `class="articulo"`, y la segmentación devolvía cero bloques. Hay un fallback
  por forma de la rúbrica y, si tampoco delimita nada, un error: una norma vacía
  se publicaría como una omisión silenciosa, que es peor que un fallo.
- **`estatus_derogacion` no sirve para saber si está derogada.** Viene a «N»
  incluso en convenios ya sustituidos. Por eso `derogada` y `nota_derogacion`
  salen del manifiesto —de una declaración explícita y revisable— y no de un
  campo del BOE.

Lo derogado no se rotula como vigente: el articulado va bajo «Texto derogado», el
frontmatter lo declara, el índice les da su propia sección y el fichero abre con
la advertencia. Es la diferencia entre un corpus utilizable y una trampa.

## Estructura

```
normativa/es/                     # fuente, versionada como sentencias/
  AVISO_LEGAL.md                  # origen y condiciones de reutilización del BOE
  readme.txt                      # inventario
  manifest.json                   # hashes, fechas y URL de cada norma
  BOE-A-2006-20764.meta.xml       # metadatos
  BOE-A-2006-20764.texto.xml      # texto consolidado íntegro
  BOE-A-2004-4347.diario.xml      # publicación original (normas derogadas)

knowledge/normativa/es/           # derivado, regenerable
  preceptos/lirpf-a9.md           # un fichero por artículo
  preceptos/cdi-boe-a-1967-3470-a4.md
  preceptos/index.md
  enlaces/jurisprudencia.json     # qué preceptos cita cada sentencia
  enlaces/por_precepto.json       # índice inverso
  reports/extraccion.json         # recuento e incidencias

frontend/public/data/             # lo que consume la web
  normativa.json                  # índice ligero de los 110 preceptos
  preceptos/lirpf-a9.json         # articulado literal, uno por precepto
```

Los ficheros de los convenios se nombran por su identificador del BOE y no por
el país. Deducir el país del título es inseguro —los 96 lo escriben de trece
formas distintas— y un país equivocado en un nombre de fichero es peor que un
identificador neutro. El título oficial va en el frontmatter y en `index.md`.

## Una jurisdicción por directorio

El README invita a aportar la jurisprudencia de otros países y pide, entre los
tres requisitos, «el precepto nacional que decide la residencia». Este pipeline
habla solo con el BOE, así que la decisión se tomó antes de que entre el primer
país:

- **El dato lleva la jurisdicción.** `normativa/<código>/`,
  `knowledge/normativa/<código>/` y `jurisdiccion` en el frontmatter de cada
  precepto. El código es ISO 3166-1 alfa-2 en minúsculas.
- **El código no se abstrae.** `descargar_normativa.py` es el lector de España y
  lo dice en su docstring; `export_normativa.py` mantiene juntas la parte
  genérica —renderizado, invariante, hashes— y la del BOE —`SELECCION_ESTATAL`,
  `OVERRIDES_CDI`, el detector—. Construir una capa de proveedores para una sola
  jurisdicción sería adivinar la forma del segundo país; el seam real aparecerá
  cuando exista.

Lo que hace falta para añadir un país: un lector que deje en
`normativa/<código>/` la fuente y un `manifest.json` con `id`, `grupo`, `titulo`
y `texto_sha256` por norma, y una entrada en `JURISDICCIONES`. Se reutilizan el
renderizado y los tests de literalidad; el frontend solo activa la nueva
proyección bajo `/<pais>/normativa` y `/<pais>/normativa/<precepto>`, mediante
los constructores comunes, sin crear una plantilla específica para ese país.

El código ISO no coincide con las rutas del frontend (`/espana`) a propósito:
aquellas son de presentación y admiten acentos, esta es la clave de máquina del
dato. Desde la fase A de la arquitectura internacional los dos están atados por
el **catálogo compartido** (`src/jurisdiction_catalog.json`,
[`INTERNATIONAL_ARCHITECTURE.md`](../product/INTERNATIONAL_ARCHITECTURE.md) §4.1):
cada jurisdicción declara `code`, `name` y `slug`, el frontend recibe una
proyección generada y `countryRoutes.json` ya no guarda copia del nombre.
Checoslovaquia y la URSS entran con su código **ISO 3166-3** —el estándar para
Estados extintos— porque sus convenios siguen en el corpus.

La arquitectura SEO queda cerrada antes de incorporar el segundo corpus:
`/<pais>/fuentes`, `/<pais>/normativa`, `/<pais>/convenios`,
`/<pais>/sentencias` y `/<pais>/doctrina`. Este pipeline solo activa las ramas
normativas respaldadas por una fuente oficial; no publica por sí mismo las demás
ni crea índices vacíos.

## Enlace con la jurisprudencia

`normativa_citas.py` resuelve las citas en texto libre de los análisis
—«art.9 LIRPF», «artículo 105.1 LGT», «art. 4.2 CDI»— al precepto publicado, sin
LLM. El resultado va a `enlaces/`, nunca dentro de los dos corpus: meterlo en el
texto legal lo contaminaría y meterlo en los perfiles de sentencia obligaría a
regenerarlos por un motivo ajeno.

Tres reglas, todas para no inventar derecho:

1. **Solo se enlaza a preceptos publicados.** El art. 13 TRLIRNR se cita y no
   está en la selección: queda como cita no resuelta, con el motivo concreto.
2. **La certeza se declara.** «art.9 LIRPF» trae la norma; «art. 9.1.a» no, y se
   resuelve por la norma de residencia del ejercicio marcándose como `inferida`.
3. **La redacción es la del ejercicio enjuiciado**, no la de hoy. Es el pago de
   haber conservado todas las versiones.

El país del convenio decide a qué texto se enlaza, y con Reino Unido, Argentina,
Japón, Rumanía y China también el ejercicio, porque tienen convenio antiguo y
moderno. `CONVENIOS_POR_PAIS` era una tabla curada de diecisiete alias escrita a
mano; hoy es una **proyección** de `src/treaty_relations_es.json`, que cubre las
92 contrapartes con sus periodos y valida que no haya solapes ni huecos. La
contraparte sigue siendo un dato curado y no se deduce del título: un país
equivocado ahí enlazaría una sentencia con el derecho de otro Estado.

Tres normas que el filtro por «doble imposición» arrastraba al grupo `cdi` no
son convenios generales de renta —la Ley 10/1996 es derecho interno y los
convenios con Venezuela de 1986 y Argentina de 1978 son de navegación marítima y
aérea—, así que se reclasifican en `descargar_normativa.py` (`RECLASIFICACION`)
y quedan fuera del registro bilateral. Ninguna publicaba precepto, de modo que
los 110 no cambian.

**Un caso puede cruzar un cambio de norma, y entonces se enlazan las dos.** Los
ejercicios enjuiciados no siempre caen todos del mismo lado: `SAN 5630/2023`
abarca 2005-2008, a caballo de la entrada en vigor de la Ley 35/2006. Elegir una
sola norma por el ejercicio más alto —lo que hacía el resolvedor— dejaba 2005 y
2006 sin el precepto que de verdad los regía. Ahora `normas_residencia_aplicables()`
devuelve una norma por periodo, `_vigentes()` hace lo mismo con los convenios
—Reino Unido cambia entre 2013 y 2014— y cada enlace declara solo las
`redaccion_aplicable` de los ejercicios que su norma rige: el texto refundido de
2004 ya no aparece con una redacción para un año en que estaba derogado.

**Los identificadores de bloque del BOE no son uniformes.** El artículo 4 es `a4`
en el convenio con Francia y `ar-4` en el del Reino Unido de 2013; también hay
`ai-4` y `a1-5`. Construir el identificador desde el número de artículo perdía
enlaces en silencio, así que el emparejamiento va por número leído de la
designación.

**Y la designación tampoco es uniforme: hay artículos en numeración romana.** Los
convenios con Suecia, Rumanía y Canadá titulan su artículo de residencia
«Artículo IV», mientras las sentencias lo citan en árabe («art. 4 CDI»), así que
esos tres preceptos eran inalcanzables: existían publicados y ningún número los
encontraba. `numero_de_designacion()` normaliza el romano a árabe exigiendo que
sea canónico —`IIII` o `VX` se rechazan en vez de convertirse en un número
inventado que apuntaría a otro artículo— y descarta los ordinales escritos con
letra, que empiezan por símbolos romanos válidos («Artículo **D**uodécimo»).

Resultado sobre las 106 sentencias: **122 enlaces** (100 explícitos, 22
inferidos) en 58 sentencias y 10 preceptos citados. De las 48 restantes, 41 no
citan ningún artículo en su análisis y 7 solo mencionan preceptos fuera de la
selección. Es un techo del dato de entrada, no del resolvedor.

El enlace número 122 y el décimo precepto son precisamente el `trlirpf-2004-a9`
de `SAN 5630/2023`. El arreglo de la numeración romana, en cambio, no cambia hoy
ningún enlace: la única sentencia con convenio de Canadá no cita ningún artículo
del convenio en su análisis. Cierra un hueco latente, y hay test que lo cubre.

El resolvedor además avisa de **tres anacronismos**: sentencias cuyo último
ejercicio es anterior a 2007 y que citan la Ley 35/2006, cuando regía el texto
refundido de 2004. Se reportan, no se corrigen: el dato es del análisis.

## Comandos

```bash
make descargar-normativa   # vuelve a bajar las 106 normas del BOE (~3 min)
make export-normativa      # genera los 110 preceptos (sin red, sin LLM)
make enlazar-normativa     # resuelve las citas de las sentencias a los preceptos
```

`descargar-normativa` solo hace falta cuando el BOE actualiza una norma o se
firma un convenio nuevo: el XML está versionado, así que el export funciona sin
red. Los convenios vigentes no se listan a mano, se localizan filtrando por
título el índice de legislación consolidada, que es la lista viva del BOE; los
sustituidos sí van declarados, porque ya no aparecen en ese índice.

Para incorporar una norma suelta sin repetir las 106 descargas —y sin ensuciar
el diff con los hashes de todas las demás— el descargador acepta identificadores
y fusiona el manifiesto existente:

```bash
uv run python src/descargar_normativa.py --solo BOE-A-2024-15573
```

### Dos convenios en vigor que el índice no devuelve

El filtro por título tiene dos falsos negativos comprobados, declarados en
`CDI_NO_CONSOLIDADO` con su motivo:

| Convenio | Por qué no aparece |
|---|---|
| España-Venezuela (`BOE-A-2004-11070`) | Su título dice «doble **tributación**», no «doble imposición» |
| España-Paraguay (`BOE-A-2024-15573`) | Publicado en 2024 y todavía fuera de la base consolidada |

Ampliar el filtro no es la solución: «tributación» arrastraría normas que no son
convenios, y una base consolidada incompleta no se arregla desde aquí. Se bajan
del diario, igual que las derogadas, **pero no lo están**. Por eso el manifiesto
declara ahora la `fuente` (`consolidada` o `diario`) al margen del grupo: el
origen del fichero y la vigencia de la norma son cosas distintas, y confundirlas
publicaría derecho aplicable bajo el rótulo «Texto derogado». El precepto lleva
en su lugar un aviso de que el texto procede de la publicación original.

Sin estos dos, las páginas de `/venezuela` y `/paraguay` no podrían enlazar su
convenio; ver [`docs/product/COUNTRY_PAGES.md`](../product/COUNTRY_PAGES.md).

El frontend regenera sus datos en el `prebuild`
(`frontend/scripts/build-normativa.mjs`), leyendo `knowledge/normativa/es/`.

## Lo que falta

- **El chat no usa todavía el enlace.** El dato y el loader están listos
  (`frontend/src/lib/normativa.ts`), pero `chat-engine.ts` está en pleno
  rediseño en otra línea de trabajo y no se ha tocado. Quien escriba el motor
  puede citar el artículo junto a la sentencia y con la redacción del ejercicio.
- **El techo del enlazado es el análisis, no el resolvedor.** 41 sentencias no
  citan ningún artículo en su registro estructurado. Si el schema v3 recogiera
  las normas citadas como campo propio en vez de dejarlas dentro de la prosa, la
  cobertura subiría sin tocar nada de aquí.
- **`sentencias/` sigue siendo plano y solo español**, mientras `normativa/` ya
  está separado por jurisdicción. La asimetría es deliberada —ese directorio lo
  está tocando otra línea de trabajo— pero hay que resolverla antes de que entre
  el primer país.
- **Los 95 convenios publican solo su artículo de residencia.** Las citas al
  art. 19 (pensiones), 13 (ganancias) o 20 aparecen en el corpus y quedan sin
  resolver. Ampliar la selección es una decisión jurídica, no técnica.
