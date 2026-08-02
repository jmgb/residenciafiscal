# Comparación de estrategias de respuesta jurisprudencial

**Estado:** F0.2 conserva el baseline de ocho consultas; F0.3 tiene rúbrica y
paquete ciego listos; A/B está activo en producción sobre las 106 sentencias.
La revisión jurídica y el banco conversacional de 40 siguen pendientes. La
opción C agentiva queda solo documentada como posibilidad futura.
**Alcance:** piloto inicial de cinco y runtime productivo sobre 106 sentencias.
**Fecha de actualización:** 2026-08-02.

La vista consolidada de capas, componentes, estado, aprendizajes y siguiente
gate está en
[`CHAT_SYSTEM_ARCHITECTURE.md`](CHAT_SYSTEM_ARCHITECTURE.md). Este documento
conserva el contrato especializado del experimento A/B.

## Implementación F0 y baseline histórico

La fase F0 creó el comparador local que sigue disponible por CLI. El mismo
dominio está expuesto en el prototipo por FastAPI, un proxy fino de Netlify Edge
y el cliente comparativo. Ese recorrido se conserva como opción futura si se
necesitan llamadas de más de 60 s. La V1 ya está portada a una Netlify Function
TypeScript, con ambas estrategias en paralelo y deadline de 50–55 s, y
`VITE_CHAT_MODE=live` está activo en producción desde el 31 de julio de 2026.
B usa el
SDK oficial `google-genai`, la Interactions API y un store basado en
`models/gemini-embedding-2`.

Interactions exige `google-genai >= 2.0.0`: el esquema anterior dejó de
aceptarse en junio de 2026. El proyecto fija la serie 2.x y tiene un test de
regresión que impide volver a instalar una versión 1.x.

El modelo inicial de pruebas es `gemini-3.5-flash-lite`, elegido para medir el
flujo completo con menor coste. `gemini-3.6-flash` está en la allowlist, pero el
cambio será manual y visible: no se usa un alias `latest` ni existe promoción
automática. Después de revisar calidad, citas, latencia y coste de las primeras
comparaciones se ejecutará explícitamente:

```bash
make compare-chat-strategies \
  CONFIRM_PAID=1 \
  FILE_SEARCH_MODEL=gemini-3.6-flash \
  CHAT_QUESTION='...'
```

Cambiar el modelo de generación no exige recrear el store: los cinco PDF siguen
indexados con `models/gemini-embedding-2`. Cada resultado y log conserva el ID
del modelo realmente usado.

Los comandos que pueden generar coste exigen confirmación redundante:

```bash
# Crea un store nuevo y sube exactamente los cinco PDF del manifiesto.
make file-search-prepare CONFIRM_PAID=1

# Ejecuta una pregunta contra A y B y muestra el coste individual.
make compare-chat-strategies \
  CONFIRM_PAID=1 \
  FILE_SEARCH_MODEL=gemini-3.5-flash-lite \
  CHAT_QUESTION='¿Qué valor se dio al certificado fiscal extranjero?'

# Elimina el store remoto y su estado local.
make file-search-delete CONFIRM_DELETE=1
```

El estado del store se guarda fuera del corpus, en
`output/file-search/f0-store.json`. Cada comparación produce un JSON con ambas
respuestas y añade dos registros, sin pregunta ni respuesta, a
`output/logs/chat-strategy-comparison.jsonl`.

Los tests no crean stores, no suben PDFs y no llaman a Gemini. La preparación
valida los cinco hashes antes de crear ningún recurso remoto y elimina el store
incompleto si una subida falla.

### Coste por modelo

El catálogo F0 aplica las tarifas estándar vigentes y las identifica con
`pricing_version: 2026-07-31`:

| Modelo | Entrada y documentos recuperados | Salida, incluido razonamiento |
|---|---:|---:|
| `gemini-3.5-flash-lite` | USD 0,30 / 1 M tokens | USD 2,50 / 1 M tokens |
| `gemini-3.6-flash` | USD 1,50 / 1 M tokens | USD 7,50 / 1 M tokens |

