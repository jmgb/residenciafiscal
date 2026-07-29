# Aviso legal sobre los textos normativos

Este directorio contiene el XML de normas españolas sobre residencia fiscal —la
Ley del IRPF, la Ley General Tributaria, sus reglamentos y los convenios de
doble imposición firmados por España—, junto con el inventario (`readme.txt`) y
el manifiesto de descarga (`manifest.json`).

## Origen

Todo procede de la **API de datos abiertos de la Agencia Estatal Boletín Oficial
del Estado** (<https://www.boe.es/datosabiertos/>), en dos endpoints:

- **Legislación consolidada** para las normas vigentes: el BOE mantiene el texto
  al día e identifica cada precepto con su fecha de vigencia.
- **Diario del BOE** para las normas derogadas, que salen de la base
  consolidada y solo conservan su publicación original.

Se descargan tal cual los publica el BOE, sin modificar su contenido. La
descarga es reproducible con `make descargar-normativa`.

## Naturaleza de los documentos

- Son **documentos públicos**. El art. 9.3 de la Constitución garantiza la
  publicidad de las normas, y el BOE es el diario oficial que las publica.
- La reutilización de la información del BOE se rige por sus propias condiciones
  y por la Ley 37/2007 de reutilización de la información del sector público.
  Consúltalas antes de redistribuir estos ficheros o construir un producto sobre
  ellos: <https://www.boe.es/informacion/aviso_legal/>.
- El BOE advierte de que **la única versión con valor jurídico es la publicada
  en su edición oficial**. El texto consolidado es una herramienta de consulta
  sin carácter oficial, y estos ficheros son una copia de esa herramienta.

## Cómo se usan aquí

El XML se incluye en el repositorio con la misma finalidad que los PDF de
`sentencias/`: que el corpus sea **reproducible y auditable**. Los preceptos
publicados en `knowledge/normativa/preceptos/` se generan a partir de estos
ficheros y de ningún otro sitio, de modo que cualquiera puede comprobar que el
texto no se ha alterado.

**El articulado no se reescribe, corrige ni parafrasea en ningún punto del
pipeline.** La única transformación es de formato —colapsar espacios en blanco y
separar los párrafos— y hay un test que verifica que cada párrafo publicado es
una cadena idéntica a la del XML de origen. Las notas editoriales del propio BOE
(«Redactado conforme a…», «Se modifica por…») se recogen en una sección aparte
porque no forman parte del precepto.

## Vigencia

Un texto consolidado refleja la redacción vigente en la fecha de descarga, que
consta en `manifest.json`. Las sentencias del corpus se refieren a ejercicios
pasados y pueden estar aplicando una redacción anterior: por eso cada precepto
publicado conserva **todas** sus redacciones con la fecha desde la que rigió
cada una. Aun así, comprueba siempre contra el BOE qué redacción aplicaba al
ejercicio que estés analizando.

## Descargo de responsabilidad

Este repositorio no es una fuente oficial de legislación ni sustituye al BOE.
El análisis automático que produce el proyecto se genera con modelos de lenguaje
y **puede contener errores u omisiones**. No es asesoramiento jurídico ni
fiscal, ni sustituye la lectura del texto oficial ni el criterio de un
profesional.
