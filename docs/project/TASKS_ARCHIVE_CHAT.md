# Histórico cerrado — backend y comparador A/B del chat

Archivo de las entradas **ya completadas** del bloque «Sustituir el motor `stub`
del chat por un backend real Netlify-only» de
[`TASKS.md`](TASKS.md), separadas el 12 de agosto de 2026 porque ocupaban ~190
líneas de backlog activo y hacían ilegible lo que sigue abierto.

**No es una lista de tareas.** Nada de lo que hay aquí está pendiente. Se
conserva íntegro —y no se borra— porque estas entradas son el único sitio donde
está escrito *por qué* se decidió lo que hoy rige: que Netlify Blobs no da
compare-and-swap bajo concurrencia, que la Function no usa `@sentry/node`, que
el recorrido Edge → FastAPI se conserva sin desplegarse, o qué midió cada gate.

Lo que sigue abierto de ese bloque —F0.3 y su revisión jurídica ciega, la fase 2
de evaluación, y el piloto de la opción C— permanece en `TASKS.md`.

Cada sección conserva la jerarquía relativa que tenía en el backlog, sin la
sangría del bloque padre: el texto es literal, solo se movió de fichero.

## F0.2 — redacción comparable y banco corto

- [x] **F0.2 — redacción comparable y banco corto.** A redacta sobre unidades
  estructuradas con IDs de evidencia; B usa File Search sobre PDF. Se
  ejecutaron ocho preguntas con el mismo modelo, se bloquearon respuestas sin
  citas verificables y se midieron coste y latencia. El banco de 40 y 3.6
  quedan aplazados hasta fijar una rúbrica neutral y revisar los gaps:
  [`CHAT_STRATEGY_F02_RESULTS.md`](../experiments/CHAT_STRATEGY_F02_RESULTS.md).

## Compilador post-revelado y separación corpus/inferencia

- [x] Preparar el compilador post-revelado con confirmación explícita,
  validación de identidad y resultados JSON/Markdown. No ejecutarlo hasta
  cerrar y versionar el formulario jurídico.
- [x] Separar corpus e inferencia: solo la estrategia A del chat reutiliza
  el singleton de `gateway_setup` con `UsageSink` y `AlertSink`; el workflow
  Python + agente no importa el gateway. B conserva File Search fuera del
  paquete. Se retiraron el analizador LLM y `POST /analizar`.
  - [x] Instalar el gateway desde PyPI con `>=0.8.0` y sin techo. La `0.7.0`
    normaliza el esquema estricto de OpenAI y declara
    `supports_temperature`, así que se retiraron los dos parches locales
    que suplían ambas cosas, y con ellos la tabla de enrutado heredada
    del analizador borrado. La `0.8.0` hace que `Execution.model_used`
    respete el id del proveedor; verificado que Luna sigue reportando el
    suyo y que el importe llega `ACTUAL` con su versión de tarifas.
  - [x] Limpiar referencias operativas residuales a `src/model_pricing.py`,
    ya borrado, en documentación y configuración de imports.
  - [x] Medir el esfuerzo de razonamiento sobre la evidencia recuperada:
    `max` tardaba 81-96 s y costaba $0.0113-$0.0128 por respuesta, frente a
    16-30 s y $0.0038-$0.0060 con `high`, entre tres y cuatro veces menos
    tiempo y dinero. La política queda en `high`. Falta comparar la
    **calidad** de ambos con la rúbrica congelada; hasta entonces la
    elección se justifica por coste y latencia, no por equivalencia
    demostrada.

## Fases 0, 0b y 1 — plataforma, cuotas e implementación tras el stub

- [x] **Fase 0 — spike de plataforma (gate).** Ejecutado el 2026-07-29 contra un
  Deploy Preview. Cuatro de cinco criterios pasan y **la decisión de runtime queda
  confirmada**: p95 de CPU 15,3 ms, streaming de 19,87 s, cabeceras en 0,30 s y los
  tres paquetes cargan en Deno. Mediciones en
  [`docs/operations/NETLIFY_EDGE.md`](../operations/NETLIFY_EDGE.md).
- [x] **Fase 0b — decidir el mecanismo de cuotas y presupuesto.** El
  quinto criterio falló: `onlyIfMatch` de Netlify Blobs **no da compare-and-swap**
  bajo concurrencia. Cinco peticiones simultáneas dejaron un contador de cinco
  incrementos en dos, y todas creyeron haber escrito. Se eligió la opción del
  diseño con atomicidad real: Postgres.

  > **Decisión actualizada 2026-08-01:** no se mantiene un presupuesto monetario
  > global ni una reserva por petición. Supabase/Postgres conserva un ledger
  > privado de consultas, coste real y estado mediante `create_chat_request`,
  > `complete_chat_request` y `fail_chat_request`; si Supabase falla, el endpoint
  > falla cerrado. El navegador aplica `VITE_CHAT_SESSION_MESSAGE_LIMIT=10` como
  > límite blando por ventana móvil de 24 horas y Netlify mantiene cinco
  > peticiones por IP y minuto.
  >
  > Evidencia histórica: lee en este orden la sección 5 de
  > [`docs/operations/NETLIFY_EDGE.md`](../operations/NETLIFY_EDGE.md) (la evidencia del
  > fallo y la alternativa medida) y la sección 4 del diseño (las tres opciones con
  > sus contrapartidas). La decisión prioriza un ledger privado y una protección
  > de abuso configurable, sin convertir el coste observado en una cuota de
  > producto.
  >
  > El límite fuerte por usuario queda aplazado hasta que existan cuentas y una
  > identidad estable; el límite de navegador no se presenta como garantía
  > antifraude ni como control económico.
  >
  > El trabajo vive en la rama `spike/chat-edge-platform`, **sin push**. El código
  > del spike se borró a propósito; `NETLIFY_EDGE.md` explica cómo reconstruirlo si
  > hace falta volver a medir.