Interactions devuelve el total y el desglose por modalidad. F0 separa los
tokens `document` recuperados de la entrada textual, suma los tokens de
razonamiento a la salida facturable y calcula el resultado con microdólares
enteros. El log conserva modelo, tokens y tarifa versionada para que cada
llamada pueda reconciliarse o recalcularse.

Si existen citas de File Search pero el proveedor omite la modalidad
`document`, el coste se marca `ESTIMATED`: `retrieved_document_tokens: 0`
significa «no informado», no «recuperación gratuita». El importe mostrado es
entonces un límite inferior formado por los tokens que sí devolvió la API. No
se permite rotularlo como `ACTUAL`, porque los documentos recuperados se cobran
como contexto.

La indexación del store —USD 0,15 / 1 M tokens según la tarifa vigente— es coste
de preparación del corpus y no se mezcla con el coste marginal de una
respuesta. Almacenamiento y embedding de consulta no añaden coste; los
documentos recuperados se cobran como contexto de entrada.

### Primer smoke real

El 30 de julio de 2026 se creó el store con los cinco PDF y se verificaron sus
IDs, rutas y SHA-256 contra
`sentencias/jurisprudence_v3_sample_5.json`. La primera pregunta fue:

> ¿Qué tiene en cuenta Hacienda para demostrar la residencia fiscal en España?

| Estrategia | Estado | Latencia | Fuentes exactas | Coste marginal |
|---|---|---:|---:|---:|
| A — estructurada | Completa | 12 ms | 49 | USD 0,000000 real |
| B — File Search | Completa | 7.883 ms | 3 | ≥ USD 0,001761 estimado |

B produjo una respuesta directamente organizada por permanencia, intereses
económicos, presunción familiar e indicios complementarios. Sus tres extractos
se verificaron literalmente en `SAN 1136/2016`, `SAN 1386/2017` y
`SAN 1071/2025`. A recuperó las cinco sentencias y sus contracasos, pero
respondió como inventario de resultados por caso y aportó 49 fragmentos; para
esta pregunta general fue menos directa y demasiado extensa.

La API devolvió 86 tokens de entrada textual y 694 de salida para B, pero no
declaró los tokens de los documentos recuperados. El artefacto del smoke se
generó antes de añadir el guardarraíl y contiene una etiqueta `ACTUAL` que esta
medición invalida; el importe debe interpretarse como el límite inferior
estimado de la tabla. Las llamadas posteriores ya quedan protegidas por test.

Un intento anterior no generó tokens: detectó que `google-genai 1.75.0` usaba
el esquema retirado de Interactions. Se migró a `2.16.0` antes del smoke
válido. Estos resultados son una observación de una pregunta, no una decisión
entre estrategias.

### F0.2 — redactor comparable y evaluación de desarrollo

F0.2 sustituye la salida determinista inicial de A por un redactor LLM sobre su
recuperación estructurada. A y B usan `gemini-3.5-flash-lite` y comparten la
misma instrucción jurídica base. Sus contratos de grounding son distintos por
diseño: A devuelve IDs `E<n>` que el servidor resuelve a anclajes exactos; B
solo publica las anotaciones de File Search verificadas localmente.

A entrega al redactor un máximo de dos fragmentos por unidad recuperada. En dos
smokes sucesivos de la misma pregunta general, este límite redujo su entrada de
31.038 a 8.954 tokens y el coste de USD 0,010731 a USD 0,003499, manteniendo
representadas las cinco sentencias.

Se ejecutaron ocho preguntas reales con el mismo modelo en ambas estrategias.
Una respuesta sustantiva sin fuentes verificables pasa a `error` y se retira,
pero conserva su coste. Preguntar o abstenerse en el router de A evita la
llamada y cuesta USD 0.

La evaluación reveló que las etiquetas del banco original están diseñadas para
el router de A y no son una rúbrica neutral. También detectó falta de cobertura
estructurada sobre ausencias esporádicas. Por ello no se ejecutan aún las 40
preguntas ni se promociona el modelo. Método, métricas, costes y decisión:
[`CHAT_STRATEGY_F02_RESULTS.md`](../experiments/CHAT_STRATEGY_F02_RESULTS.md).

### Configuración vigente posterior a F0.2

