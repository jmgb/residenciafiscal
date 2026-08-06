# Arquitectura vigente del sistema jurisprudencial conversacional

**Estado del corpus:** el rollout v3 técnico contiene 106 casos, 67 dentro del
ámbito recuperable y 74 unidades. Sigue `AGENT_REVIEWED_ONLY`; no sustituye la
revisión humana. Está conectado al chat desde el 2026-08-01 con rollback al
deploy y store piloto.
**Fecha de corte del corpus:** 2026-08-01.

Este documento es la puerta de entrada canónica para entender el sistema de
jurisprudencia conversacional. Explica qué existe, cómo se relacionan sus
capas, qué hemos aprendido y qué debe ocurrir después. Los contratos y las
mediciones detalladas permanecen en los documentos especializados enlazados.

## 1. Objetivo y no objetivo

El sistema ayuda a un abogado a investigar un supuesto de residencia fiscal:

- recupera cuestiones y casos comparables;
- explica los hechos, las pruebas, la valoración judicial y el resultado de
  cada cuestión;
- presenta casos de apoyo y de contraste;
- permite comprobar cada afirmación en la sentencia y página originales;
- pide datos o declara falta de cobertura cuando corresponde.

No determina la residencia del usuario, no predice un pleito y no sustituye la
revisión jurídica. Una respuesta del modelo es una síntesis de investigación,
no una fuente de Derecho.

El contrato de producto completo está en
[`CHAT_JURISPRUDENCE_USE_CASE.md`](CHAT_JURISPRUDENCE_USE_CASE.md).

## 2. Corpus offline y chat online

El repositorio contiene dos líneas distintas:

| Línea | Alcance actual | Resultado | Uso |
|---|---|---|---|
| Preparación del corpus | Workflow Python + agente, 106 borradores técnicos | Verbatim, casos por cuestión, anclajes e índice | Fuente verificable interna |
| Chat | Comparador A/B Netlify-only activo con las 106 | Respuestas con fuentes, coste y límites | Consulta del abogado |

Los exports JSONL/CSV/XLSX que existen son históricos y no tienen un generador
LLM activo. El rollout v3 siguió la secuencia 1 → 5 → 106 y completó los gates
técnicos. La conexión técnica y la revisión jurídica humana siguen separadas.

Tampoco deben mezclarse los árboles:

- `knowledge/jurisprudencia/` y `knowledge/jurisprudencia-muestra-5/` pertenecen
  al perfil OKF/2 legado;
- `knowledge/jurisprudencia-v3/` contiene el caso canónico, verbatim e índices
  del chat;
- `knowledge/jurisprudencia-v3/retrieval/corpus.json` conserva el agregado
  piloto de cinco para rollback y `retrieval/rollout-106.corpus.json` es el
  agregado productivo;
- `output/` contiene ejecuciones y logs locales regenerables; no es una fuente
  canónica ni se versiona.

## 3. Capas de datos y autoridad

```text
PDF original del CENDOJ
        │
        ├── extracción determinista por páginas
        │       └── verbatim canónico + hashes
        │
        └── propuesta jurídica del agente
                │
                └── compilador y gates Python
                        └── caso v3 canónico
                                ├── Markdown OKF/3
                                └── unidades de recuperación
```

| Capa | Función | Autoridad | Edición |
|---|---|---|---|
| PDF | Resolución conservada | Máxima para el texto judicial | Nunca |
| Verbatim por páginas | Representación íntegra y localizable | Derivada mecánicamente del PDF | Solo se regenera |
| Propuesta jurídica | Cuestiones, hechos, pruebas y razonamiento | Análisis derivado | Agente/persona |
| Sidecar humano | Correcciones y aprobación separadas | Decisión editorial | Persona |
| Caso v3 | Modelo canónico compilado | Fuente estructurada del chat | Nunca a mano |
| Índice/Markdown | Vistas derivadas | No añade contenido jurídico | Solo se regenera |
| Respuesta del chat | Síntesis temporal | No es autoridad | No se incorpora al corpus |

Invariante bloqueante: el texto de una sentencia puede formatearse, pero no
reescribirse, corregirse ni completarse. El matching difuso solo localiza
candidatos. Una cita publicada siempre procede de una subcadena exacta de la
página declarada.

El reparto Python/agente/persona y los gates de compilación están en
[`JURISPRUDENCE_CASE_PIPELINE.md`](JURISPRUDENCE_CASE_PIPELINE.md). El contrato
del texto íntegro está en [`VERBATIM_CORPUS.md`](VERBATIM_CORPUS.md).

