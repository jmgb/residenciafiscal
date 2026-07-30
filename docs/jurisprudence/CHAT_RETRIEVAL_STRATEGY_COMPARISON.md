# Comparación de estrategias de respuesta jurisprudencial

**Estado:** decisión de producto documentada; implementación pendiente.
**Alcance inicial:** las cinco sentencias piloto.
**Fecha de decisión:** 2026-07-30.

## Decisión

Durante la fase experimental, cada mensaje del usuario producirá dos respuestas
consecutivas y visualmente separadas:

1. **Respuesta A — Sistema estructurado actual.**
2. **Respuesta B — Gemini File Search.**

Las dos estrategias reciben la misma pregunta y el mismo historial permitido,
pero trabajan de forma independiente. Ninguna puede consumir la respuesta, los
candidatos, las puntuaciones ni las conclusiones de la otra.

El objetivo es comparar con evidencia qué enfoque recupera y explica mejor las
sentencias. Las dos respuestas no implican que existan dos verdades jurídicas:
son resultados experimentales que el abogado puede contrastar con sus fuentes.

## Qué se compara

### Respuesta A — sistema estructurado actual

Usa el flujo propio del repositorio:

1. analiza la pregunta y determina si debe responder, preguntar, responder
   parcialmente o abstenerse;
2. recupera unidades jurídicas v3 por cuestión, hechos, pruebas, reglas,
   holdings y facetas;
3. aplica ranking auditable, diversificación y selección de casos de apoyo y
   contraste;
4. entrega al redactor únicamente las unidades seleccionadas;
5. resuelve cada cita contra los anclajes verbatim y el PDF original.

Su fuente de recuperación son los casos canónicos y sus índices derivados, no
los Markdown completos ni todos los PDF dentro del contexto del modelo.

### Respuesta B — Gemini File Search

Usa únicamente Gemini File Search para recuperar sobre los PDF originales de la
misma muestra y para fundamentar su respuesta:

1. los cinco PDF piloto se importan directamente a un File Search Store
   experimental;
2. File Search realiza chunking, embeddings y búsqueda semántica;
3. Gemini redacta usando solo los fragmentos recuperados por esa herramienta;
4. no recibe unidades v3, candidatos, scores, holdings ni resultados generados
   por la estrategia A;
5. las citas devueltas por el proveedor se contrastan localmente antes de
   mostrarse como extractos judiciales.

Se pueden adjuntar metadatos deterministas como `judgment_id`,
`source_sha256`, órgano y fecha. No se adjunta el análisis jurídico derivado:
la finalidad es comparar el sistema estructurado con File Search sobre la
fuente original, no hacer que File Search reutilice el resultado del primero.