- [x] **Fase 1 — implementación detrás del stub.** La Function, sus módulos
  puros, ledger privado, límite de sesión y adaptadores están implementados con
  TDD. Producción sigue simulada.

  > **La fuente del chat ya está decidida e implementada tanto en el comparador
  > local como en la Function cerrada.** Debe ser
  > `residenciafiscal-case/3` con anclajes verbatim; no el JSONL ni el perfil
  > v2 directamente. El plan antiguo genera `lib/corpus.ts` desde el JSONL y
  > por eso sus tareas 3–6 y las partes del protocolo están marcadas como
  > parcialmente superadas.
  >
  > Las piezas de plataforma y varios módulos siguen siendo reutilizables. La
  > recuperación cambia de sentencias completas a cuestiones jurídicas, y las
  > tarjetas llevan hechos, valoración, resultado por cuestión y fragmentos
  > verbatim. Cada marcador debe resolverse a **sentencia + cuestión + página**.
  >
  > El diseño y la validación con 1, 5 y 106 sentencias ya están completados.
  > Las 106 permanecen como borrador interno `AGENT_REVIEWED_ONLY`; la
  > conexión técnica al chat está hecha y la aprobación jurídica humana sigue
  > pendiente.

## Fase 2 — hitos cerrados de protocolo, A/B y persistencia

- [x] Seleccionar y contestar manualmente 40 preguntas contra la muestra de
  cinco, con casos, contracasos, límites y gaps de datos:
  [`docs/experiments/CHAT_QUESTION_PILOT_5.md`](../experiments/CHAT_QUESTION_PILOT_5.md).
- [x] Convertir la referencia manual provisional de recuperación en el
  banco machine-readable
  `knowledge/jurisprudencia-v3/evaluations/chat-question-pilot-5.bank.json`.
- [x] Evolucionar el contrato de fuentes a `ChatSourceV2` con `sourceId`,
  `issueId`, `anchorId`, página, fidelidad, hash de fuente y estado de
  revisión; adaptar persistencia y UI sin perder varios anclajes de una
  misma sentencia. Los historiales v1 se conservan como fuentes legadas y
  nunca reciben trazabilidad inventada.
- [x] Implementar `chat-engine.live.ts` y la base individual del protocolo 2;
  validar en la frontera que cada evento `sources` contiene exclusivamente
  `ChatSourceV2`, sin aceptar fuentes legadas desde el backend. Tolera
  eventos y UTF-8 partidos, exige un único terminal, distingue errores HTTP
  no SSE y envía solo `role` y `content`. La extensión A/B posterior conserva
  esta compatibilidad.
- [x] Extender el protocolo 2 al modo comparativo A/B con `strategy`,
  `answer_start`, `answer_done`, coste y terminal global; adaptar
  `ChatMessage`/UI antes de conectar el selector al backend.
- [x] Implementar el prototipo `POST /chat` en FastAPI con composición
  perezosa, secreto del proxy, fuentes/coste por estrategia y logs sin
  consulta ni respuesta. Se conserva como referencia y posible runtime
  futuro; no es el target de despliegue V1.
- [x] Implementar el proxy FastAPI como Edge Function fina con rate limit y
  transmisión del stream. El prototipo original con secreto estático se
  retiró al sustituirlo la fachada firmada
  `netlify/prototypes/chat-fastapi-edge-v2.ts`.
- [x] Implementar `/api/chat` como Netlify Function TypeScript autosuficiente:
  portar solo el runtime online de A/B, sin trasladar a TypeScript el
  pipeline Python de preparación del corpus.
- [x] Ejecutar las estrategias A/B activas en paralelo con aislamiento de errores, conservar el
  orden visual A → B y cancelar todo trabajo restante antes del deadline
  global de 50–55 s.
- [x] Corregir la regresión de autoridad en B: el comodín
  `judgment_id="sts-*"` devolvía un falso vacío. El store nuevo contiene
  106/106 PDF con `authority` explícita y B filtra por igualdad exacta. El
  store anterior se conserva para rollback.
