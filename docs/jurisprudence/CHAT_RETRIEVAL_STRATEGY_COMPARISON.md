# Comparación de estrategias de respuesta jurisprudencial

**Estado:** F0.2 conserva el baseline de ocho consultas; F0.3 tiene rúbrica y
paquete ciego listos; A/B está activo y configurable en producción sobre las 106
sentencias.
La iteración real del 3 de agosto corrigió el filtro de autoridad de B, añadió
trazabilidad por afirmación en A y versionó el ledger del experimento. La vista
ciega con voto usa dos columnas en escritorio y pestañas en móvil cuando A y B
están activas; si solo existe una respuesta conserva una única columna. La
revisión jurídica y el banco conversacional de 40 siguen pendientes. La opción
C agentiva tiene ya una arquitectura de piloto acordada y una implementación
técnica desplegada bajo bandera, pero no está autorizada para tráfico real.
**Alcance:** piloto inicial de cinco y runtime productivo sobre 106 sentencias.
**Fecha de actualización:** 2026-08-03.

La vista consolidada de capas, componentes, estado, aprendizajes y siguiente
gate está en
[`CHAT_SYSTEM_ARCHITECTURE.md`](CHAT_SYSTEM_ARCHITECTURE.md). Este documento
conserva el contrato especializado del experimento A/B.

## Implementación F0 y baseline histórico

La fase F0 creó el comparador local que sigue disponible por CLI. El mismo
dominio está expuesto en el prototipo por FastAPI, un proxy fino de Netlify Edge
y el cliente comparativo. Ese recorrido se conserva como opción futura si se
necesitan llamadas de más de 60 s. La V1 ya está portada a una Netlify Function
TypeScript, con las estrategias activas en paralelo y deadline de 50–55 s, y
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

Interactions devuelve el total y el desglose de uso. El adaptador admite tanto
el contrato histórico `input_tokens_by_modality=document` como el contrato
observado en agosto de 2026, que declara la recuperación en
`total_tool_use_tokens`. Esos tokens se separan como documentos recuperados, se
suman a la entrada facturable y se conservan junto con la tarifa versionada para
reconciliar o recalcular cada llamada.

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

A entregaba en F0.2 al redactor un máximo de dos fragmentos por unidad recuperada. En dos
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

Durante la fase experimental, la configuración comparativa con A y B activas
producirá dos respuestas consecutivas y visualmente separadas:

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
4. entrega al redactor las unidades seleccionadas y hasta cuatro fragmentos
   verificables por unidad: el mejor match léxico y, si existen, muestras de
   resultado, razonamiento y carga de la prueba;
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

Se adjuntan metadatos deterministas como `judgment_id`, `source_sha256`,
`authority`, órgano y fecha. `authority` usa los valores cerrados
`tribunal_supremo` y `audiencia_nacional`; una consulta de órgano aplica igualdad
exacta, no un comodín sobre `judgment_id`. La prueba real demostró que
`judgment_id="sts-*"` producía un falso vacío aunque el store sí contuviera
sentencias del Supremo. No se adjunta el análisis jurídico derivado:
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
  1. Opción A
  2. Opción B