El baseline anterior conserva valor porque controló el modelo. La configuración
destinada al producto ya no lo comparte: A usa la política Luna + `high`; B debe
usar uno de los modelos Gemini permitidos por File Search. Las próximas ocho
preguntas compararán por tanto stacks completos. Una diferencia observada no se
puede atribuir exclusivamente a la recuperación.

La frontera, los motivos y el tratamiento de coste están en
[`LLM_GATEWAY.md`](../development/LLM_GATEWAY.md). El despliegue cerrado por
defecto está en [`CHAT_DEPLOYMENT.md`](../operations/CHAT_DEPLOYMENT.md).

## Decisión

Durante la fase experimental, cada mensaje del usuario producirá dos respuestas
consecutivas y visualmente separadas:

1. **Respuesta A — Sistema estructurado actual.**
2. **Respuesta B — Gemini File Search.**

Las dos estrategias reciben la misma última pregunta autosuficiente, pero
trabajan de forma independiente. El historial permanece local en esta versión
single-turn. Ninguna puede consumir la respuesta, los candidatos, las
puntuaciones ni las conclusiones de la otra.

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
4. entrega al redactor las unidades seleccionadas y como máximo dos fragmentos
   verificables por unidad;
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

La presentación es siempre A y después B. La V1 debe ejecutar ambas estrategias
en paralelo para reducir latencia, pero debe almacenar y emitir
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
  "pricing_version": "2026-07-31",
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

Cada petición escribe un log operativo estructurado sin el texto de la consulta
ni de la respuesta. Separadamente, Supabase persiste en schema privado la
pregunta y ambas respuestas con citas y costes para comparar calidad:

```json
{
  "request_id": "...",
  "strategy": "gemini_file_search",
  "status": "ok",
  "cost_microusd": 12345,
  "cost_measurement": "ACTUAL",
  "pricing_version": "2026-07-31",
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
- no se activa la unión ni en el piloto ni en el runtime productivo de 106.

## Posible estrategia futura C: investigación agentiva

**Estado de decisión:** posibilidad documentada; no implementada, presupuestada
ni autorizada para tráfico real. No cambia el contrato A/B vigente.

C sería una investigación de mayor profundidad en la que un agente pudiera
iterar sobre el corpus: formular búsquedas, leer unidades v3, abrir páginas
verbatim, ampliar o descartar candidatos, contrastar varias resoluciones y
verificar si la evidencia sostiene cada afirmación antes de responder. Un
piloto puede usar Codex como explorador de archivos; una eventual versión de
producto debe exponer herramientas jurídicas estrechas en lugar de shell y
acceso general al repositorio.

La documentación oficial permite controlar Codex desde servidor mediante el
[Codex SDK](https://learn.chatgpt.com/docs/codex-sdk), ejecutarlo de forma
[no interactiva](https://learn.chatgpt.com/docs/non-interactive-mode) con salida
estructurada y limitarlo con un sandbox de solo lectura. Si Codex fuese un
especialista dentro de una orquestación mayor, la ruta documentada es
[Codex como MCP con Agents SDK](https://learn.chatgpt.com/docs/mcp-server). Estas
interfaces hacen viable un prototipo, pero no deciden por sí mismas que Codex
sea el runtime jurídico definitivo. Los límites de permisos se regirían por el
contrato oficial de [sandbox y aprobaciones](https://learn.chatgpt.com/docs/sandboxing).

### Objetivo y encaje

C persigue dos usos posibles:

1. medir un techo de calidad frente a A y B con más tiempo y herramientas;
2. ofrecer «Investigación profunda» bajo demanda cuando las respuestas rápidas
   discrepen, sean parciales, se abstengan o no aporten autoridad directa.

No persigue sustituir el pipeline offline, modificar casos v3, navegar por
fuentes externas ni decidir automáticamente cuál de las otras respuestas es
correcta. Si C dispone de internet o de un corpus distinto, deja de ser
comparable con A y B y debe tratarse como otro experimento.

```text
pregunta
   ├── A — corpus estructurado ───────┐
   ├── B — Gemini File Search ────────┼── comparación rápida
   │                                  │
   └── C — investigación profunda ◄───┘
          activación explícita o por criterio medido
             └── worker asíncrono
                    └── búsqueda y lectura iterativas
                           └── salida estructurada
                                  └── verificador determinista