- [x] Vincular cada afirmación de A con sus citas, ampliar de forma segura
  los anclajes breves desde el verbatim y retirar claims sin respaldo
  literal suficiente. La batería real del 3 de agosto está en
  [`CHAT_AB_QUALITY_ITERATION_2026-08-03.md`](../experiments/CHAT_AB_QUALITY_ITERATION_2026-08-03.md).
- [x] Persistir versión de experimento, commit, corpus/store, prompts,
  filtros, documentos recuperados, citas verificadas, claims y diagnóstico
  acotado en Supabase. Añadir además el endpoint y RPC de voto ciego cerrado.
- [x] Aprobar una variante visual de la vista ciega y conectar el voto en la
  UI. La variante elegida muestra dos columnas en escritorio y pestañas en
  móvil solo cuando A y B están activas; con una respuesta conserva una
  columna sin controles experimentales. El voto ciego cerrado usa el
  `request_id` persistido y no se muestra hasta que ambas opciones terminan.

## Fase 2 — tests deterministas y selector seguro

- [x] Cubrir con tests deterministas la paridad de recuperación, fuentes,
  estados, modelo, tokens, coste, cancelación y respuesta parcial. El smoke
  productivo pagado del 31 de julio confirmó además A/B en paralelo y
  persistencia/reconciliación en Supabase; el prototipo Python se conserva
  únicamente como referencia de la arquitectura futura.
- [x] Cablear el selector seguro: solo `VITE_CHAT_MODE=live` activa el cliente;
  cualquier otro valor conserva el stub.

## Fase 2 — contexto multi-turn con privacidad y grounding

- [x] Diseñar e implementar contexto multi-turn con privacidad y grounding.
  El navegador sigue enviando solo la pregunta actual; el servidor reconstruye
  hasta seis turnos y 12 KiB desde el ledger, entrega a cada estrategia solo
  su propio hilo y no trata el historial como evidencia. El UUID de la URL no
  autoriza la lectura: un secreto local de 256 bits protege el hilo y la base
  solo conserva su SHA-256; las conversaciones locales anteriores empiezan un
  `ledgerId` nuevo al migrar. Las referencias explícitas se contextualizan
  incluso si contienen términos del dominio. La evaluación
  conversacional de calidad sigue perteneciendo al banco de 40 preguntas.

## Opción C — C1, bundle de investigación

- [x] **C1 — construir el bundle de investigación.** Exportar únicamente
  casos v3, verbatim e índices jurídicos JSON necesarios desde
  una versión congelada del corpus. Validar manifiesto, hashes, límites
  de tamaño y ausencia de secretos antes de copiarlo al VPS.
  - [x] Implementar `deep-research-bundle.py` y los targets
    `make deep-research-bundle` / `make deep-research-bundle-verify`.
    El builder produce ZIP determinista, no sobrescribe snapshots y el
    verificador comprueba la allowlist y todos los hashes. La instantánea
    `rollout-106/1` quedó validada localmente, transferida al VPS de
    Alfredo y validada allí; bundle y schema se montan en solo lectura.
  - [x] Construir `rollout-106/2` solo con JSON (sin copias PDF o Markdown),
    añadir el MCP allowlisted de lectura y verificar localmente el bundle.
    Instalado en Alfredo y validado E2E el 2026-08-04 con el job
    `deep-1b556373-3e2b-4deb-a160-c4b67d24226b`: salida v2, cita literal
    de SAN 1210/2023 página 8, callback enviado y mensaje de asistente
    persistido con `gpt-5.6-luna` y esfuerzo `high`.

## Opción C — C4 herramientas jurídicas y C5 experiencia bajo demanda

- [x] **C4 — sustituir el explorador por herramientas jurídicas.** El
  perfil v2 expone solo `search_corpus`, `read_case` y
  `read_verbatim_page` mediante un MCP local, sin shell, navegador,
  internet accesible al modelo ni acceso general al repositorio. Exigir
  salida estructurada con estado, respuesta, límites, afirmaciones y
  evidencias; pasar toda cita por el verificador determinista y retirar
  cualquier afirmación sin apoyo válido. El texto visible se deriva solo
  de los claims verificados. Prompt, MCP y verificador viven en el runtime
  del perfil dentro del contenedor; Alfredo solo transporta y entrega el
  resultado. No persistir ni mostrar cadena de pensamiento; conservar
  solo trazas operativas seguras.
- [x] **C5 — integrar la experiencia bajo demanda.** Desde A/B mostrar
  únicamente un botón explícito «Iniciar investigación profunda» o una
  oferta tras respuestas parciales, abstenciones o discrepancias. No
  añadir C a la comparación síncrona ni retrasar A/B. Mostrar estados de
  búsqueda/lectura/verificación y, al terminar, añadir un bloque o pestaña
  C independiente con fuentes, límites, coste y latencia; permitir votar
  A, B, C o empate sin declarar automáticamente una ganadora.

## Fase 3 — activación técnica

- [x] **Fase 3 — activación técnica.** `VITE_CHAT_MODE=live` y el backend están
  activos en Production desde el 31 de julio de 2026. El rollback es volver a
  `stub` y deshabilitar el backend. La activación técnica no cierra privacidad,
  retención ni revisión jurídica.