## 4. Pipeline híbrido fuera de línea

El enfoque híbrido aprovecha capacidades distintas:

1. Python extrae cada página, conserva bytes y calcula hashes.
2. El agente propone la estructura jurídica y selecciona pasajes literales.
3. Python resuelve offsets, revalida cada pasaje y comprueba relaciones e IDs.
4. Una persona puede corregir el análisis derivado o aprobarlo mediante
   sidecars; nunca modifica el texto de un anclaje.
5. Python compila atómicamente el caso v3 y genera todos sus derivados.

El agente no es mejor sustituto de Python para hashes, offsets, reproducción o
validación exacta. Python tampoco sustituye el juicio necesario para separar
cuestiones, interpretar el papel de una prueba o identificar el razonamiento
decisivo. Las cinco sentencias actuales están técnicamente validadas, pero no
deben presentarse como revisadas por expertos: su estado jurídico es
`AGENT_REVIEWED`, salvo aprobación humana explícita posterior.

## 5. Arquitectura experimental por pregunta

F0.2 compara dos respuestas independientes sobre la misma muestra:

```text
pregunta del usuario
        │
        ├── A — sistema estructurado
        │     router local
        │       ├── preguntar/abstenerse → respuesta determinista, USD 0
        │       └── recuperar hasta 5 unidades
        │              └── máximo 4 fragmentos diversos por unidad
        │                     └── redactor LLM
        │                            └── IDs E<n>
        │                                   └── resolución local + gate
        │
        └── B — Gemini File Search
              File Search Store con los 106 PDF
                    └── recuperación + redactor LLM
                           └── anotaciones del proveedor
                                  └── verificación local + gate

salida experimental:
  Respuesta A + fuentes A + límites A + coste A
  Respuesta B + fuentes B + límites B + coste B
```

Reglas de comparabilidad:

- A y B reciben la misma pregunta actual y la misma instrucción jurídica base;
  el router puede terminar A sin llamada;
- el servidor reconstruye hasta seis turnos y 12 KiB desde el ledger. A recibe
  solo sus respuestas anteriores y B solo las suyas; las preguntas del usuario
  y los turnos editoriales son comunes, estos últimos marcados como ajenos;
- la lectura requiere un secreto aleatorio de posesión además del UUID visible;
  Supabase guarda su SHA-256 y nunca el secreto en claro;
- el historial ayuda a interpretar y recuperar, pero nunca cuenta como evidencia
  de la respuesta actual;
- los modelos son deliberadamente distintos en la configuración vigente: A
  usa Luna + `high` y B uno de los modelos Gemini permitidos por File Search;
  esta prueba compara stacks de producto completos y no aísla el efecto del
  recuperador. El baseline F0.2 con el mismo modelo en ambas rutas se conserva
  como evidencia histórica controlada;
- no comparten el contexto recuperado;
- A usa IDs opacos `E<n>`; B obtiene fuentes de las anotaciones del proveedor;
- ninguna recibe candidatos, puntuaciones, fuentes ni prosa de la otra;
- no existe fallback cruzado;
- B puede repetir una sola vez con el mismo modelo y store si su primera
  respuesta sustantiva carece de citas verificables; el coste suma ambos
  intentos y la señal de cancelación sigue siendo única;
- una respuesta sustantiva sin fuentes verificables se retira como `error`;
- un `error` público conserva estado y coste, pero no el texto bruto de la
  excepción del proveedor;
- el coste incurrido se conserva incluso cuando el gate bloquea la prosa.

La misma comparación sigue disponible por CLI y el prototipo conserva FastAPI,
un proxy fino de Netlify Edge y el frontend como referencia. Producción usa ya
la **V1 Netlify-only**: una Function TypeScript autosuficiente ejecuta las
estrategias A/B activas en paralelo, conserva errores, fuentes y costes separados
y los presenta en orden estable A → B. La Function cancela antes de alcanzar los 60 s del runtime y
mantiene Luna con esfuerzo `high`. Latencia, percentiles, timeouts, tokens,
coste y calidad deben decidir cualquier cambio posterior de esfuerzo o modelo.

### 5.1. Opción C: investigación agentiva en piloto controlado