```

### Ventajas y desventajas

| Dimensión | Ventaja potencial | Coste o riesgo |
|---|---|---|
| Recuperación | Reformula consultas y amplía la búsqueda cuando un primer intento falla | Menor reproducibilidad si no se congelan herramientas, modelo y presupuesto |
| Profundidad | Puede leer contexto completo y separar presencia, residencia extranjera y CDI | Más latencia y consumo que las rutas rápidas |
| Contraste | Puede comparar varias resoluciones y buscar apoyo y contraejemplos | Riesgo de exploración excesiva o de seleccionar evidencia después de ver la conclusión |
| Grounding | Puede revisar si una cita sostiene una proposición antes de entregarla | La autorrevisión del agente no sustituye la validación literal local |
| Cobertura | Puede rescatar preguntas parciales o desacuerdos A/B | Un agente más flexible también puede producir respuestas plausibles fuera de alcance |
| Producto | Permite una modalidad diferenciada de investigación profunda | Complica UX, presupuestos, cancelación, retención y soporte operativo |
| Evaluación | Sirve como referencia superior para medir margen de mejora | Ya no aísla recuperación: compara un stack completo con más recursos |

### Fronteras de seguridad y operación

Un piloto aceptable debe cumplir simultáneamente:

- ejecutarse fuera de la Netlify Function síncrona, en un worker asíncrono con
  timeout y cancelación;
- crear un entorno efímero por petición y montar en solo lectura únicamente los
  PDF, verbatim, casos e índices permitidos;
- excluir `.env`, credenciales, configuración de despliegue, historial Git y
  cualquier otro repositorio;
- deshabilitar red y escritura, salvo un directorio temporal desechable;
- tratar todo texto recuperado como datos, nunca como instrucciones;
- ofrecer herramientas acotadas como `buscar_sentencias`,
  `buscar_en_sentencia`, `leer_paginas`, `leer_unidad_v3`,
  `comparar_resoluciones` y `verificar_cita`;
- fijar límites de tiempo, turnos, llamadas de herramienta, documentos, páginas
  y coste antes de iniciar la ejecución;
- exigir JSON Schema con estado, respuesta, límites, afirmaciones y evidencias;
- resolver citas contra el verbatim/PDF mediante código determinista y retirar
  cualquier afirmación sustantiva sin apoyo válido;
- no persistir ni mostrar cadena de pensamiento. La traza operativa conserva
  solo herramientas invocadas, IDs de sentencia/página, métricas, estados y
  códigos de fallo seguros.

La pregunta fiscal y la respuesta seguirían bajo el mismo contrato privado de
retención que A/B. Antes de tráfico real deben revisarse además el mecanismo de
autenticación del worker, la retención propia del runtime elegido y el acuerdo
de tratamiento aplicable.

### Comparabilidad y gate de promoción

El piloto no se ejecutará antes de cerrar el baseline jurídico ciego de A/B.
Después debe usar una muestra pequeña de preguntas difíciles separada del
holdout y mantener constantes:

- corpus y fecha de corte;
- ausencia de internet;
- contrato de respuesta y verificación;
- presupuesto máximo de herramientas, tiempo y coste;
- versión del agente, modelo, instrucciones y herramientas;
- rúbrica ciega, sin revelar A/B/C al revisor.

Los gates binarios siguen siendo cero identificadores inventados, autoridad
correcta, todas las citas literales y ninguna afirmación sustantiva sin apoyo.
Solo después se comparan utilidad jurídica, cobertura, claridad, latencia,
coste y tasa de cancelación. C se promueve únicamente si aporta una mejora
relevante y repetible que compense su coste operativo. Si no, permanece como
diagnóstico offline o herramienta interna de evaluación.

### Presentación futura

C no debe convertirse en una tercera columna larga ni retrasar siempre A/B. La
interfaz propuesta es un botón explícito «Iniciar investigación profunda» o una
oferta posterior a una discrepancia. Mientras corre muestra estados objetivos
—búsqueda, lectura y verificación—, no razonamiento interno. Al terminar añade
un bloque o pestaña C independiente, con fuentes, límites, coste y latencia, y
permite votar A, B, C o empate. Nunca sustituye una respuesta anterior ni se
declara ganadora automáticamente.

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
