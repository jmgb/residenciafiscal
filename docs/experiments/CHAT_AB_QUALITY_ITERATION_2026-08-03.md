# Iteración de calidad A/B del 3 de agosto de 2026

**Estado:** smoke real completado; no sustituye la revisión jurídica ciega.
**Configuración final probada:** A `structured-claims-v3`; B
`file-search-authority-v6`; Gemini `gemini-3.5-flash-lite`; corpus de 106 PDF.

## Hallazgo que motivó la iteración

El filtro desplegado `judgment_id="sts-*"` era una regresión real. Sobre el store
anterior, la misma consulta recuperó seis citas sin filtro y ninguna con el
comodín. No era seguro interpretar ese vacío como ausencia de jurisprudencia.

Se creó de forma reversible un store nuevo con 106/106 PDF y metadatos exactos
`authority="tribunal_supremo"` / `authority="audiencia_nacional"`. El recurso
nuevo es `fileSearchStores/residenciafiscalrollout106a-zwmb28labwje`; el anterior
se conserva para rollback. Las consultas finales recuperaron exclusivamente
resoluciones del órgano solicitado.

## Cambios evaluados

- A enlaza cada afirmación atómica con sus extractos exactos y descarta
  afirmaciones sin relación literal suficiente. Los anclajes breves se amplían
  desde el artefacto verbatim, verificando hash, página y offsets.
- A responde primero a la pregunta y ya no muestra como límites los campos
  personales ausentes en consultas jurídicas generales.
- B usa igualdad exacta por autoridad y distingue permanencia, residencia
  extranjera, ausencias esporádicas y CDI. No atribuye al tribunal argumentos de
  las partes o de la instancia y debe contestar todas las partes de la pregunta.
- Los tokens de recuperación que Gemini devuelve como `total_tool_use_tokens`
  se contabilizan como documentos. Antes podían aparecer como cero y dejar el
  coste infravalorado.
- Ambas estrategias fallan cerrado si no pueden publicar evidencia verificable.

## Batería final real

Las llamadas se ejecutaron directamente contra los dos proveedores con la misma
pregunta y el nuevo store. Latencia y coste son observaciones de una sola
ejecución por celda; no son percentiles.

| Pregunta | A: estado / fuentes / latencia / coste | B: estado / fuentes / latencia / coste |
|---|---|---|
| Pruebas que acepta el TS para desvirtuar 183 días | Parcial / 2 / 15,437 s / USD 0,003257 | Completa / 1 / 6,300 s / USD 0,002339 |
| Ausencias esporádicas y cuándo computan según el TS | Parcial / 3 / 18,557 s / USD 0,003276 | Completa / 2 / 8,558 s / USD 0,005707 |
| Indicios usados por la AN para el centro de intereses económicos | Completa / 3 / 11,845 s / USD 0,002791 | Completa / 3 / 5,653 s / USD 0,002571 |

Media observada: A, 15,280 s y USD 0,003108; B, 6,837 s y USD
0,003539. B fue 2,2 veces más rápida, pero no resultó sistemáticamente más
barata una vez incluidos los documentos recuperados.

## Valoración provisional

A fue mejor en trazabilidad y detalle probatorio. En la pregunta de la Audiencia
Nacional enumeró indicios concretos —retribuciones, consejos, sociedades,
fundaciones, arte y movimientos bancarios— y dejó claro que ninguno era
necesariamente decisivo por sí solo. Cada afirmación quedó vinculada a sus
fuentes.

B fue mejor en concisión y latencia. Tras las iteraciones, dio una formulación
directa y correcta de las ausencias esporádicas: son temporales u ocasionales,
computan en la permanencia y se aplica la salvedad de residencia fiscal
acreditada en otro país. En preguntas probatorias tiende a sintetizar categorías
generales y sus citas siguen vinculadas a la respuesta completa, no a cada
afirmación individual.

La decisión sigue abierta. Con tres preguntas no hay base para elegir un ganador
global. La vista ciega con voto ya está implementada: dos columnas en escritorio,
pestañas en móvil y una sola columna cuando únicamente hay una respuesta. El
siguiente gate válido es recoger votos sobre un banco congelado y someterlo a
revisión jurídica humana. El voto mide preferencia; no sustituye los
gates de autoridad directa, literalidad y cobertura.

## Reproducibilidad y despliegue

El runtime persiste desde esta versión el experimento, commit desplegado, store,
versiones de prompt, filtros, resoluciones recuperadas, citas verificadas,
claims de A y diagnóstico acotado en Supabase. Las llamadas exploratorias de
este documento fueron directas y no se insertaron como tráfico de usuario.

Para activar B debe desplegarse el código y cambiar conjuntamente
`CHAT_FILE_SEARCH_STORE_NAME` al recurso nuevo. No se debe cambiar solo la
variable mientras siga desplegado el filtro con comodín.
