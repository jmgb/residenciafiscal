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

La rúbrica no sirve. Los 96 convenios titulan ese precepto «Residente»,
«Residentes», «Residencia», «Residencia fiscal» o «Domicilio fiscal» según la
época: el CDI con Suiza de 1966 lo llama «Domicilio fiscal» y es el que aplican
cuatro sentencias del corpus.

Lo que sí es estable en todos los que siguen el Modelo OCDE es la **firma
sustantiva**: el artículo que plantea la doble residencia (`residente de ambos
Estados`) y la resuelve con la `vivienda permanente`. Esa conjunción identifica
un único bloque en 93 de los 96 convenios.

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
| `test_el_corpus_generado_esta_al_dia` | Los 107 ficheros coinciden byte a byte con lo que produce el renderizador |

Las dos precisiones importan más de lo que parece. Contrastar contra **el
bloque** y no contra el XML entero: si se compara con todos los párrafos del
fichero, cualquier texto del BOE pasa la prueba aunque pertenezca a otro
artículo. Y comparar **todos** los ficheros y no una muestra: validar solo
`lirpf-a9.md` dejaba sin gate el renderizado de los 93 convenios.

## Estructura

```
normativa/                        # fuente, versionada como sentencias/
  AVISO_LEGAL.md                  # origen y condiciones de reutilización del BOE
  readme.txt                      # inventario
  manifest.json                   # hashes, fechas y URL de cada norma
  BOE-A-2006-20764.meta.xml       # metadatos
  BOE-A-2006-20764.texto.xml      # texto consolidado íntegro
  BOE-A-2004-4347.diario.xml      # publicación original (normas derogadas)

knowledge/normativa/              # derivado, regenerable
  preceptos/lirpf-a9.md           # un fichero por artículo
  preceptos/cdi-boe-a-1967-3470-a4.md
  preceptos/index.md
  reports/extraccion.json         # recuento e incidencias
```

Los ficheros de los convenios se nombran por su identificador del BOE y no por
el país. Deducir el país del título es inseguro —los 96 lo escriben de trece
formas distintas— y un país equivocado en un nombre de fichero es peor que un
identificador neutro. El título oficial va en el frontmatter y en `index.md`.

## Comandos

```bash
make descargar-normativa   # vuelve a bajar las 102 normas del BOE (~3 min)
make export-normativa      # genera los 106 preceptos (sin red, sin LLM)
```

`descargar-normativa` solo hace falta cuando el BOE actualiza una norma o se
firma un convenio nuevo: el XML está versionado, así que el export funciona sin
red. Los convenios no se listan a mano, se localizan filtrando por título el
índice de legislación consolidada, que es la lista viva del BOE.

## Lo que falta

- **Dos convenios citados por el corpus no están**: el CDI España-Argentina de
  1992 y el CDI España-Reino Unido de 1975. Ambos fueron sustituidos y ya no
  figuran en la base consolidada. Se pueden recuperar del diario del BOE, como
  el TR del IRPF de 2004, en cuanto se localicen sus identificadores.
- **Nada enlaza todavía la sentencia con el precepto que aplica.** Los análisis
  citan «art. 9 LIRPF» en texto libre; resolver esa cita al fichero
  `lirpf-a9.md` es el siguiente paso natural y lo que haría útil el corpus para
  el chat.
- **El frontend no consume este corpus.** `frontend/scripts/build-corpus.mjs`
  solo lee el JSONL de sentencias.