Gemini File Search admite PDF, configuración básica de chunking, `topK`,
filtros por metadatos y anotaciones de cita y página. La documentación oficial
vigente está en
[`ai.google.dev/gemini-api/docs/file-search`](https://ai.google.dev/gemini-api/docs/file-search).

## Formato elegido para File Search

La documentación de Gemini enumera PDF, Markdown y JSON como formatos
compatibles, pero no declara que uno produzca mejor recuperación jurídica. La
elección es, por tanto, una decisión del experimento:

| Formato | Ventaja | Limitación en esta comparación | Decisión |
|---|---|---|---|
| PDF original | Conserva la fuente independiente y permite anotaciones de página | Chunking menos controlable y posible ruido de cabeceras o maquetación | **Entrada inicial de B** |
| Markdown verbatim por páginas | Texto limpio, legible y con límites de página explícitos | Ya incorpora nuestra extracción y añade una transformación intermedia | Diagnóstico posterior separado |
| JSON del caso v3 | Conserva relaciones jurídicas y campos tipados | Reutiliza el análisis de A y deja de medir «File Search solo» | No usar en B |

La respuesta B se construye, por tanto, sobre los cinco PDF originales. No se
suben simultáneamente PDF y derivados al mismo store, porque duplicarían
contenido y harían ambiguo qué representación produjo cada resultado.

Si el experimento posterior sobre Markdown verbatim se ejecuta, será una
variante distinta, con store, versión y métricas propias. Nunca sustituirá el
PDF silenciosamente dentro de B.

Para una eventual unión con reranking local, la entrada semántica preferida sí
podría ser un Markdown generado por cuestión: es más adecuado para embeddings
que el JSON serializado y puede enlazar cada pasaje con sus IDs canónicos. Esa
opción pertenece exclusivamente a la estrategia futura.

## Flujo por mensaje

```text
pregunta + historial permitido
        │
        ├── estrategia A: caso v3 + recuperación local
        │         └── respuesta A + fuentes A
        │
        └── estrategia B: PDF + Gemini File Search
                  └── respuesta B + fuentes B

presentación:
  1. Respuesta A — Sistema estructurado actual
  2. Respuesta B — Gemini File Search
```

La presentación es siempre A y después B. La implementación puede ejecutar
trabajo interno en paralelo para reducir latencia, pero debe almacenar y emitir
cada resultado como una unidad independiente y nunca alimentar una estrategia
con la salida de la otra.

## Contrato visual y semántico

Cada bloque debe mostrar:

- nombre completo de la estrategia;
- estado `completa`, `parcial`, `pregunta`, `abstención` o `error`;
- texto de la respuesta;
- fuentes utilizadas exclusivamente por esa estrategia;
- límites o datos ausentes detectados;
- coste marginal de esa respuesta en USD;
- indicación `real` o `estimado` del coste;
- nota de que no incluye la preparación previa del corpus;
- aviso visible de que se trata de una comparación experimental.

No se permite:

- intercalar párrafos de ambas estrategias;
- compartir una lista de fuentes común;
- presentar una síntesis automática de las dos;
- declarar una estrategia ganadora dentro de la respuesta;
- ocultar que una estrategia falló o no encontró cobertura;
- sustituir automáticamente una respuesta fallida por la de la otra.

Si A falla, B se sigue mostrando. Si B falla, A permanece disponible y el
segundo bloque muestra su error de forma aislada. El cierre global ocurre cuando
ambos bloques alcanzan un estado terminal.

## Autoridad y citas

La independencia de recuperación no elimina las salvaguardas comunes:

1. el PDF original sigue siendo la máxima autoridad;
2. ningún proveedor puede modificar el texto de una sentencia;
3. un extracto solo se rotula como judicial si puede verificarse como texto
   literal de la página declarada;
4. cada fuente conserva estrategia, sentencia, página y `source_sha256`;
5. una cita de File Search no se convierte automáticamente en anclaje canónico;
6. una afirmación sin fuente válida debe retirarse o marcarse como no
   verificada.

La verificación local no altera la estrategia B: actúa después de recuperar y
redactar como gate de seguridad común a cualquier proveedor.

## Protocolo previsto

El protocolo de streaming deberá identificar a qué respuesta pertenece cada
evento. El contrato conceptual es:

```text
answer_start  strategy=current_structured
token         strategy=current_structured
sources       strategy=current_structured
answer_done   strategy=current_structured cost_usd=...

answer_start  strategy=gemini_file_search
token         strategy=gemini_file_search
sources       strategy=gemini_file_search
answer_done   strategy=gemini_file_search cost_usd=...

done
```

La implementación debe evolucionar el protocolo actual antes de activar el
modo comparativo. Los eventos `token` y `sources` nunca pueden carecer de
`strategy`. El frontend debe persistir dos respuestas hermanas asociadas al
mismo mensaje del usuario, no concatenarlas como si fueran una sola.
`answer_done` incluye un objeto de coste:

```json
{
  "currency": "USD",
  "amount_usd": "0.012345",
  "measurement": "ACTUAL",
  "scope": "REQUEST_MARGINAL",
  "pricing_version": "2026-07-30",
  "input_tokens": 8421,
  "output_tokens": 631,
  "retrieved_document_tokens": 0
}
```

`amount_usd` se serializa como decimal y se calcula internamente con
microdólares enteros. `measurement` vale `ACTUAL` cuando el proveedor devuelve
uso completo y `ESTIMATED` en caso contrario. Una respuesta fallida también
muestra y registra el coste incurrido hasta el fallo. `pricing_version`
identifica el catálogo aplicado para poder recalcular y auditar la cifra.

## Medición

La comparación se registra por pregunta y por estrategia:

- conducta: responder, preguntar, parcial o abstenerse;
- cuestiones y sentencias recuperadas;
- recall de casos esperados;
- precisión de casos relevantes;
- presencia de casos de contraste;
- afirmaciones sustantivas con fuente;
- citas exactas, páginas válidas y hashes resolubles;
- latencia al primer token y latencia total;
- tokens de entrada, salida y documentos recuperados;
- coste marginal visible, estimado o real, en USD;
- error o ausencia de resultados.

Las respuestas pueden someterse a revisión humana ciega, ocultando el nombre de
la estrategia durante la valoración. La preferencia humana complementa, pero no
sustituye, los gates objetivos de cita y cobertura.

El holdout E ya observado conserva su política
`OBSERVE_ONLY_NO_TUNING`: no se usa para ajustar ninguna de las dos estrategias.
La decisión posterior exige un nuevo banco ciego congelado.

## Datos, privacidad y coste

- El experimento usa un proyecto Gemini con facturación y `store: false`.
- El File Search Store contiene únicamente sentencias públicas de la muestra.
- Los hechos aportados por el usuario se usan como consulta y no se importan al
  store.
- No se incorporan documentos privados del usuario.
- El índice experimental debe poder eliminarse de forma explícita.
- La reserva de presupuesto incluye el coste máximo de A y B antes de iniciar
  la primera llamada facturable.
- El rate limit cuenta una pregunta del usuario, aunque internamente produzca
  dos respuestas.

El coste visible de A suma router y redacción. El de B suma la generación de
Gemini y los tokens de documento recuperados facturados como contexto. Si una
estrategia se abstiene antes de una llamada, su coste puede ser `USD 0`.

La preparación de los casos v3 de A y la indexación de File Search de B son
costes de corpus, no de una respuesta concreta. Se registran por separado en el
experimento y no se prorratean arbitrariamente entre usuarios. La interfaz
muestra «coste de esta respuesta; no incluye preparación del corpus». El
almacenamiento y los embeddings de consulta se etiquetan según la tarifa
vigente. El coste adicional de B nunca se mezcla con el consumo de A.

Cada petición escribe un log estructurado sin el texto de la consulta ni de la
respuesta:

```json
{
  "request_id": "...",
  "strategy": "gemini_file_search",
  "status": "ok",
  "cost_microusd": 12345,
  "cost_measurement": "ACTUAL",
  "pricing_version": "2026-07-30",
  "model": "...",
  "input_tokens": 8421,
  "retrieved_document_tokens": 5100,
  "output_tokens": 631,
  "latency_ms": 2840
}
```

Debe existir un registro por estrategia y pregunta, correlacionado por
`request_id`. Los dashboards pueden sumar A y B, pero conservan siempre el
desglose individual que ve el usuario.

## Posible estrategia futura: unión y reranking local

Se conserva como opción futura, no implementada ni aprobada:

```text
candidatos del sistema estructurado
              +
candidatos de Gemini File Search
              ↓
normalización a identidades canónicas
              ↓
reranking y diversificación local
              ↓
una única respuesta con anclajes verificados
```

Esta tercera estrategia solo se evaluará después de medir A y B por separado.
Su adopción requerirá demostrar que mejora recuperación o contraste sin reducir
precisión, trazabilidad, reproducibilidad ni seguridad de citas.

Hasta entonces:

- no se mezclan candidatos;
- no existe respuesta híbrida;
- no se usa File Search como autoridad jurídica;
- no se amplía el experimento a las 106 sentencias.

## Criterio de salida

El modo de dos respuestas es experimental. Antes de elegir una estrategia
productiva deben existir:

- resultados comparables sobre el banco de desarrollo;
- revisión humana de una muestra de respuestas;
- un nuevo holdout ciego;
- medición de coste y latencia;
- coste individual visible y reconciliable con los logs;
- 100 % de citas mostradas verificables;
- decisión explícita documentada: A, B, unión futura o mantenimiento del
  experimento.