La implementación técnica de esta tercera estrategia está desplegada bajo una
bandera explícita, pero **no está autorizada para promoción jurídica general**.
C permitiría que un agente planificase búsquedas sucesivas,
leyese datos estructurados y páginas verbatim, contrastase resoluciones y
revisase sus propios candidatos antes de redactar. Su finalidad sería medir el
techo de calidad de una investigación con más tiempo y herramientas, y actuar
eventualmente como rescate bajo demanda cuando A y B discrepen o no encuentren
cobertura suficiente.

C no sería una variante aislada del recuperador: compararía un stack completo
—modelo, planificación, herramientas y presupuesto—. Tampoco debe ejecutarse
dentro de la Function síncrona actual ni recibir acceso general al repositorio.
El piloto usa un worker asíncrono, entorno efímero, corpus montado en solo
lectura y el mismo gate determinista de citas que A y B. El contenedor Docker de
Alfredo es la frontera efectiva; conserva únicamente el egress HTTPS necesario
para el proveedor autenticado de Codex. La sustitución por herramientas
jurídicas acotadas y la separación estricta del egress siguen siendo objetivos
de la fase C4, no afirmaciones del runtime actual. La salida permanece separada
como «Investigación profunda» y nunca reemplaza silenciosamente otra respuesta.