```

La presentación conserva el orden A y después B cuando ambas están activas. La V1
ejecuta en paralelo las estrategias activas para reducir latencia, pero debe
almacenar y emitir
cada resultado como una unidad independiente y nunca alimentar una estrategia
con la salida de la otra.

## Contrato visual y semántico

El objetivo aprobado para el experimento es una comparación ciega: durante el
voto se muestran `Opción A` y `Opción B`, no los nombres de proveedor o sistema.
En escritorio, la variante aprobada usa dos columnas alineadas; en móvil, dos
pestañas conservan el ancho legible. Este patrón solo se activa cuando hay dos
opciones. Con una única estrategia activa se mantiene una respuesta centrada en
una sola columna, sin pestañas, aviso experimental ni formulario de voto.

Cada bloque debe mostrar:

- etiqueta ciega A/B; la identidad técnica queda en el ledger y puede revelarse
  después del voto o en metodología;
- estado `completa`, `parcial`, `pregunta`, `abstención` o `error`;
- texto de la respuesta;
- fuentes utilizadas exclusivamente por esa estrategia;
- límites o datos ausentes detectados;
- coste marginal de esa respuesta en USD;
- indicación `real` o `estimado` del coste;
- nota de que no incluye la preparación previa del corpus;
- aviso visible de que se trata de una comparación experimental cuando hay dos
  estrategias activas.

Cuando hay dos estrategias activas, al final se ofrece un único voto: A, B,
empate o ambas insuficientes, con un motivo cerrado y sin texto libre. El backend
acepta un voto por `request_id` y no permite sobrescribirlo. Esta preferencia
sirve para UX y evaluación; nunca convierte por sí sola una respuesta en
jurídicamente correcta.

No se permite:

- intercalar párrafos de ambas estrategias;
- compartir una lista de fuentes común;
- presentar una síntesis automática de las dos;
- declarar una estrategia ganadora dentro de la respuesta;
- ocultar que una estrategia falló o no encontró cobertura;
- sustituir automáticamente una respuesta fallida por la de la otra.

Si A falla, B se sigue mostrando cuando está activa. Si B falla, A permanece
disponible cuando está activa y su error se muestra de forma aislada. El cierre
global ocurre cuando todos los bloques activos alcanzan un estado terminal.

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
`strategy`. El frontend debe persistir una o dos respuestas hermanas activas
asociadas al mismo mensaje del usuario, no concatenarlas como si fueran una sola.
`answer_done` incluye un objeto de coste y, cuando una estrategia termina con
`status=error`, un `failure_code` seguro para que la interfaz pueda mostrar el
tipo de fallo sin exponer el mensaje bruto del proveedor:

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

Los códigos admitidos son `timeout`, `exception`, `strategy_contract`,
`citation_verification` y `evidence_validation`. La respuesta fallida conserva
su coste y sus límites, mientras las otras estrategias de la comparación siguen
siendo utilizables.

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
- La reserva de presupuesto incluye el coste máximo de las estrategias activas antes de iniciar
  la primera llamada facturable.
- El rate limit cuenta una pregunta del usuario, aunque internamente produzca una
  o dos respuestas.

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
pregunta y ambas respuestas con citas y costes para comparar calidad. También
conserva versión del experimento, commit desplegado, store, versiones de prompt,
filtro aplicado, IDs recuperados, citas verificadas, claims de A y diagnóstico
acotado. Los logs de Netlify no son la fuente única del análisis: si una línea se
pierde o queda vacía, el ledger privado es la fuente de verdad por petición.

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

La batería real más reciente y su valoración provisional están en
[`CHAT_AB_QUALITY_ITERATION_2026-08-03.md`](../experiments/CHAT_AB_QUALITY_ITERATION_2026-08-03.md).

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

## Plan de opción C: investigación agentiva

**Estado de decisión:** arquitectura de piloto acordada e implementación técnica
desplegada bajo bandera controlada; todavía no está evaluada, presupuestada ni
autorizada para tráfico jurídico general. No cambia el contrato A/B vigente.

La fundación C0/C1 ya está implementada: contratos ejecutables para job, límites,
progreso, salida, claims y evidencias, más un builder/verificador de snapshots
ZIP deterministas. El bundle v1 está transferido y validado en el VPS de
Alfredo, y el worker autenticado ya supera un smoke E2E histórico. El bundle
`rollout-106/2`, solo JSON y con herramientas acotadas, está validado localmente
pero todavía requiere instalación y smoke E2E. Siguen pendientes la muestra de
calidad C2 y la decisión de promoción C3/C6.

C será una investigación de mayor profundidad en la que un agente pueda iterar
sobre el corpus: formular búsquedas, leer unidades v3, abrir páginas verbatim,
ampliar o descartar candidatos, contrastar varias resoluciones y verificar si la
evidencia sostiene cada afirmación antes de responder. El perfil v2 mantiene
Codex como orquestador, pero sustituye la exploración de archivos por tres
herramientas jurídicas locales: buscar en el índice, leer un caso estructurado
y leer una página verbatim. No expone shell ni acceso general al repositorio.

El host previsto es el VPS privado de Alfredo, pero no se clonará allí el
repositorio completo. Cada ejecución recibirá un bundle inmutable y versionado
con manifiesto y hashes que contendrá únicamente casos v3, verbatim e índices
JSON permitidos. Quedan fuera PDF y Markdown duplicados, `.env`, credenciales, configuración de
despliegue, historial Git, frontend, scripts y cualquier otro repositorio.

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

El worker es asíncrono, autenticado, cancelable y limitado por tiempo,
herramientas, documentos, páginas y coste. El perfil v2 vive dentro del
contenedor Codex endurecido, con filesystem de solo lectura y directorio
temporal efímero. El agente no recibe ninguna herramienta de red; el proceso
padre conserva únicamente el egress HTTPS necesario para llamar al proveedor.
Prompt, MCP y verificador pertenecen al perfil, no al supervisor de Alfredo.

### Secuencia de ejecución

1. **C0 — contrato y amenazas:** fijar job, resultado, estados objetivos,
   retención, autenticación, cancelación y presupuestos.
2. **C1 — bundle:** exportar el corpus permitido desde una versión congelada y
   validar manifiesto, hashes, tamaño y ausencia de secretos.
3. **C2 — piloto:** ejecutar preguntas difíciles separadas del holdout A/B en un
   contenedor o microVM con usuario sin privilegios. Codex CLI/SDK puede servir
   como explorador controlado en modo solo lectura, ejecución no interactiva y
   JSON Schema; no es aún el runtime jurídico definitivo. La muestra congelada
   `c2-2026-08-03` se valida por hashes y el target `make
   deep-research-pilot-run` queda como lanzamiento explícito, nunca automático.
   El runner local usa `bwrap` como frontera externa de filesystem. En Alfredo,
   el contenedor Docker endurecido es la frontera efectiva: Codex solo ve el
   bundle y schema read-only, no ve credenciales, repo ni configuración, y el
   egress HTTPS del proveedor queda disponible para completar la ejecución.
   El smoke E2E ya pasó; la muestra de calidad C2 sigue pendiente.
4. **C3 — evaluación:** no ejecutar antes de cerrar el baseline jurídico ciego
   A/B. Mantener constantes corpus, fecha, ausencia de internet, contrato,
   presupuesto, modelo, herramientas e instrucciones; medir utilidad, cobertura,
   claridad, latencia, coste y cancelaciones.
5. **C4 — worker acotado:** implementado en el perfil v2 con
   `search_corpus`, `read_case` y `read_verbatim_page`; las citas pasan después
   por un verificador determinista fuera del modelo pero dentro del mismo
   runtime aislado. El texto visible se recompone solo desde claims verificados.
6. **C5/C6 — UX y promoción:** la UX bajo demanda, los estados objetivos y el
   bloque independiente están implementados y probados como piloto. Promover a
   tráfico real solo tras revisar autenticación, retención, tratamiento,
   observabilidad, rollback y presupuesto; esa decisión C6 sigue pendiente.

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
  verbatim, casos e índices JSON permitidos;
- excluir `.env`, credenciales, configuración de despliegue, historial Git y
  cualquier otro repositorio;
- deshabilitar todas las herramientas de red y la escritura del agente, salvo
  un directorio temporal desechable; el cliente conserva solo el transporte al
  proveedor del modelo;
- tratar todo texto recuperado como datos, nunca como instrucciones;
- ofrecer únicamente las herramientas acotadas `search_corpus`, `read_case` y
  `read_verbatim_page`;
- fijar límites de tiempo, turnos, llamadas de herramienta, documentos, páginas
  y coste antes de iniciar la ejecución;
- exigir JSON Schema con estado, respuesta, límites, afirmaciones y evidencias;
- resolver citas contra `raw_page_text` mediante código determinista y retirar
  cualquier afirmación sustantiva sin apoyo válido;
- no persistir ni mostrar cadena de pensamiento. La traza operativa conserva
  solo nombre de servidor/herramienta, estado, métricas y códigos de fallo
  seguros; no conserva argumentos, preguntas, páginas ni citas en el audit.

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
