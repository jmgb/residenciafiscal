NORMATIVA DE RESIDENCIA FISCAL - INVENTARIO
============================================

XML de las normas espanolas que deciden la residencia fiscal de una persona
fisica (Art. 9 LIRPF) y de los convenios de doble imposicion firmados por
Espana, descargado de la API de datos abiertos del BOE.

TOTAL: 104 normas (14,7 MB de texto)

DESGLOSE
--------
- Nucleo estatal vigente:     5 normas
- Nucleo estatal derogado:    1 norma
- Convenios de doble imp.:   96 convenios vigentes (1967-2021)
- Convenios sustituidos:      2 convenios (Argentina 1992, Reino Unido 1975)

NUCLEO ESTATAL
--------------
BOE-A-2006-20764  Ley 35/2006, IRPF                  -> arts. 8, 9, 10, 72
BOE-A-2003-23186  Ley 58/2003, General Tributaria    -> arts. 105, 106, 108
BOE-A-2004-4527   RDLeg 5/2004, TR del IRNR          -> art. 6
BOE-A-2007-6820   RD 439/2007, Reglamento del IRPF   -> art. 120
BOE-A-2023-3508   Orden HFP/115/2023, jurisdicciones no cooperativas
BOE-A-2004-4347   RDLeg 3/2004, TR del IRPF (DEROGADO) -> arts. 8, 9

El texto refundido de 2004 esta derogado por la Ley 35/2006, pero rige los
ejercicios 2005 y 2006, que aparecen en el corpus de sentencias.

NOMENCLATURA DE ARCHIVOS
------------------------
{BOE-ID}.meta.xml    Metadatos de la norma (titulo, rango, vigencia, ELI)
{BOE-ID}.texto.xml   Texto consolidado completo, con todas sus redacciones
{BOE-ID}.diario.xml  Publicacion original (solo para normas derogadas)
manifest.json        Inventario generado: hash, fechas y URL de cada norma

FUENTE
------
Agencia Estatal Boletin Oficial del Estado
https://www.boe.es/datosabiertos/

- Legislacion consolidada: https://www.boe.es/datosabiertos/api/legislacion-consolidada
- Diario del BOE:          https://www.boe.es/diario_boe/xml.php

COMO SE REGENERA
----------------
  make descargar-normativa   Vuelve a bajar todo del BOE (unos 3 minutos)
  make export-normativa      Genera knowledge/normativa/es/preceptos/ (sin red)
  make enlazar-normativa     Resuelve las citas de las sentencias a los preceptos

Solo la primera necesita red: las otras dos trabajan sobre el XML versionado en
este directorio.

NORMAS DEROGADAS
----------------
Cuatro preceptos son de normas ya sustituidas. Estan porque rigen ejercicios que
las sentencias del corpus enjuician, y se publican rotulados como derogados:

- RDLeg 3/2004, TR del IRPF        -> ejercicios hasta 2006
- CDI Espana-Argentina 1992        -> ejercicios hasta 2012
- CDI Espana-Reino Unido 1975      -> ejercicios hasta 2013

El BOE saca de la base consolidada lo que deroga, asi que estas se descargan del
diario, que conserva la publicacion original.

JURISDICCION
------------
Este directorio es el corpus de Espana (codigo ISO 3166-1 alfa-2: es). Un pais
nuevo anade su propio directorio hermano; ver docs/normativa/NORMATIVA.md.

Ver AVISO_LEGAL.md para el origen, las condiciones de reutilizacion y el
alcance de estos ficheros.