Pros, contras, límites operativos, UX y gates de promoción:
[`CHAT_RETRIEVAL_STRATEGY_COMPARISON.md`](CHAT_RETRIEVAL_STRATEGY_COMPARISON.md#plan-de-opción-c-investigación-agentiva).

El prototipo FastAPI no se elimina. Se conserva como arquitectura futura más
robusta si el producto acaba necesitando llamadas de más de 60 s, reintentos
largos, almacenamiento persistente o mayor control del proceso. El contrato
completo, comandos, privacidad y protocolo previsto están en
[`CHAT_RETRIEVAL_STRATEGY_COMPARISON.md`](CHAT_RETRIEVAL_STRATEGY_COMPARISON.md).
El runbook de despliegue está en
[`CHAT_DEPLOYMENT.md`](../operations/CHAT_DEPLOYMENT.md).

### Componentes de código

| Responsabilidad | Módulo |
|---|---|
| Contratos de respuesta y coste | `src/chat_answer_contract.py`, `src/chat_strategy_models.py` |
| Instrucción jurídica compartida | `src/chat_answer_prompt.py` |
| Router y recuperación estructurada | `src/jurisprudence_phase_d_retrieval.py` |
| Contexto compacto y fuentes `E<n>` | `src/structured_evidence_context.py` |
| Estrategia A | `src/current_structured_strategy.py` |
| Puerto del redactor A | `src/structured_answer_writer.py` |
| Redactor A sobre el gateway compartido | `src/gateway_chat_writer.py`, `src/gateway_setup.py` |
| Estrategia B y verificación de citas | `src/gemini_file_search_answer.py` |
| Store y gateway de B | `src/gemini_file_search_store.py`, `src/google_genai_file_search.py` |
| Aislamiento, persistencia y logs | `src/chat_strategy_comparison.py`, `src/chat_strategy_logging.py` |
| CLI experimental | `src/gemini_file_search_cli.py` |
| Paquete ciego F0.3 | `src/chat_blind_review.py` |
| Contrato y validación de fuentes v2 | `frontend/src/types/chat.ts`, `frontend/src/lib/chat-source.ts` |
| Persistencia y presentación de fuentes | `frontend/src/stores/useConversations.ts`, `frontend/src/components/chat/ChatSources.tsx` |
| Endpoint y runtime HTTP cerrados por defecto | `src/api/chat.py`, `src/api/chat_runtime.py` |
| Runtime V1 Netlify-only | `frontend/netlify/functions/chat/`; ejecuta A/B en paralelo, aísla sus hilos y falla cerrado |
| Turnos editoriales | `frontend/netlify/functions/chat-editorial.ts`, `frontend/src/data/editorialChatAnswers.json` |
| Mensajes, historial y costes V1 | `supabase-chat-store.ts`, `supabase/migrations/` |
| Proxy FastAPI conservado | `frontend/netlify/prototypes/chat-fastapi-edge-v2.ts` |
| Parser SSE comparativo y transporte live | `frontend/src/lib/chat-sse-protocol.ts`, `frontend/src/lib/chat-engine.live.ts` |
| UI y persistencia de una o dos respuestas | `frontend/src/components/chat/ChatComparisonAnswers.tsx`, `frontend/src/stores/useConversations.ts` |

A ya usa el paquete común sin cambiar el dominio, la selección de evidencias,
el gate de grounding ni los contratos de coste. B conserva su integración
directa con Gemini porque File Search requiere tools, ficheros e indexación que
el paquete excluye por diseño.

## 6. Coste y observabilidad

Cada estrategia informa por separado:

- modelo usado;
- tokens de entrada, salida/razonamiento y documentos recuperados;
- latencia total;
- coste marginal en USD;
- medición `ACTUAL` o `ESTIMATED`;
- fuentes verificadas, límites y estado.

El coste marginal no incluye preparar los casos v3 ni indexar el File Search
Store. Si Gemini omite los tokens de modalidad `document`, el coste de B es un
límite inferior y debe marcarse `ESTIMATED`. El log operativo evita contenido;
la persistencia privada de Supabase correlaciona por `request_id` la pregunta y
las respuestas A/B con sus citas y costes para evaluar el producto.

El recibo local del store y los artefactos de cada ejecución viven en
`output/file-search/`, ignorado por Git. Un clon nuevo no debe asumir que ese
estado local existe aunque las mediciones estén versionadas.

F0.3 debe generar a partir de esos artefactos un paquete ciego saneado y
versionado. Debe conservar el contenido necesario para revisión, pero retirar
modelo, estrategia, orden original e identificadores del proveedor. Así la
evaluación humana persistirá sin convertir `output/` en una fuente canónica ni
obligar a repetir llamadas de pago.

Ese paquete ya se genera sin LLM mediante:

```bash
make build-chat-f03-review
make build-chat-f03-legal-bundle
```

El primer comando valida los hashes de rúbrica, banco y ocho artefactos; produce
JSON, Markdown, plantilla y clave separados. El segundo crea el único ZIP que
debe recibir el revisor: cuatro Markdown permitidos y un manifiesto de hashes,
sin clave X/Y ni resultados previos. La plantilla debe copiarse antes de
rellenarla para que una regeneración no sobrescriba una revisión jurídica. El
gate debe ejecutarlo un abogado especialista conforme al
[`protocolo de revisión jurídica ciega`](../experiments/CHAT_STRATEGY_F03_LEGAL_REVIEW_PROTOCOL.md).
Antes del revelado, la completitud mecánica del formulario se comprueba sin LLM
mediante:

```bash
make validate-chat-f03-review
```

Una vez cerrado y versionado el formulario, el revelado se compila sin
sobrescribirlo:

```bash
make compile-chat-f03-results \
  CONFIRM_REVEAL=1 \
  CHAT_F03_REVIEW_COMMIT=<commit-del-formulario>
```

El gap `DAY-05` se ha preparado por separado en
[`CHAT_DATA_GAP_ABSENCES.md`](../experiments/CHAT_DATA_GAP_ABSENCES.md). Sus
citas exactas y hashes validan, pero la propuesta permanece
`PROPOSED_NOT_APPLIED`: no modifica ni alimenta el corpus hasta la revisión
jurídica humana.

## 7. Estado comprobado

- El corpus v3 contiene 106 casos, 67 documentos dentro del ámbito y 74 unidades
  recuperables. Sus 1.620 elementos jurídicos están `AGENT_REVIEWED`; ninguno
  está `HUMAN_APPROVED`.
- El banco de 40 preguntas ya sirvió para medir recuperación y conducta del
  router. Esa medición es `RETRIEVAL_ONLY`; no equivale a evaluar la calidad de
  dos respuestas redactadas.
- El holdout E obtiene 75 % de conducta y permanece
  `OBSERVE_ONLY_NO_TUNING`.
- F0.2 ejecutó ocho comparaciones reales con
  `gemini-3.5-flash-lite`.
- F0.3 congeló una rúbrica neutral y materializó las ocho parejas como X/Y con
  orden equilibrado, sin modelo, coste, estrategia ni metadatos del proveedor.
- Existe un ZIP reproducible y de lista permitida para entregar la revisión sin
  exponer accidentalmente la clave.
- El compilador post-revelado está listo y falla cerrado; no hay resultados
  reales porque todavía no existe un formulario jurídico cerrado.
- El gap de ausencias esporádicas está documentado y validado contra dos pasajes
  literales, pero deliberadamente no aplicado al corpus.
- `ChatSourceV2` ya conserva cuestión, anclaje, página física, página impresa,
  fidelidad, SHA-256 del PDF y revisión técnica/jurídica. La UI mantiene
  separados varios anclajes de una sentencia y el almacenamiento v2 migra las
  fuentes antiguas como legado explícito, sin inventar trazabilidad.
- El protocolo 2 valida status, `Content-Type`, versión, orden A → B, terminal,
  JSON, fuentes exactas y costes decimales; admite una o dos estrategias activas y
  tolera eventos y caracteres UTF-8
  partidos. `VITE_CHAT_MODE=live` lo selecciona explícitamente y cualquier otro
  valor mantiene el stub.
- Solo el chat comparativo A utiliza `neutral-llm-gateway` con sus sinks; el
  corpus offline no lo importa. B mantiene File Search directo por el límite
  deliberado del paquete.
- La revisión jurídica ciega de ese paquete por un abogado especialista todavía
  no se ha realizado.
- El límite vigente de cuatro fragmentos por unidad preserva el mejor match
  léxico y, cuando existen, una cita de `HOLDING`, `REASONING` y
  `BURDEN_OF_PROOF`. Sustituye al límite histórico de dos, que podía ocultar la
  valoración judicial tras una alegación con mayor coincidencia textual.
- Dos respuestas sustantivas de B sin fuentes verificables demostraron que el
  gate debe fallar cerrado.
- B recuperó fuentes sobre ausencias esporádicas que el corpus estructurado no
  cubría, pero su respuesta `DAY-05` parece invertir el efecto de la excepción
  respecto del texto literal que publica. Es simultáneamente un gap de datos de
  A y un posible fallo crítico de redacción de B, pendiente del gate jurídico.
- La Function Netlify-only y la interfaz de una o dos respuestas están activas. El
  prototipo FastAPI se conserva como alternativa futura fuera del runtime V1.
- Las 106 están conectadas como borrador técnico `AGENT_REVIEWED_ONLY`. No
  existe aprobación para presentarlas como revisadas por una persona y las
  métricas del holdout no permiten declarar el recuperador como definitivo.

Las cifras, preguntas y límites exactos de F0.2 están en
[`CHAT_STRATEGY_F02_RESULTS.md`](../experiments/CHAT_STRATEGY_F02_RESULTS.md).

## 8. Aprendizajes convertidos en decisiones

1. **No inyectar todas las sentencias.** La recuperación selectiva reduce coste,
   latencia y confusión.
2. **Usar PDF para B.** Mantiene File Search independiente de la transformación
   de A. El Markdown verbatim podrá probarse como variante diagnóstica separada;
   el JSON v3 no es una entrada justa para “File Search solo”.
3. **Recuperar cuestiones, no sentencias completas.** Una resolución puede
   contener holdings distintos y una similitud global oculta las diferencias.
4. **Conservar apoyo y contraste.** El resultado no sustituye la similitud y no
   deben seleccionarse solo casos favorables.
5. **Separar redacción y grounding.** El LLM explica; la aplicación resuelve y
   verifica fuentes.
6. **Fallar cerrado sin fuentes.** Una prosa plausible no se publica como
   respuesta jurisprudencial si no puede verificarse.
7. **No confundir modelo, recuperación y datos.** El baseline con el mismo
   modelo ayudó a aislar la recuperación. La configuración implementada
   A=Luna+`high` y B=Gemini File Search mide stacks completos; sus diferencias no se
   atribuyen solo al corpus o al recuperador. Un modelo más caro tampoco
   corrige un gap de datos ni una evaluación sesgada.
8. **No confundir etiquetas del router con calidad de respuesta.** Explicar una
   regla general y pedir hechos pueden ser conductas simultáneamente útiles.
9. **Tratar A y B como complementarias hasta medirlas.** La unión con reranking
   local es futura; mezclar hoy impediría saber qué aporta cada una.
10. **No ajustar con el holdout.** Los gaps descubiertos en desarrollo pueden
    corregirse; el banco congelado solo observa generalización.

## 9. Rúbrica F0.3 congelada

La rúbrica es el contrato de evaluación fijado **antes** de repetir llamadas.
No estima posibilidades de ganar ni asigna valor jurídico a una sentencia.
Evita cambiar el criterio después de ver qué estrategia respondió.

Debe separar:

- gates binarios: fuentes verificables, cero identificadores inventados, apoyo
  para cada afirmación sustantiva, respeto del alcance y ausencia de
  predicciones;
- valoración de utilidad: corrección, relevancia, cobertura, claridad,
  contraste y reconocimiento de límites;
- intención: regla general, aplicación a un caso particular, solicitud de
  fuentes o falta real de cobertura.

Una pregunta podrá admitir más de una conducta válida. Por ejemplo, un sistema
puede explicar la regla general y, a la vez, pedir los hechos necesarios para
aplicarla. La revisión humana debe ser ciega: “Respuesta X” y “Respuesta Y”, sin
revelar cuál es A o B.

Si se usa una escala de utilidad, debe ser corta y acompañarse de comentario:

| Valor | Significado |
|---:|---|
| 0 | Incorrecta, no responde o incumple el criterio |
| 1 | Útil pero incompleta o con una limitación relevante |
| 2 | Correcta y suficiente dentro del corpus disponible |

Estas puntuaciones sirven para comparar iteraciones del experimento. No puntúan
la fuerza de una sentencia ni calculan la probabilidad de éxito del usuario.

Contrato congelado:
[`CHAT_STRATEGY_F03_RUBRIC.md`](../experiments/CHAT_STRATEGY_F03_RUBRIC.md).

## 10. Siguiente secuencia autorizada

1. **Completado:** congelar la rúbrica neutral y preparar el paquete ciego
   saneado y versionado de las ocho respuestas.
2. Entregar únicamente los materiales permitidos a un abogado especialista,
   completar la revisión jurídica ciega baseline y cerrarla antes de abrir la
   clave X/Y.
3. Someter la
   [propuesta aislada de ausencias esporádicas](../experiments/CHAT_DATA_GAP_ABSENCES.md)
   a revisión; solo después de aprobarla, incorporarla a la muestra v3 mediante
   el mismo pipeline híbrido.
4. **Completado:** cablear el paquete común en A, reutilizar una sola instancia
   con sus sinks y cubrir el composition root.
5. **Completado:** evolucionar `ChatSourceV2`, persistencia y UI; mantener las
   fuentes del stub y de historiales antiguos como legado no verificable.
6. **Completado:** implementar el parser y transporte del protocolo 2
   individual como base compatible.
7. **Completado como prototipo:** extender el protocolo, FastAPI, el proxy Edge,
   la persistencia y la UI al flujo comparativo A/B. El selector sigue en
   `stub`; este recorrido se conserva como opción futura, no como deploy V1.
8. Portar el runtime online a una Netlify Function TypeScript, ejecutar A y B
   en paralelo, fijar un deadline de 50–55 s y mantener Luna `high` mientras se
   miden varios días de tráfico controlado.
9. Repetir las ocho consultas con la configuración destinada al producto —A
   con Luna + `high`; B con un modelo Gemini permitido por File Search— y
   generar una segunda revisión ciega sin sobrescribir el baseline. Interpretar
   el resultado como comparación de stacks, no como prueba aislada del
   recuperador.
10. Si pasan los gates, ejecutar el banco de 40 como evaluación conversacional
   A/B.
11. Probar `gemini-3.6-flash` solo si queda un problema atribuible a redacción,
   no a datos, grounding o evaluación.
12. Resolver cuotas y presupuesto, desplegar la V1 Netlify-only en un entorno
   de integración y completar la revisión del corpus antes de producción.
13. Reevaluar Edge → FastAPI únicamente si la evidencia exige llamadas de más
   de 60 s o garantías operativas que la Function no pueda ofrecer.
14. Mantener revisión jurídica y promoción al chat como decisiones posteriores
    separadas del rollout técnico ya ejecutado.

## 11. Reglas de handoff para otros agentes

Antes de cambiar esta área:

1. leer este documento y
   [`CHAT_JURISPRUDENCE_USE_CASE.md`](CHAT_JURISPRUDENCE_USE_CASE.md);
2. comprobar el estado operativo en
   [`../project/TASKS.md`](../project/TASKS.md);
3. tratar las cifras experimentales como evidencia, no como contratos;
4. no editar `knowledge/jurisprudencia-v3/cases/`, sus índices ni verbatim a
   mano;
5. no usar el banco de 40 o el holdout para declarar ganadora una estrategia
   sin la rúbrica neutral;
6. no realizar llamadas reales sin los flags explícitos de coste;
7. no cambiar de modelo mediante alias ni de forma silenciosa;
8. no atribuir revisión humana por inferencia ni ocultar las métricas y el
   rollback que condicionan la conexión del corpus completo.

Si una decisión cambia, deben actualizarse en el mismo cambio este documento,
el contrato especializado afectado y `docs/project/TASKS.md`. Las mediciones se
versionan en `docs/experiments/`; los resultados locales de `output/` no
sustituyen esa evidencia.
