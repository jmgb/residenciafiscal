NORMATIVA DE RESIDENCIA FISCAL - INVENTARIO
============================================

XML de las normas espanolas que deciden la residencia fiscal de una persona
fisica (Art. 9 LIRPF) y de los convenios de doble imposicion firmados por
Espana, descargado de la API de datos abiertos del BOE.

TOTAL: 106 normas (14,2 MB de texto)

DESGLOSE
--------
- Nucleo estatal vigente:     5 normas
- Nucleo estatal derogado:    1 norma
- Convenios de doble imp.:   95 convenios generales vigentes (1967-2024)
- Convenios sustituidos:      2 convenios (Argentina 1992, Reino Unido 1975)
- Convenios sectoriales:      2 convenios (Venezuela 1986, Argentina 1978)
- Ley interna, no convenio:   1 norma (Ley 10/1996)

Las tres ultimas llegaron al corpus porque su titulo dice "doble imposicion",
pero no son un convenio general de renta y no contienen regla de residencia:
dos son convenios de navegacion maritima y aerea y la tercera es derecho interno
sobre doble imposicion intersocietaria. El manifiesto las separa en los grupos
cdi_sectorial e interna_no_cdi (src/descargar_normativa.py, RECLASIFICACION)
para que la relacion bilateral de Venezuela no acabe apuntando a un convenio de
navegacion con el nombre correcto encima.

Dos de los 95 convenios generales vigentes no salen del indice consolidado
y estan declarados a mano en src/descargar_normativa.py (CDI_NO_CONSOLIDADO):

- BOE-A-2004-11070  CDI Espana-Venezuela 2003: su titulo dice "doble
                    tributacion", asi que el filtro por "doble imposicion" del
                    indice del BOE no lo encuentra.
- BOE-A-2024-15573  CDI Espana-Paraguay 2023: el BOE todavia no lo ha
                    incorporado a la base consolidada.

Ambos se descargan del diario, igual que las normas derogadas, pero estan en
vigor: el grupo del manifiesto los distingue (cdi, no cdi_derogado).

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
{BOE-ID}.diario.xml  Publicacion original (normas derogadas y convenios que el
                     BOE no sirve consolidados)
manifest.json        Inventario generado: hash, fechas, fuente y URL de cada norma

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

Para incorporar una norma suelta sin volver a bajar las 106, el descargador
admite una lista de identificadores y fusiona el manifiesto existente:

  uv run python src/descargar_normativa.py --solo BOE-A-2024-15573

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
