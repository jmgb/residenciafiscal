# Tareas pendientes

Backlog operativo del proyecto. Las tareas SEO y de despliegue deben verificarse
contra el dominio público después de cada deploy. Los pendientes operativos
breves están en [`tasks.md`](../../tasks.md); los hitos cerrados sin subtareas
abiertas se conservan en [`TASKS_ARCHIVE.md`](TASKS_ARCHIVE.md).

> **Si retomas el backend del chat**, separa dos líneas: el experimento de
> comparación entre el corpus v3 y Gemini File Search, y la activación
> productiva. El mecanismo atómico ya está implementado y el chat está activo en
> producción desde el 31 de julio de 2026. El corpus técnico de 106 se conectó
> el 1 de agosto como `AGENT_REVIEWED_ONLY`; siguen pendientes la mejora de
> relevancia genérica y la revisión jurídica humana, que esta activación no
> sustituye.
> La fase 0 de plataforma ya está ejecutada y medida.
>
> **Decisión de runtime V1 (2026-07-31):** el chat se desplegará íntegramente en
> una Netlify Function estándar, con las estrategias A/B activas en paralelo y deadline interno
> inferior a 60 s. El recorrido Edge → FastAPI ya implementado no se borra: se
> conserva como alternativa futura si hacen falta llamadas más largas o mayor
> control operativo, pero no debe desplegarse como V1.
>
> El diseño está promocionado en
> [`docs/development/CHAT_BACKEND_DESIGN.md`](../development/CHAT_BACKEND_DESIGN.md);
> el plan de ejecución quedó como scratch local en `docs/superpowers/`, que está
> en `.gitignore` y no se versiona (regla de promoción en `CLAUDE.md`).

> **Si retomas el corpus normativo**, los dos pendientes de «Corpus normativo»
> son independientes entre sí y se pueden coger por separado. El schema v3 ya
> está congelado: añadir las normas citadas exige una extensión opcional
> compatible o una versión nueva. La tabla de convenios y el guardarraíl de la
> redescarga ya están implementados; su evidencia se conserva en el histórico.

## Prioridad alta

- [ ] **P1 — Segunda tanda de rutas de país, solo después de medir la primera.**
  Diez países con convenio ya publicado, coste de una línea cada uno: **Países
  Bajos, Bélgica, Irlanda, Luxemburgo, Malta, Chipre, Canadá, Singapur,
  Tailandia y China**. El criterio aquí es **demanda real de expatriación
  española**, no el corpus: ninguno aporta contenido único hoy, son puro long
  tail, y por eso van después y no antes.

  **El gate es medir, no el calendario.** Las 34 rutas vigentes se publicaron el
  1 de agosto de 2026 y Search Console mide desde ese mismo día (propiedad
  verificada, sitemap enviado y línea semanal en Telegram); la primera lectura
  útil de cobertura llega hacia mediados de agosto. Si a las 4-6 semanas
  no se indexan o no reciben impresiones, ampliar multiplica un formato que no
  funciona; si funcionan, esta lista ya está priorizada. Para llegar a los ~98
  convenios hace falta antes la tarea de cruzar cada página con sus sentencias:
  sin eso son 98 URLs con el mismo esqueleto.

  **Primera lectura de Search Console (12 de agosto de 2026, datos del 1 al 9;
  la API lleva tres días de retraso).** 43 impresiones, 0 clics y 18 URLs
  distintas de las 149 del sitemap. Nueve de las 34 rutas de país reciben el
  53 % de las impresiones y salen en primera página: `/alemania` 5 @9,8,
  `/emiratos-arabes-unidos` 5 @8,6, `/brasil` 4 @15,5, `/el-salvador` 2 @8,
  `/italia` 2 @5,5, `/suiza` 2 @28,5, y `/kuwait`, `/nicaragua` y `/monaco` con
  una. Las fichas de precepto aportan el 37 % restante (`lgt-a105` 6 @10,
  `lirpf-a9` 5 @18,2 y cuatro fichas de CDI con una cada una).

  - **Esto no levanta el gate**, y no debe leerse como si lo hiciera: son nueve
    días y 43 impresiones frente a las 4-6 semanas que exige esta entrada. La
    lectura de decisión cae hacia el **12-15 de septiembre de 2026**. El 0 % de
    CTR sobre 23 impresiones no es una señal de nada.
  - Lo que sí queda descartado es el riesgo que motivaba el gate: el formato se
    indexa y posiciona. Seis de las nueve rutas están por debajo del puesto 10.
  - **El contador `indexed` del sitemap no sirve para medir esto.** La API
    sigue devolviendo `submitted: 149, indexed: 0` (rastreo del 11 de agosto)
    mientras 18 URLs reciben impresiones, que es imposible sin estar indexadas.
    Medir con impresiones o con la API de inspección, nunca con ese contador.
  - 18 de 149 URLs con impresiones confirma la cola lenta de indexación: pesan
    más ahora la indexación manual y los primeros backlinks —ambas más abajo—
    que abrir rutas nuevas.

  **Actualización del 15 de noviembre de 2026:** la ventana de espera ya venció.
  La consulta de Search Console del 16 de octubre al 12 de noviembre está
  guardada en el informe operativo local `reports/gsc_checkpoint/2026-11-15.json`.
  El checkpoint de fichas CDI se cerró más abajo; decidir la segunda tanda
  requiere valorar las páginas de país de esa consulta, no seguir esperando
  septiembre ni ampliar rutas automáticamente.
- [ ] **P1 — Cruzar cada página de país con las sentencias del corpus que lo
  mencionan.** Vale más que setenta rutas nuevas: es contenido único y
  verificable —Reino Unido aparece en 115 pasajes, Suiza en 111, Argentina en
  57, Francia en 39— frente al articulado de un convenio, que está también en el
  BOE y en cualquier despacho. Requiere decidir cómo se extrae la mención
  (el nombre del país en los hechos probados no siempre es la jurisdicción en
  disputa) y respetar el invariante de literalidad.
  - La fase A ya aporta el catálogo `src/jurisdiction_catalog.json` y los
    sidecars de roles de `knowledge/jurisprudencia-v3/jurisdicciones/`.
    Reutilizar esa clave y esos roles: `judgment.countries` es texto libre y no
    sirve para cruzar datos. El enriquecimiento público sigue sujeto a los
    gates de la fase B de
    [`INTERNATIONAL_ARCHITECTURE.md`](../product/INTERNATIONAL_ARCHITECTURE.md).

## Producto y arquitectura

- [ ] **Ley Beckham (art. 93 LIRPF): integrarla como segunda vertical del corpus
  español, no como sitio clonado.** Valoración completa en
  [`LEY_BECKHAM_VALORACION.md`](../product/LEY_BECKHAM_VALORACION.md) (3 de
  agosto de 2026): frente a
  la alternativa de clonar el repositorio con dominio propio (`leybeckham.es` o
  similar), la recomendación es publicar el régimen de impatriados **dentro de
  residenciafiscal.org**, bajo la plantilla por jurisdicción ya cerrada en
  [`INTERNATIONAL_ARCHITECTURE.md`](../product/INTERNATIONAL_ARCHITECTURE.md).
  Razones: es la misma ley (LIRPF), las mismas fuentes y el mismo pipeline; es
  contenido exclusivamente español que encaja bajo `/espana` sin abrir la
  plantilla; un segundo dominio partiría de autoridad cero y dividiría el
  esfuerzo SEO en dos sitios débiles en lugar de acumular autoridad temática en
  uno; un clon duplica toda la operación (Netlify, Supabase, backups del VPS,
  Sentry ×3, UptimeRobot, CI, privacidad) y bifurca el código; y «Beckham» es
  marca de un tercero, frágil como nombre de dominio propio.

  **Tensión documental que hay que resolver primero:**
  [`TASKS_LEY_BECKHAM.md`](TASKS_LEY_BECKHAM.md) (estado: propuesta, nada
  ejecutado) planifica la opción contraria — repositorio y dominio propios. Sus
  fases de contenido (corpus normativo, fuentes DGT/TEAC, modelo de datos)
  siguen siendo válidas y se reutilizan aquí; lo que esta recomendación descarta
  son sus fases 0 (dominio/marca) y 1 (duplicación técnica). Si en el futuro se
  validara un producto separado (p. ej. English-first para «Beckham law», que la
  decisión D3 de solo-español bloquea aquí), la forma sería **mismo monorepo con
  un segundo deploy**, nunca un clon.

  - [ ] **Gate de decisión del propietario**: sección integrada vs sitio
    separado. Hasta decidirlo, no comprar dominio ni crear repositorio. Si se
    aprueba la integración, marcar `TASKS_LEY_BECKHAM.md` como sustituido en sus
    fases 0–1 y conservarlo como plan de contenido.
  - [ ] **Normativa** (pipeline existente, sin LLM): añadir a la selección de
    preceptos el art. 93 LIRPF, su desarrollo en el RIRPF (opción, renuncia,
    exclusión; arts. 113–120) y los cambios de la Ley 28/2022, verificando cada
    uno contra el BOE — no dar la lista por buena de memoria. Fichas en
    `/espana/normativa/<slug>`. Redacciones pre-2023 rotuladas por ejercicio,
    como se hace con las derogadas.
  - [ ] **Dimensionar el corpus candidato antes de comprometer rutas**: búsqueda
    CENDOJ de sentencias del régimen (art. 93, modelo 149/151, exclusiones) y
    valoración de si la interpretación viva está más en consultas vinculantes
    DGT y resoluciones TEAC. Toda fuente nueva exige condiciones de
    reutilización claras, `AVISO_LEGAL.md` e inventario, y jerarquía de
    autoridad explícita (TS > AN/TSJ > TEAC > DGT); sin eso, no entra.
  - [ ] **Landing editorial `/espana/ley-beckham`** enlazando precepto, futuro
    corpus y el hub de 183 días, con redirect 301 desde `/ley-beckham`. Slug
    siempre `ley-beckham` (ASCII, guion medio; la política de slugs prohíbe
    `ley_beckham`). «Ley Beckham» se usa como término descriptivo en títulos y
    contenido, nunca como marca del producto.
  - [ ] **Modelo de datos, solo si el corpus lo justifica**: el régimen
    introduce un `issue_type` de primera clase con criterios propios (no
    residencia previa, causa del desplazamiento, plazo de la opción, extensión a
    familiares…), tipo de fuente con fuerza vinculante y **ejercicio aplicable**
    (mezclar redacciones pre y post Ley 28/2022 es el error más caro). El schema
    v3 está congelado: exige extensión compatible o versión nueva, con el mismo
    escalonado 1 → 5 → N y los mismos gates de revisión humana que el corpus del
    art. 9.

- [x] **Sustituir el motor `stub` del chat por un backend real Netlify-only.** El
  prototipo React → Netlify Edge `/api/chat` → FastAPI → comparador A/B está
  implementado y probado, pero deja de ser el objetivo de la V1. El composition
  root está portado a una Netlify Function TypeScript, Supabase está conectado y
  una consulta productiva A/B terminó en 20,23 s por 0,004542 USD. La
  implementación anterior se conserva como opción futura para peticiones de
  más de 60 s. Runbook y corte:
  [`CHAT_DEPLOYMENT.md`](../operations/CHAT_DEPLOYMENT.md). Incluye recuperación
  con fuentes trazables que el servidor verifica y convierte en referencias
  tipadas por estrategia; el navegador nunca resuelve identificadores del LLM.
  La arquitectura vigente, el estado implementado y el orden de handoff están
  en
  [`CHAT_SYSTEM_ARCHITECTURE.md`](../jurisprudence/CHAT_SYSTEM_ARCHITECTURE.md).
  El caso de uso principal y el contrato de respuesta/recuperación están en
  [`docs/jurisprudence/CHAT_JURISPRUDENCE_USE_CASE.md`](../jurisprudence/CHAT_JURISPRUDENCE_USE_CASE.md): el
  chat ayuda al abogado a investigar casos comparables por cuestión, hechos y
  pruebas con referencias a sentencia y página; no predice su caso.
  Antes de elegir la estrategia definitiva se comparan dos respuestas
  independientes —corpus v3 estructurado y Gemini File Search sobre PDF— con
  fuentes, métricas y coste en USD separados. Contrato:
  [`docs/jurisprudence/CHAT_RETRIEVAL_STRATEGY_COMPARISON.md`](../jurisprudence/CHAT_RETRIEVAL_STRATEGY_COMPARISON.md).
  > **Histórico archivado (12 de agosto de 2026).** Las fases y subtareas ya
  > cerradas de este bloque —F0.2, fases 0, 0b, 1 y 3, los 22 hitos cerrados de
  > la fase 2 y C1/C4/C5— se movieron íntegras a
  > [`TASKS_ARCHIVE_CHAT.md`](TASKS_ARCHIVE_CHAT.md). No se borraron: documentan
  > decisiones vigentes que no están escritas en ningún otro sitio. Aquí queda
  > solo lo abierto.
  - [ ] **F0.3 — evaluación neutral y corrección de la muestra.**
    - [x] Congelar una rúbrica que separe gates binarios, utilidad e intención.
    - [x] Generar un paquete ciego saneado y versionado con las ocho parejas
      F0.2, su plantilla y la clave separada.
    - [x] Preparar un ZIP reproducible de lista permitida para el abogado,
      excluyendo clave, build y resultados previos.
    - [ ] Obtener y cerrar la revisión jurídica ciega de un abogado especialista
      en residencia fiscal, sin abrir antes la clave X/Y. Debe completar, fechar
      y conservar `CHAT_STRATEGY_F03_REVIEW_COMPLETED.md`; una revisión técnica
      o de un agente no sustituye este gate jurídico. Protocolo y validador
      mecánico preparados en
      [`CHAT_STRATEGY_F03_LEGAL_REVIEW_PROTOCOL.md`](../experiments/CHAT_STRATEGY_F03_LEGAL_REVIEW_PROTOCOL.md)
      y `make validate-chat-f03-review`.
      - [ ] Justo antes del handoff, ejecutar
        `make build-chat-f03-legal-bundle`, registrar el SHA-256 del ZIP y
        comprobar que contiene solo los cuatro Markdown permitidos y
        `MANIFEST.json`.
      - [ ] Entregar al abogado únicamente ese ZIP; no compartir el repositorio,
        la clave X/Y, el build F0.3, resultados F0.2, artefactos del proveedor
        ni código.
      - [ ] El abogado copia la plantilla como
        `CHAT_STRATEGY_F03_REVIEW_COMPLETED.md`, registra solo identificador no
        personal, cualificación, experiencia y fechas, y completa las 16
        respuestas y 8 preferencias. La comprobación de identidad queda fuera
        del repositorio.
      - [ ] El custodio ejecuta `make validate-chat-f03-review`; cualquier
        casilla, `N/A`, fallo crítico o preferencia incompleta vuelve al revisor
        antes del cierre.
      - [ ] Versionar el formulario cerrado y registrar commit y SHA-256 antes
        de abrir la clave. Si el abogado conoció X/Y antes, conservar la revisión
        solo como exploratoria y repetir el gate ciego.
      - [ ] Solo después, ejecutar `make compile-chat-f03-results
        CONFIRM_REVEAL=1 CHAT_F03_REVIEW_COMMIT=<commit>` y versionar el JSON y
        Markdown resultantes sin editar el formulario cerrado.
      - [ ] Añadir una interpretación humana separada con incidencias,
        desacuerdos y decisión —corregir datos, repetir ocho o detenerse—; el
        compilador no debe inventarla.
    - [ ] Incorporar después la cobertura verificable de ausencias esporádicas
      mediante propuesta híbrida, compilación y tests.
      - [x] Propuesta aislada con citas exactas, hashes y validador:
        [`CHAT_DATA_GAP_ABSENCES.md`](../experiments/CHAT_DATA_GAP_ABSENCES.md).
      - [ ] Después de cerrar la revisión ciega, pedir al abogado que valore la
        proposición derivada, los dos pasajes `EXACT` y el límite expreso: la
        muestra respalda la regla de cómputo, no una definición exhaustiva de
        qué ausencia es «esporádica».
      - [ ] Registrar aceptación, corrección o rechazo y motivación en un
        artefacto de revisión separado. Nunca corregir ni normalizar el texto de
        la sentencia.
      - [ ] Si se aprueba, actualizar las propuestas fuente de
        `san-1226-2021` y `san-1210-2023`; recompilar casos, perfiles e índices
        con el pipeline híbrido. No editar a mano casos o derivados generados.
      - [ ] Ejecutar `make validate-chat-absences-candidate`, los tests de
        contrato del caso v3 y una prueba de recuperación específica de
        `CRIT_AUSENCIAS_ESPORADICAS`.
      - [ ] Repetir `DAY-05` en un artefacto nuevo y comprobar que ninguna
        respuesta invierte «se computarán [...] salvo que»; no sobrescribir el
        baseline F0.2 ni la revisión jurídica cerrada.
    - [ ] Repetir las ocho con la configuración destinada al producto —A con
      Luna + `high`; B con un modelo Gemini permitido por File Search— y una
      segunda revisión ciega. Esta ejecución compara stacks completos, no
      permite atribuir las diferencias exclusivamente al recuperador. Solo si
      pasa los gates, ejecutar las 40.
  - Diseño: [`docs/development/CHAT_BACKEND_DESIGN.md`](../development/CHAT_BACKEND_DESIGN.md)
  - Plan de ejecución: `docs/superpowers/plans/2026-07-29-chat-backend.md`
    (scratch local, sin versionar)
  - [ ] **Fase 2 — evaluación.** El banco de 40 preguntas está versionado, pero
    sus etiquetas heredadas evalúan el router y no son todavía una rúbrica
    neutral para comparar respuestas A/B. Bloquean los gates binarios
    (0 identificadores inventados, 0 párrafos sin fuente, fuera de corpus,
    adversariales, presupuesto); `recall@12` se publica como línea base medida.
    El catálogo inicial de comportamiento y preguntas está en
    [`docs/jurisprudence/CHAT_USER_QUESTION_CATALOG.md`](../jurisprudence/CHAT_USER_QUESTION_CATALOG.md).
    - [ ] Mantener Luna `high` en la V1 y medir durante varios días latencia
      total, percentiles, timeouts, tokens, coste y calidad. Evaluar un esfuerzo
      menor solo después, si la evidencia muestra que falta margen bajo 60 s.
      - [x] Ejecutar un smoke local pagado con A/B realmente en paralelo: 13,552 s
        de pared, A `ACTUAL` USD 0,002491 y B `ESTIMATED` USD 0,002278. Corrigió
        `labels` incompatible con Gemini API y el truncado de Luna `high` con
        1.200 tokens. Evidencia:
        [`CHAT_NETLIFY_V1_PAID_SMOKE.md`](../experiments/CHAT_NETLIFY_V1_PAID_SMOKE.md).
    - [ ] Añadir un Deploy Preview reproducible para validar cambios futuros sin
      probar primero en producción. La V1 ya está desplegada y el smoke
      productivo terminó en 20,23 s; esta tarea es un guardarraíl para próximos
      cambios, no un bloqueo técnico de la versión vigente.
    - [ ] **Piloto controlado — opción C agentiva; promoción general pendiente.**
      C queda separada de las respuestas rápidas A/B y se activa únicamente bajo
      una bandera explícita; nunca entra en el runtime Netlify síncrono. La
      implementación técnica del worker asíncrono privado en Alfredo está
      desplegada, con job autenticado, timeout, cancelación y resultado
      reconciliable con el mismo contrato privado de retención. El piloto no
      equivale todavía a una autorización de tráfico jurídico general.
      El VPS no recibirá un clon completo del repositorio: cada ejecución usará
      un bundle inmutable y versionado del corpus permitido, con manifiesto y
      hashes, montado en solo lectura. El bundle excluirá `.env`, credenciales,
      configuración de despliegue, historial Git, frontend, scripts y cualquier
      otro repositorio.
      - [ ] **C0 — cerrar el modelo de amenazas y el contrato del piloto.**
        Definir el esquema de job/resultado, estados objetivos (búsqueda,
        lectura, verificación, completada, cancelada y error), presupuesto de
        tiempo, turnos, herramientas, documentos, páginas y coste, además de
        retención, autenticación y cancelación. Las herramientas no tendrán
        red ni escritura; si el agente necesita llamar al proveedor LLM, ese
        acceso quedará en el controlador con egress estrictamente permitido,
        nunca en el entorno de herramientas.
        - [x] Añadir contratos Pydantic ejecutables para job, límites, progreso,
          salida, claims y evidencias, sin campo de razonamiento.
      - [ ] **C2 — piloto controlado con Codex.** Ejecutar una muestra pequeña de
        preguntas difíciles, separada del holdout A/B, en un contenedor o
        microVM con usuario sin privilegios, filesystem de solo lectura, red de
        herramientas deshabilitada y directorio temporal efímero. Codex CLI/SDK
        podrá usarse aquí como explorador controlado, con sandbox `read_only`,
        ejecución no interactiva y salida JSON Schema; esto será un piloto
        interno de calidad, no el runtime jurídico definitivo.
        - [x] Congelar el piloto `c2-2026-08-03` fuera del holdout E y añadir
          preflight por hashes, jobs JSON, workspace temporal y salida JSON
          Schema. El runner local conserva `bwrap` como preflight de
          filesystem; el runtime de Alfredo usa el contenedor Docker dedicado
          como frontera externa porque el sandbox `bwrap` anidado no puede crear
          namespaces bajo la política del VPS.
        - [x] Desplegar y verificar el worker autenticado en Alfredo. El smoke
          E2E del 2026-08-03 completó un job real con el bundle `rollout-106/1`,
          callback HMAC y salida estructurada válida.
        - [ ] Ejecutar la muestra completa de preguntas difíciles y registrar
          calidad, cobertura, claridad, latencia, coste y cancelaciones; el
          smoke E2E no sustituye esa evaluación.
      - [ ] **C3 — evaluar y decidir.** Ejecutar C solo después de cerrar el
        baseline jurídico ciego A/B. Mantener constantes corpus, fecha de corte,
        ausencia de internet, contrato, presupuesto, versión de agente/modelo,
        herramientas e instrucciones. Bloquear cualquier resultado con
        identificadores inventados, autoridad incorrecta, citas no literales o
        afirmaciones sustantivas sin apoyo verificable. Medir utilidad, cobertura,
        claridad, latencia, coste y cancelaciones; promover solo una mejora
        relevante, repetible y proporcional al coste operativo.
      - [ ] **C6 — promoción controlada.** Antes de tráfico real revisar
          autenticación del worker, retención, tratamiento de datos, observabilidad,
          rollback y presupuesto. La promoción requiere decisión explícita y
          documentada; si C no compensa su coste o pierde reproducibilidad,
          permanece como diagnóstico offline o herramienta interna de evaluación.
        - [x] Implementar el recorrido detrás de `DEEP_RESEARCH_ENABLED`: botón
          explícito fuera de A/B, job firmado Netlify → Alfredo, polling de
          estados, callback reconciliable, cancelación de jobs en cola y bloque
          C independiente con fuentes, límites, coste y «Respuesta en:».
          El bloque permite valorar A, B, C, empate o ambas insuficientes mediante
          el mismo catálogo ciego. La implementación está activa bajo bandera
          de piloto; la promoción general sigue bloqueada hasta cerrar C2, C3 y C6.
        - [ ] Completar la revisión formal de promoción y decidir explícitamente
          si la bandera permanece limitada al piloto o se desactiva hasta cerrar
          los gates de calidad, presupuesto, retención, observabilidad y rollback.
      - Contrato, seguridad, UX y gates:
        [`CHAT_RETRIEVAL_STRATEGY_COMPARISON.md`](../jurisprudence/CHAT_RETRIEVAL_STRATEGY_COMPARISON.md#plan-de-opción-c-investigación-agentiva).
- [x] **Procesar técnicamente el corpus v3 de 5 a 106 sentencias.** El rollout
  autorizado se ejecutó el 1 de agosto de 2026 desde un manifiesto bloqueado por
  hashes: 106/106 documentos `BUILD_PASSED` en 11 lotes, 67 casos dentro del
  ámbito recuperable, 39 conservados como fuera de ámbito y 74 unidades de
  recuperación. El resultado es un borrador interno
  `AGENT_REVIEWED_ONLY`, no un corpus jurídicamente aprobado. Desde el 1 de
  agosto está conectado al chat con comprobación cerrada de 106 artefactos y
  rollback al deploy/store piloto. Estado, métricas y operación:
  [`docs/jurisprudence/JURISPRUDENCE_PHASE_E0.md`](../jurisprudence/JURISPRUDENCE_PHASE_E0.md).
  - [x] Diseñar `residenciafiscal-case/3` a partir del caso de uso principal y
    de los doce gaps del piloto de 40 preguntas; probarlo con 1 sentencia y
    después regenerar las 5. Roadmap canónico:
    [`docs/jurisprudence/JURISPRUDENCE_DATA_V3_ROADMAP.md`](../jurisprudence/JURISPRUDENCE_DATA_V3_ROADMAP.md).
    - [x] Documentar arquitectura, responsabilidades, rollout, gates y estrategia
      RAG.
    - [x] Escribir el contrato campo por campo
      `docs/jurisprudence/JURISPRUDENCE_CASE_SCHEMA_V3.md`.
    - [x] Implementar modelos Pydantic, JSON Schema, fixtures y tests.
    - [x] Implementar contrato, extractor crudo, JSON Schema, fixtures y tests
      de `residenciafiscal-verbatim/1`.
    - [x] Generar `residenciafiscal-verbatim/1` en JSON para `SAN 1210/2023`.
    - [x] Construir y validar el caso v3 híbrido de `SAN 1210/2023`.
    - [x] Renderizar su Markdown e índice por cuestión desde el modelo canónico.
    - [x] Validar 18 preguntas aplicables del piloto contra esa sentencia.
    - [x] Regenerar las cinco con el mismo pipeline y ejecutar las 40 preguntas.
    - [x] Comparar recuperación estructurada y léxica antes de añadir
      embeddings. Fase D decidió `NOT_REQUIRED_FOR_PILOT`; se reabre al ampliar
      el corpus o si fallan los gates.
    - [x] Preparar la fase E0 con holdout independiente, contrato de manifiesto,
      ejecución reanudable y gates, sin crear el listado de las 106.
    - [x] Crear el manifiesto real con hashes de PDF, propuesta y evaluación;
      generar los 101 borradores restantes sin reescribir citas; y ejecutar los
      11 lotes hasta obtener 106/106 builds válidos.
    - [x] Generar el corpus agregado, el informe de calidad y un banco técnico de
      117 preguntas. La línea base obtiene recall esperado de 52,14 % @5 y
      77,78 % @12; tras el ranker v2, el holdout congelado queda en 47,86 % @3,
      precisión aparente 36,11 % y recall de contraste 20,83 %, por lo que no se
      promueve este retriever al chat como estrategia definitiva. La precisión
      no es interpretable para el corpus completo: el holdout solo etiqueta 5 de
      las 106 sentencias.
    - [x] Separar desarrollo y holdout. El banco de lookup por identificador
      contiene 117 consultas y mejora de 20,51 % a 100 % top-1 y de 34,19 % a
      100 % recall @3 con BM25 y reconocimiento de `SAN/STS número/año`, sin
      ajustar contra el holdout congelado.
    - [x] Ejecutar una segunda pasada automática de los 42 casos HIGH: 0 fallos
      de literalidad, 13 análisis CDI ausentes, 36 determinaciones residenciales
      sin tipar, 6 coberturas de anclajes bajas y 5 resultados parciales o de
      retroacción. Todos conservan `NEEDS_HUMAN_REVIEW`.
    - [x] Añadir verificación reproducible en CI y política de artefactos: hashes
      de entradas y derivados, regeneración de agregados y límites de 1.000
      ficheros/50 MB.
  - [x] **Conectar de forma reversible las 106 al chat.** A usa el agregado
    completo (67 documentos recuperables y 74 unidades) con BM25 y lookup
    `SAN/STS número/año`; B usa un File Search Store con los 106 PDF. La Function
    valida que los 106 IDs tienen artefacto verbatim antes de arrancar y el store
    piloto se conserva para rollback. Esta decisión operativa no convierte el
    holdout limitado en un gate aprobado ni cambia el estado jurídico del corpus.
  - [ ] **Completar los gaps estructurales y mejorar la relevancia genérica.**
    Prioridad: tipar las 36 determinaciones residenciales y crear los 13 análisis
    CDI ausentes desde anclajes literales; después ampliar un banco de relevancia
    para consultas genéricas con anotaciones independientes. No ajustar contra
    el holdout congelado ni inferir estos campos sin apoyo literal.
  - [ ] **Obtener aprobación jurídica humana del corpus de 106.** No hay revisor
    disponible: los 1.620 elementos jurídicos siguen `AGENT_REVIEWED`, con 0
    `HUMAN_APPROVED`. La revisión automática no debe registrarse como humana.
  - [ ] Revisar el piloto `san-1071-2025`: 3 cuestiones jurídicas propuestas y **0
    aprobadas**, más 5 textos del análisis pendientes. Las decisiones se registran en
    `knowledge/annotations/san-1071-2025.yaml` con `status: approved`,
    `reviewed_by: human:<identidad>` y `reviewed_at`. Solo puede hacerlo una persona.
  - [ ] Definir la lista de responsables autorizados a aprobar, que el pipeline exige
    antes de publicar el corpus como revisado y que hoy no existe.
  - [x] Añadir la orquestación batch separada que `export_okf.py` no tiene:
    `export_okf_batch.py` usa manifiesto explícito, orden determinista,
    publicación atómica y no descubre PDFs por defecto.
  - [x] Ejecutar y revisar de forma asistida la muestra de 5 fijada en
    `sentencias/okf_muestra_5.json`. Las 17 citas heredadas ya están
    clasificadas. La aprobación jurídica humana sigue pendiente; la autorización
    posterior permitió procesar las 106 solo como `AGENT_REVIEWED_ONLY`.
  - [x] Materializar para la muestra de cinco el corpus verbatim por páginas
    definido en
    [`docs/jurisprudence/VERBATIM_CORPUS.md`](../jurisprudence/VERBATIM_CORPUS.md)
    como JSON canónico y decidir en E0 su almacenamiento para la futura
    expansión. El Markdown verbatim sigue siendo una vista humana opcional.
- [ ] **Futuro — API/MCP para agentes externos con créditos prepagados.** Vender
  la consulta del corpus y las respuestas del chat a agentes de IA de terceros:
  cuenta por organización, API keys hasheadas, ledger de créditos append-only en
  Supabase con reserva → liquidación por petición, y doble superficie REST + MCP
  remoto reutilizando los módulos de la Function del chat (la estrategia B no se
  expone). Diseño completo, fases (F1 piloto manual → F2 self-service con Stripe
  → F3 MCP público) y riesgos en
  [`AGENT_API_MCP.md`](../product/AGENT_API_MCP.md). **No arrancar antes de**:
  chat de producción estabilizado, coste medio real por respuesta medido sobre el
  ledger, y los bloqueantes legales del diseño (ampliar `/privacidad`, ToS del
  API, consulta fiscal sobre IVA de servicios electrónicos). La F1 existe para
  validar demanda barato: 1–3 clientes con clave manual y recarga contra factura.

## Corpus normativo

`normativa/es/` guarda el XML del BOE y `knowledge/normativa/es/preceptos/` los
108 preceptos publicados; `enlaces/` resuelve qué precepto cita cada sentencia.
Arquitectura, invariantes y decisiones en [`NORMATIVA.md`](../normativa/NORMATIVA.md). Léelo
antes de tocar nada: el articulado no se reescribe nunca, y hay tests que lo
comprueban párrafo a párrafo contra la fuente.

- [ ] **Recoger en el schema v3 las normas que cita la sentencia, como campo
  propio.** Es el techo del enlazado: de las 106 sentencias, **41 no citan ningún
  artículo en su registro estructurado** aunque el razonamiento las mencione en
  prosa, así que hoy solo 58 tienen precepto enlazado. El resolvedor extrae las
  citas de todos los campos de texto del JSONL; no puede sacar lo que el análisis
  no escribió.
  - Con un campo `normas_citadas[]` —igual que ya hay criterios y pruebas— la
    cobertura sube sin tocar una línea de `normativa_citas.py`.
  - Debe entrar como extensión opcional compatible del contrato congelado o en
    una versión posterior
    ([`JURISPRUDENCE_DATA_V3_ROADMAP.md`](../jurisprudence/JURISPRUDENCE_DATA_V3_ROADMAP.md)): es
    obligatorio regenerar la muestra y repetir sus gates si cambia el schema.
  - Formato mínimo útil: sigla o nombre de la norma, número de artículo y
    apartado. El resolvedor ya sabe casar «art. 9.1.b LIRPF» y el apartado no
    participa en la resolución (se publica el artículo completo).

- [ ] **Separar `sentencias/` por jurisdicción, como ya está `normativa/`.** El
  corpus normativo vive en `normativa/es/` con el código ISO 3166-1 en la ruta y
  en el frontmatter; `sentencias/` sigue plano y solo español. La asimetría fue
  deliberada —ese directorio lo estaba tocando otra línea de trabajo— pero hay
  que resolverla **antes de que entre el primer país**, no cuando ya haya PDFs de
  dos jurisdicciones mezclados en el mismo directorio.
  - Afecta a `INPUT` del Makefile, a `sentencias/readme.txt`, a
    `sentencias_CLAVE.txt`, a `okf_muestra_5.json` y a las rutas `resource` de los
    perfiles de `knowledge/jurisprudencia/`.
  - El contrato de qué necesita una jurisdicción nueva está en
    [`NORMATIVA.md`](../normativa/NORMATIVA.md#una-jurisdicción-por-directorio) y en
    [`CONTRIBUTING.md`](../../CONTRIBUTING.md#aportar-la-jurisprudencia-de-otro-país).
  - [x] Clave de jurisdicción unificada (1 de agosto de 2026): las 34 entradas de
    `frontend/src/data/countryRoutes.json` llevan `code` con el ISO 3166-1 alfa-2
    en minúscula, el mismo que usan `normativa/es/` y el campo `jurisdiccion` del
    corpus. Validado por zod y por `tests/country-routes.test.ts`, que exige
    formato y unicidad. La ruta sigue siendo un slug legible y no vale como clave.

## SEO y contenido

- [ ] **Nichos SEO adyacentes: verticales y páginas pilar candidatas** (investigación
  del 3 de agosto de 2026; el informe completo con el análisis de SERPs está en
  [`SEO_NICHOS_ADYACENTES.md`](../product/SEO_NICHOS_ADYACENTES.md)).
  Criterio: solo entran nichos contencioso-intensivos donde aplique el
  diferenciador del proyecto (corpus verificable con sentencia, página y
  extracto literal frente a guías de despachos sin fuentes), que encajen bajo
  `/espana/{normativa,sentencias,doctrina}` y refuercen el cluster de
  residencia. Sin datos de keyword tool: la demanda se juzgó por composición de
  SERPs. Secuencia recomendada:

  > Los puntos 1 y 4 los ejecuta la **fase B** del plan de arquitectura
  > internacional (más abajo), que absorbió también el enriquecimiento editorial
  > de las landings de país; aquí se conservan por el orden y el criterio, no
  > como trabajo aparte. Los puntos 2, 3 y 5 sí son verticales nuevas.

  - [ ] **1. Publicar lo ya construido**: los 6 hubs de doctrina del art. 9
    (§6.4 de
    [`INTERNATIONAL_ARCHITECTURE.md`](../product/INTERNATIONAL_ARCHITECTURE.md)).
    Mejor ratio esfuerzo/impacto; bloqueado solo por revisión humana y el gap
    de ausencias esporádicas.
  - [ ] **2. Art. 7p LIRPF (exención por trabajos en el extranjero) como
    segunda vertical de corpus.** La cara inversa del corpus actual: residentes
    que trabajan fuera. Litigiosidad altísima y viva (TS corrigiendo a la AEAT
    en directivos/administradores; denegaciones masivas → la gente busca
    sentencias), mismas fuentes ya integradas (precepto en el XML de la LIRPF
    del pipeline; corpus CENDOJ con el escalonado 1 → 5 → N). Valorar si va por
    delante de la ley Beckham: más litigio, cero riesgo de marca. Primer paso
    en ambos casos: dimensionar el corpus CENDOJ disponible antes de
    comprometer rutas.
  - [ ] **3. Cluster «salida de España»**: landing editorial del exit tax
    (art. 95 bis; mucha consulta DGT, poca sentencia aún) y ficha de la
    cuarentena fiscal (art. 8.2; casi sin competencia de calidad, el corpus ya
    toca deportistas de élite). Después, corpus del **modelo 720** (STJUE
    27-1-2022 + TS anulando sanciones; demanda estacional cada Q1).
  - [ ] **4. Ampliar las fichas de convenio con el artículo de pensiones**
    (art. 18/19 OCDE). La vía más barata: mismo XML del BOE ya descargado, sin
    fuente nueva; multiplica el contenido de las 97 fichas precepto a precepto.
  - [ ] **5. Landings puente**: certificado de residencia fiscal con el único
    ángulo que la SERP no tiene —su valor probatorio según los tribunales, tema
    recurrente en las 106—, y teletrabajo internacional (reparte hacia Beckham
    y 7p).

  **Descartados** (con motivo en el informe): modelo 210/IRNR (materia
  distinta, gestorías especializadas dominan), ISD de no residentes
  (controversia resuelta por la Ley 11/2021), dividendos extranjeros/art. 80
  (audiencia inversor retail; revisar en 2027), guías «irse a
  Andorra/Portugal/Dubái» (no verificables con nuestras fuentes; ese tráfico se
  captura desde páginas de país y el cluster de salida). Rigen las reglas
  vigentes: sin thin content, corpus antes de afirmar doctrina, revisión humana
  antes de publicar análisis y «un precepto, una URL».

- [ ] **Futuro (en unos meses, cuando exista volumen de preguntas/respuestas en
  el chat): runner diario que convierta las consultas en landings long tail.**
  Evaluar un runner o agente programado (systemd timer, como el informe semanal
  de tráfico) que cada día procese las conversaciones del día anterior y
  proponga o cree las páginas correspondientes. El objetivo es **posicionar las
  búsquedas long tail que los usuarios ya formulan al chat**: cada pregunta real
  es una keyword long tail que ninguna herramienta de terceros va a descubrir
  antes, y una landing con URL propia (`/espana/doctrina/<tema>`, punto 11 de
  [`SEO_AUDIT.md`](../product/SEO_AUDIT.md)) puede capturar esa demanda en
  Google respondiéndola con el corpus.
  - **Clasificar contra el catálogo jurídico existente, no clustering libre.**
    El corpus ya tiene taxonomía: los criterios de `src/config.py` y las
    unidades de recuperación por cuestión jurídica (el router del chat ya
    clasifica cada consulta contra ellas en producción). El runner asigna cada
    consulta a esa taxonomía, de modo que todo tema candidato tiene corpus
    detrás **por construcción** —la regla anti thin content se cumple sola— y
    la evidencia de la landing (sentencias, páginas, extractos literales) se
    ensambla reutilizando el retriever offline, sin publicar nunca texto
    generado por el LLM.
  - **Anonimato como propiedad mecánica: umbral de k-anonimato.** La consulta
    del chat es dato fiscal: nunca se publica una consulta literal ni nada que
    permita reidentificar a su autor (hechos concretos, fechas, cuantías de un
    caso particular). El límite no es solo editorial sino verificable: un tema
    solo se materializa si lo han formulado **≥k sesiones distintas** dentro de
    la ventana de retención (k por decidir; ≥3 como suelo). Un tema preguntado
    por una sola persona es un caso concreto reidentificable y, además, no
    tiene demanda que justifique una página. La agregación diaria encaja con la
    retención de 15 días declarada en `/privacidad`, que este proceso no puede
    exigir alargar.
  - **Deduplicar contra lo ya publicado antes de crear.** Muchos temas
    recurrentes ya tienen URL (la ficha del art. 9 LIRPF, las páginas de país,
    `/metodologia`). El runner mapea primero tema → URL existente y, si hay
    cobertura, propone **ampliar** esa página en lugar de crear una casi
    duplicada que canibalice el ranking.
  - **Segundo artefacto: las preguntas sin respuesta.** Las consultas donde el
    chat se abstiene o no encuentra cobertura son la señal más valiosa del
    proceso: demanda insatisfecha y gaps del corpus. No generan landing (no hay
    corpus detrás), pero salen del runner como backlog priorizado de expansión
    del corpus.
  - **Cadencia: diaria para agregar, por lotes para publicar.** La agregación
    debe ser frecuente porque las consultas caducan a los 15 días, pero la
    publicación va en lotes pequeños y espaciados (pocas páginas por semana
    como techo): decenas de páginas nuevas de golpe en un dominio joven encajan
    en el patrón de «scaled content abuse» que Google penaliza desde 2024.
    Decidir si el runner publica directamente o deja borradores como PR —el
    merge sería el gate editorial—; el gate de GSC sigue rigiendo y ninguna
    página puede afirmar revisión humana inexistente.
  - **Se puede empezar a acumular ya, sin esperar el volumen.** El ranking de
    temas no caduca aunque las consultas sí: un script quincenal mínimo que
    clasifique las consultas contra el catálogo y persista **solo contadores
    agregados por tema** haría que el runner nazca con histórico. Cautela
    previa: incluso esos contadores son ya una finalidad nueva del tratamiento
    que `/privacidad` no declara hoy; hay que declararla (con su base jurídica)
    antes de la primera ejecución, también en modo agregado.
  - Requisito previo para el runner completo: volumen real de consultas. Con el
    tráfico actual el clustering diario no tendría señal; hasta entonces bastan
    el acumulador quincenal y la selección manual de temas del punto 11 de la
    auditoría.

## Colaboración internacional

El proyecto invita a expertos de cualquier jurisdicción a aportar la jurisprudencia
de su país. Contrato y perfiles en
[`CONTRIBUTING.md`](../../CONTRIBUTING.md#aportar-la-jurisprudencia-de-otro-país);
página pública en `/colaborar`. Desde el 1 de agosto de 2026 las landings de país
**también son indexables**: publican el convenio de doble imposición con España,
que es contenido propio y verificable, así que la invitación ya no depende de una
sola URL para poder encontrarse.

- [x] **Traducir la plantilla `aportar_pais.yml` al inglés** (1 de agosto de 2026).
  La plantilla es bilingüe: los `label` llevan los dos idiomas separados por ` / `
  y las ayudas largas ponen el español primero y el inglés tras `EN — `.
  `tests/test_issue_template_pais.py` fija esa convención, los ids —incluido el
  `pais` que GitHub prerrellena— y que las tres comprobaciones previas siguen
  siendo obligatorias; sin ese gate, una edición en español deja media plantilla
  sin traducir en silencio.
  - [ ] Sigue pendiente un nivel más abajo: el schema de extracción también está
    en español, y un corpus no hispano necesita traductor jurídico antes que
    desarrollador.
- [x] **Hacer público el repositorio** (1 de agosto de 2026). `jmgb/residenciafiscal`
  es **público**; las URLs que publica la web responden `200` sin sesión,
  comprobado de forma anónima: la raíz del repo, `CONTRIBUTING.md`, `SECURITY.md`,
  `CODE_OF_CONDUCT.md`, `sentencias/AVISO_LEGAL.md`, `normativa/es/AVISO_LEGAL.md`
  y la plantilla `aportar_pais.yml`.

  **Escaneo previo de secretos** (gitleaks 8.30.0 con `--log-opts="--all
  --remotes"`: 217 commits con diff propio de los 220 alcanzables, 54 MB, más un
  barrido de entropía independiente sobre los ficheros versionados):

  - Un único secreto real en toda la historia, el `SENTRY_AUTH_TOKEN` de
    `.mcp.json` en `13dc89c`, **ya revocado** el 2026-07-29. Se publicó a
    sabiendas: purgar la historia habría cambiado todos los SHA y roto las
    referencias a `13dc89c`/`098e492` de este mismo backlog sin cerrar ningún
    riesgo, porque el token no abre nada. GitHub lo detectó como
    `sentry_personal_token` (alerta 1) y queda cerrado como `revoked`.
  - `.env` y `credentials/ga4.json` concentran 22 credenciales vivas y **nunca
    estuvieron versionados**: verificado contra los 2007 paths que han existido
    en la historia, no solo contra `.gitignore`. El único fichero sensible que
    llegó a estarlo fue `.mcp.json`.
  - El hallazgo de `generic-api-key` en `CHAT_SYSTEM_ARCHITECTURE.md` es un falso
    positivo por entropía sobre prosa española («tokens de entrada,
    salida/razonamiento»). No se añade al allowlist: silenciarlo exigiría una
    regex sobre lenguaje natural que taparía secretos reales en la misma línea.

  **Protecciones activadas al abrir**, todas gratuitas por ser público:
  `secret_scanning`, `secret_scanning_push_protection`, alertas de Dependabot y
  `dependabot_security_updates`. Push protection es la que cambia el resultado
  la próxima vez: rechaza el push **antes** de que el objeto llegue al servidor,
  mientras que `gitleaks.yml` corre después y solo avisa cuando el secreto ya
  está en GitHub y ya hay que rotarlo. `secret_scanning_validity_checks` **no se
  pudo activar**: la API acepta el `PATCH` pero el campo sigue en `disabled`,
  así que la validez de un token detectado seguirá saliendo como `unknown`.

  Quedan públicos, a propósito, tres identificadores que no son credenciales:
  `GA4_PROPERTY_ID` en [`WEEKLY_TRAFFIC_REPORT.md`](../operations/WEEKLY_TRAFFIC_REPORT.md)
  y los dos ruleset IDs de Cloudflare en
  [`CLOUDFLARE.md`](../operations/CLOUDFLARE.md), que no sirven de nada sin un
  token. Ese mismo documento describe qué reglas WAF están activas: es la única
  información de postura de seguridad que la apertura hace pública, y se mantuvo
  por su valor operativo para un colaborador.

  **La licencia no se detectaba.** GitHub clasificaba el repositorio como
  `Other` porque `LICENSE` llevaba una nota en español tras el texto MIT, así
  que un colaborador no veía licencia alguna en la barra lateral. `LICENSE`
  vuelve a ser el MIT canónico byte a byte y la salvedad pasa a
  [`NOTICE.md`](../../NOTICE.md), que además cubre `normativa/es/`: la nota
  anterior solo excluía `sentencias/`, dejando el corpus del BOE sin declarar.
- [ ] **Verificar en GitHub el prerrellenado de la issue.** `contribution.ts`
  construye `?template=aportar_pais.yml&title=…&pais=<País>`; el formato de query
  y el YAML están validados por test. Con el repositorio ya público la URL deja
  de dar `404`, pero **sigue sin comprobarse el prerrellenado en vivo**: GitHub
  redirige a `/login` a quien no tiene sesión, conservando íntegra la query
  —incluido `pais`— en el `return_to`. Falta abrirla **con sesión iniciada** y
  confirmar que el campo `pais` llega relleno al formulario.
  - [x] Comprobación anónima realizada: GitHub conserva `template`, `title` y
    `pais` íntegros en el `return_to`; queda pendiente únicamente la comprobación
    visual con una sesión iniciada.
- [ ] **Difundir `/colaborar` fuera de GitHub.** Desde que las landings de país son
  indexables, el descubrimiento ya no depende de una sola URL, pero sigue
  necesitando canales externos (colegios de abogados, asociaciones de fiscalistas,
  LinkedIn) además de `/colaborar` y `llms.txt`. El bloqueo que impedía difundir
  —el `404` del repositorio privado— ya no existe.
- [ ] **Decidir si activar GitHub Discussions.** Una propuesta de país es una
  conversación antes que una tarea; hoy todo entra como issue. Requiere activarlo
  en la web del repositorio.

## Seguridad y datos

- [x] **Cerrar la parte técnica de la persistencia productiva en Supabase.** La
  V1 guarda una pregunta y una o dos respuestas por turno. Migraciones, RLS, RPC,
  advisors, concurrencia, backup, fallos, dry-run, auditoría y una petición
  productiva están verificados. Queda la aprobación legal y algunos huecos
  operativos:
  - [x] Implementar el purgado de `chat_messages`, `chat_requests` y
    conversaciones huérfanas, con cutoff, timer, dry-run, límite por lote y
    auditoría privada. Coordinarlo con R2 sigue pendiente de la aprobación del
    plazo: borrar Supabase no borra un backup existente.
  - [x] Configurar técnicamente el plazo operativo en 15 días y activar
    `CHAT_RETENTION_PURGE_ENABLED=true` tras el dry-run. La primera ejecución
    real con `CHAT_RETENTION_DRY_RUN=false` terminó con cero candidatos y cero
    borrados.
  - [ ] Obtener y archivar la aprobación jurídica formal del plazo, base jurídica
    y texto de `/privacidad`; la activación operativa no sustituye ese requisito.
  - [x] Implementar y probar el procedimiento de supresión solicitado por el
    usuario. Sin cuentas, la identidad se verifica fuera de la base de datos,
    se exige ticket y confirmación, y el UUID visible no basta por sí solo.
  - [x] Añadir estados `failed`/`timed_out` y una RPC idempotente de fallo sin
    guardar diagnósticos brutos del proveedor. Los fallos de proveedor y del
    deadline ya quedan distinguidos de las respuestas completadas.
  - [x] Retirar la reserva monetaria global y sustituirla por un registro privado
    idempotente de consulta. `create_chat_request` reutiliza el mismo registro
    para el par `conversation_id`/`user_message_id`; `actual_microusd` queda solo
    como coste observado y ya no existe `chat_daily_budgets`.
  - [x] Aplicar un límite blando de `10` mensajes por ventana móvil de 24 horas
    en el navegador, configurable mediante `VITE_CHAT_SESSION_MESSAGE_LIMIT`.
    El rate limit server-side de cinco peticiones por IP y minuto permanece.
  - [ ] Implementar un límite fuerte por usuario autenticado cuando existan
    cuentas y una identidad estable; no convertir el almacenamiento local en
    prueba de identidad.
  - [x] Instrumentar los fallos 503 con `request_id`, `failure_code` y etapa
    (`record`, `compare`, `complete`) mediante el evento estructurado
    `chat_request_failed`, sin registrar la excepción del proveedor ni contenido
    fiscal. El contrato queda cubierto por test.
  - [x] **Elegir el canal operativo y configurar alertas** (1 de agosto de 2026).
    Se descartó el drenaje de logs de Netlify —es de plan Pro— y se separaron los
    dos canales por naturaleza: **los errores van a Sentry**, al proyecto propio
    `residencia-fiscal-chat`, y **el gasto a Telegram**, porque no es un error y
    Sentry lo mide mal. Verificado de extremo a extremo: Sentry devolvió `200` al
    envelope que produce el código y la issue aparece como
    `chat_request_failed: comparison_error (compare)`; el resumen diario leyó el
    ledger real de producción.
    - La Function **no usa `@sentry/node`**, y es deliberado: el SDK captura
      breadcrumbs de consola y contexto del runtime por defecto, y este runtime
      loguea eventos estructurados por consola. `observability.ts` construye el
      envelope con `fetch`, así que lo que sale es exactamente lo que se lee en
      `buildEnvelope`: código de fallo, etapa, `request_id` y nombre de clase del
      error saneado. Nunca la pregunta, la respuesta ni el `message` del
      proveedor, que puede traer el prompt incrustado.
    - **Dos reglas de alerta, no una.** Con el tráfico actual una alerta por tasa
      no saltaría nunca, así que además de «5 fallos en 1 h» hay otra que avisa
      del primer fallo nuevo y de las regresiones.
    - [ ] **Hacer accionables para Autofix los eventos saneados de
      `residencia-fiscal-chat` sin debilitar su privacidad.** Reproducir primero
      el descarte real `skip_missing_stacktrace_and_culprit` con un test rojo en
      `autofix-control-plane`; admitir como contexto técnico alternativo solo el
      contrato versionado del chat (`failure_code`, etapa o estrategia,
      `error_name`, `error_context` saneado y release); mantener el requisito de
      stacktrace/`culprit` para los demás proyectos; y cubrir con tests negativos
      que nunca pasan pregunta, respuesta, mensaje bruto del proveedor, body,
      cabeceras ni cookies. Cerrar con una entrega sintética extremo a extremo,
      sin datos de usuario ni llamada pagada, que llegue a invocar al agente o
      quede explícitamente en revisión humana por un motivo distinto de falta de
      contexto.
    - El gasto sale de la RPC `chat_daily_stats`, que devuelve solo recuentos,
      sumas y percentiles: el script no puede leer contenido aunque quiera.
    - [x] **Configurado en producción** (2 de agosto de 2026).
      `CHAT_SENTRY_ENABLED=true` y `CHAT_SENTRY_DSN` son variables ordinarias del
      contexto `production` y todos los scopes —la cuenta Netlify Legacy **no**
      permite scope Functions, igual que con el resto de credenciales del
      backend— y sin prefijo `VITE_`. El timer
      `residenciafiscal-daily-chat-cost-telegram` está instalado y activo, con
      una ejecución real verificada de extremo a extremo. Runbook:
      [`CHAT_OBSERVABILITY.md`](../operations/CHAT_OBSERVABILITY.md).
      - **El timer no vive en el VPS `alfredo`**, donde el backlog lo daba por
        supuesto. Su `.env` solo tiene `SUPABASE_REF` y `SUPABASE_DB_PASSWORD`
        para `pg_dump`, y el resumen necesita `SUPABASE_URL` y
        `SUPABASE_SECRET_KEY` para la RPC `chat_daily_stats`: llevarlo allí
        ampliaría la superficie de la clave de servicio a cambio de nada. Va
        como unit de usuario en la máquina de informes, junto al timer semanal
        de tráfico, que ya corría ahí. El checkout de alfredo, además, sigue
        desfasado y sin `scripts/agentic/`.
  - [ ] Cuadrar el coste `ESTIMATED` de Gemini y revisar la medición. B sale
    `ESTIMATED` cuando la Interactions API cita documentos pero devuelve cero
    tokens de documento
    (`frontend/netlify/functions/chat/file-search-strategy.ts:79`), lo que fija
    `actual_complete=false` en todos los turnos. El coste real sigue guardándose
    para reconciliarlo con el panel de Google, pero ya no afecta a una reserva ni
    a un techo diario.
  - [ ] Ejecutar al menos trimestralmente un restore real del último dump en una
    base aislada y comprobar las cuatro tablas `private`; el simulacro mensual
    vigente solo descarga, descomprime y cuenta líneas.
  - [ ] Rotar `SUPABASE_SECRET_KEY`, `OPENAI_API_KEY` y `GEMINI_API_KEY` si cambia
    el acceso al equipo o se sospecha exposición. Si Netlify pasa a Pro,
    convertirlas de variables ordinarias de todos los scopes a secretos de
    scope Functions y rotarlas durante el cambio.
- [ ] **Completar la protección operativa del endpoint live.** La V1 ya tiene
  rate limit, cierre por bandera, límite blando configurable de sesión, ledger
  privado en Supabase y, desde el 2 de agosto de 2026, los dos canales
  operativos activos: errores a Sentry y coste diario a Telegram. Falta cerrar
  el coste contable de Gemini; el límite fuerte por usuario queda condicionado a
  disponer de cuentas.
- [ ] **Requisitos legales pendientes con el chat real activo.** La última
  pregunta y el contexto acotado reconstruido por el servidor viajan a OpenAI
  para A y a Google/Gemini para B; la
  activación técnica del 31 de julio no sustituye estos requisitos.
  - [x] Aviso de que no es asesoramiento jurídico visible junto al chat tanto en
    `stub` como en `live`; el modo live no afirma que la respuesta sea simulada.
  - [ ] Publicar una política de privacidad que declare ambos proveedores, base
    jurídica, transferencias, retención efectiva y encargados del tratamiento.
    Verificar contractualmente las opciones de no conservación de cada ruta; no
    prometer `store: false` para un proveedor basándose en la configuración del
    otro.
    - [x] Publicar `/privacidad` con el flujo técnico real, minimización,
      almacenamiento local, persistencia Supabase, ambos proveedores y contacto.
    - [x] Completar con identidad legal del responsable (Intangible Land LLC,
      EIN 92-2584862, Miami FL), base jurídica por finalidad, tabla de
      encargados con su ubicación, transferencias fuera del EEE, plazos de
      conservación —15 días de chat y la retención propia de las copias—,
      derechos, AEPD y cookies. `/privacidad` es además la identificación del
      art. 10 LSSI-CE, porque no hay página de aviso legal separada.
    - [ ] Verificar y archivar los contratos de encargo con Supabase, OpenAI,
      Google, Netlify, Cloudflare, Sentry y PostHog, y la validación jurídica
      del texto publicado. La página ya declara lo que hace el sistema; falta el
      respaldo contractual y la aprobación formal.
      > Antes de difundir el chat a terceros como servicio disponible debe
      > validarse jurídicamente el texto y estar verificados los acuerdos con
      > Supabase, OpenAI y Google. No prometer un plazo hasta automatizarlo y
      > probarlo.
    - [ ] **Consentimiento previo para GA4 y PostHog.** Ambas se instalan hoy
      sin recabar consentimiento; la exclusión de `?no_analytics=1` es opt-out,
      no el consentimiento previo que exige el art. 22.2 LSSI para cookies e
      identificadores no exentos. Opciones: banner de consentimiento con la
      analítica bloqueada por defecto, o configuración sin identificadores.
      Hasta cerrarlo, la política declara la medición bajo interés legítimo, que
      es lo que ocurre de hecho, no lo que la AEPD acepta para cookies.
    - [x] **Representante en la UE (art. 27 RGPD): decidido no designarlo**
      (1 de agosto de 2026). La titularidad es estadounidense y no habrá
      representante. No es un pendiente: no volver a abrirlo como tarea ni
      publicar uno inexistente en `/privacidad`, que guarda silencio sobre el
      art. 27 sin negar la obligación. Razonamiento, riesgo asumido y reglas de
      edición en
      [`PRIVACY_AND_LEGAL.md`](../operations/PRIVACY_AND_LEGAL.md).
  - [x] Aviso visible antes del envío para no incluir datos personales o
    identificativos.
  - [x] Minimización técnica: el cliente live envía exclusivamente la última
    pregunta no vacía, no el historial local. Supabase guarda una pregunta por
    turno y sus respuestas A/B o editorial; para un seguimiento, la Function
    relee una proyección acotada de las mismas filas. No se guardan IP, user-agent
    ni diagnósticos brutos.

## Calidad y despliegue

- [ ] Añadir smoke tests de navegador para `/`, `/metodologia`, `/colaborar` y las landings
  públicas, incluyendo comprobación de redirecciones, sitemap, robots y corpus publicado.
  - **Lo determinista ya está cubierto sin navegador** (12 de agosto de 2026), que
    era el 90 % del valor y cuesta 0,3 s en CI:
    `tests/test_frontend_seo_assets.py` comprueba que las cinco rutas estáticas
    sirven su prerender con `status = 200`, `force = true` y por delante del
    fallback (`test_public_routes_serve_their_prerender_before_the_spa_fallback`,
    endurecido y verificado por mutación), que cada ruta de país tiene su regla
    (`test_country_routes_have_prerender_redirects`), que el sitemap solo lleva
    rutas canónicas y ninguna sentencia, y que la shell es `noindex`.
  - **Lo que un navegador sí añadiría y sigue pendiente**: que el HTML *servido*
    por producción —no el que genera el build— llegue con su meta `robots`, y
    que el corpus publicado responda. Hoy lo vigila UptimeRobot con dos
    monitores de palabra clave, así que esto ya no es un hueco urgente.
  - Una página de país con convenio puede ser indexable aunque no tenga corpus
    jurisprudencial propio. Verificar su estado según `countryRoutes.json`;
    una sección sin contenido suficiente debe devolver 404, conforme a
    [`COUNTRY_PAGES.md`](../product/COUNTRY_PAGES.md).

## SEO y operación

- **Enriquecer editorialmente las landings de país** → fusionada el 12 de agosto
  de 2026 en la **fase B** del plan de arquitectura internacional, más abajo, que
  es la única de las entradas que describía este trabajo con gates. Era el mismo
  contenido diferencial y verificable contado desde tres sitios distintos (aquí,
  en los nichos SEO adyacentes y en la fase B).
- [ ] **Configurar Resend para correo transaccional.** Las credenciales necesarias
  ya están disponibles en el `.env` de la raíz; reutilizar sus nombres sin leer,
  imprimir, copiar ni versionar los valores.
  - Definir primero el flujo que sustituirá o complementará los enlaces `mailto:`,
    el remitente, el destinatario operativo y el contenido estrictamente
    transaccional. Mantener marketing y newsletters fuera de este flujo.
  - Verificar un dominio o subdominio de envío y sus registros SPF, DKIM y DMARC
    antes del primer correo real.
  - Configurar las variables equivalentes en el runtime servidor de Netlify.
    `RESEND_API_KEY` y `RESEND_WEBHOOK_SECRET` nunca llevan prefijo `VITE_` ni
    pueden llegar al bundle, logs o respuestas al navegador.
  - Implementar el envío solo en servidor, con validación de entrada, clave de
    idempotencia estable, timeout y reintentos únicamente para `429`, `5xx` y
    fallos transitorios.
  - Si se habilitan eventos de entrega, verificar la firma del webhook y procesar
    de forma idempotente al menos `delivered`, `bounced` y `complained`.
  - Añadir pruebas con mocks y ejecutar un único smoke real explícito después de
    verificar dominio y destinatario.
    - [x] Los nombres de variables ya están declarados en `.env.example`
      (12 de agosto de 2026), solo los nombres y sin un solo valor, con la nota
      de que no hay flujo implementado todavía. Se añadieron en el mismo cambio
      `CLOUDFLARE_ACCOUNT_ID` y `CLOUDFLARE_API_TOKEN`, que ya se usaban a mano
      —son las que necesita la revisión del WAF, más abajo— y no estaban
      declaradas en ningún fichero versionado.
- [x] **Registrar el sitemap en Google Search Console** (1 de agosto de 2026).
  La propiedad `sc-domain:residenciafiscal.org` **no existía: se creó y
  verificó por API el mismo día**, sin pasar por la UI. La Site Verification API
  estaba deshabilitada en el proyecto de GCP que usa el skill
  `google-search-console` y su cuenta local no podía habilitarla, así que se
  activó —junto a la de Search Console— en otro proyecto de GCP del propietario,
  y la verificación la hizo la service account de ese segundo proyecto: token
  DNS, registro TXT creado por la API de Cloudflare y `webResource.insert`. Esa
  cuenta de servicio delegó después la propiedad a las cuentas personales y a la
  service account del skill, que quedó `siteOwner` y envió el sitemap. Google lo
  descargó con **0 errores y 0 avisos**. Los identificadores concretos de esos
  proyectos de GCP viven en sus repositorios privados, no aquí. Detalle
  operativo completo en
  [`SEO_AUDIT.md`](../product/SEO_AUDIT.md).
  - **No borrar el registro TXT** `google-site-verification=…` de la zona de
    Cloudflare: sostiene la verificación de la propiedad; si desaparece, la
    verificación caduca y con ella el acceso de todos los owners delegados.
  - **El recuento delataba un sitemap viejo.** Search Console registraba `5` URLs
    —justo `/espana` más las cuatro estáticas, es decir, el sitemap anterior a
    publicar las rutas de país— mientras producción servía ya 38. Había
    descargado una versión previa al deploy del día. Reenviarlo lo corrigió: 38
    URLs, `indexed: 0` por recién descargado.
  - Verificar el recuento tras cada deploy que añada rutas: un sitemap servido
    correctamente y una versión obsoleta en Google se ven igual desde fuera.
  - Para el próximo dominio, el flujo es repetible sin UI: las dos APIs siguen
    habilitadas en ese segundo proyecto y el procedimiento (token → TXT → verify →
    delegar owners → `sites.add` → `sitemaps.submit`) está documentado en la
    auditoría.
  - `GSC_SITE_URL` queda declarada en `.env.example` para que el skill
    `google-search-console` no necesite el flag `--site-url`.
  - **Complementos ya operativos** (2 de agosto de 2026): enlace GSC ↔ GA4
    activo —manual en la UI de GA4, con la cuenta administradora, que ya era
    owner delegada en GSC— y línea de Search Console en el informe semanal de
    Telegram ([`WEEKLY_TRAFFIC_REPORT.md`](../operations/WEEKLY_TRAFFIC_REPORT.md)).
    Pendiente solo Bing Webmaster Tools (importar desde GSC, manual).
- [ ] Revisar durante varios días los eventos del WAF. Ajustar la regla custom si
  los User-Agents genéricos (`curl`, `axios`, `python-requests`) bloquean monitores
  o integraciones legítimas.

### Pendientes de evaluación

- [x] Mantener visible en la barra lateral el país activo además de los tres
  iniciales, también al entrar en una subruta o navegar sin desplegar la lista
  completa (2026-11-15). Cubierto por `CountryNavigation.test.tsx`.
- [ ] Evaluar si merece la pena añadir tests de aislamiento que garanticen que cada país consulta
  únicamente su propio corpus cuando existan corpus nacionales adicionales.

## Plan de arquitectura internacional y posts de sentencias (2026-08-02)

El diseño vive en
[`INTERNATIONAL_ARCHITECTURE.md`](../product/INTERNATIONAL_ARCHITECTURE.md). Las
fases **A** (fundación de datos) y **C1** (renderer jurisprudencial en preview)
quedaron **ejecutadas y verificadas el 2 de agosto de 2026**. La fase
**C2 está aplazada sin fecha** por falta de revisor humano; ninguna otra fase
depende de ella y el gate de `HUMAN_APPROVED` no se rebaja. Lo pendiente, en el
orden recomendado:

- [ ] **Pedir indexación manual en la UI de GSC** (2026-08-03, ~15 min). Unas
  diez URLs prioritarias: `/espana/normativa`, `lirpf-a9`, las fichas de CDI
  con más demanda (Andorra, Portugal, Francia, Emiratos), `/colaborar` y dos o
  tres páginas de país. La API no permite solicitar indexación; solo la
  interfaz.
  - [ ] Intento pendiente: la sesión de navegador disponible no está autenticada
    en Search Console; no se puede solicitar indexación con la service account
    ni mediante la API de inspección. Requiere abrir la UI con una cuenta con
    permisos sobre `sc-domain:residenciafiscal.org`.
  - [x] La inspección API sí funciona y confirma para `/espana/normativa`
    `Discovered - currently not indexed`; no sustituye la solicitud manual.
- [ ] **Primeros backlinks** (continuo desde 2026-08-03). Repositorio público
  de GitHub, perfiles y comunidades de fiscalidad internacional o expats. Sin
  autoridad entrante, la cola de indexación de un dominio nuevo seguirá lenta
  con independencia de los ajustes técnicos.
- [ ] **Decisión de producto: ficha documental sin análisis** (§6.3 del
  diseño). Solo metadatos primarios y citas literales verificadas, sin
  resultados ni resúmenes del agente. Es la única vía de contenido
  jurisprudencial indexable mientras no haya revisor; exige su propia decisión
  jurídica de alcance, pero no revisión caso a caso.
  - **Fecha orientativa vencida** (era la semana del 2026-08-10; sin decidir el
    12 de agosto). No se refecha a ciegas: es una decisión del propietario y no
    depende de trabajo previo. Mientras siga abierta, el renderer jurisprudencial
    está construido y verificado (Gate C1) publicando **cero** fichas —
    `LOTES_PUBLICADOS = {}` en `src/export_public_judgments.py:45`— y la fase B
    no puede arrancar.
- [ ] **Fase B — piloto de 3 bilaterales** (tras el Gate A y tras la decisión
  §6.3; su fecha orientativa, la semana del 2026-08-10, venció sin arrancar).
  `/espana/convenios`, tres bilaterales que cubran
  convenio único, sucesión (Japón/Rumanía/China) y fuente del diario; sus
  páginas de país se convierten en hubs en el mismo lote. Ampliar por lotes
  solo si el Gate B pasa. Los componentes se implementan desde el inicio por
  jurisdicción, aunque `es` sea la única instancia con datos.
  - Absorbe **el enriquecimiento editorial de las landings de país**, que estaba
    duplicado en «SEO y operación», y es el vehículo de los puntos 1 y 4 de la
    secuencia de nichos SEO adyacentes. Los tres describían el mismo trabajo;
    esta entrada es la única de las tres con gates.
- [x] **Checkpoint GSC de las fichas de CDI**, cerrado el 2026-11-15 (fecha
  inicial: 2026-09-01). Se inspeccionaron por API las 97 URLs del artefacto
  actual: 95 vigentes y 2 históricas. Hay indexación parcial; predominan las
  fichas indexadas frente al resto y no aparece el patrón masivo de
  «Crawled – currently not indexed» que disparaba este gate. Las demás combinan
  descubrimiento pendiente, URLs desconocidas y exclusiones tras rastreo.
  **Decisión:** mantener el sitemap; esta medición no justifica una poda ni
  activa por sí sola la diferenciación masiva (§12.1 del diseño).
  La consulta de rendimiento usa la ventana final del 2026-10-16 al 2026-11-12.
  Respuestas de inspección y métricas quedan en
  `reports/gsc_checkpoint/2026-11-15.json`, ignorado por git por contener datos
  de tráfico. El estado observado es el de la API en esta fecha; no se usa el
  contador `indexed` del sitemap como medida de cobertura.
- [ ] **Opcional, sin fecha — Fase C2 (publicación con análisis).** Solo si
  aparece un revisor humano comprometido: lote pequeño y diverso,
  `HUMAN_APPROVED` por caso con identidad y fecha. No programar; no bloquea
  nada.
- [ ] **Fase D — primera normativa no española.** Activar para el país elegido
  la misma superficie `fuentes` + `normativa` + `convenios`, con fuente oficial,
  especialista y tests de aislamiento; no crear una plantilla abreviada.
- [ ] **Fase E — primera jurisprudencia no española.** Migrar antes el layout
  físico por jurisdicción y activar el mismo renderer de `sentencias` y
  `doctrina`, preservando hashes y gates de aprobación.

## Criterio de cierre SEO

- `/` redirige con `301` a `/espana`; `/espana` y `/metodologia` responden
  `200` y tienen canonical propia.
- El sitemap sólo contiene URLs públicas, canónicas y rastreables.
- `/c/` permanece fuera del índice por ser contenido de conversación dinámico.
- El WAF no bloquea Googlebot, crawlers LLM ni monitores autorizados.

## Migración del chat a Alfredo (2026-08-04) — pausada y mapeada

Estado, inventario de lo que quedó corriendo y ruta de reanudación en
[`CHAT_ALFREDO_STATE.md`](CHAT_ALFREDO_STATE.md). Contrato y gates en
[`CHAT_ALFREDO_MIGRATION_PLAN.md`](CHAT_ALFREDO_MIGRATION_PLAN.md); decisiones
en [`ADR-20260804-chat-alfredo.md`](../decisions/ADR-20260804-chat-alfredo.md).

**Producción sigue en la Netlify Function.** El runtime FastAPI está instalado
en el host de operaciones pero **cerrado**: sin credenciales, sin persistencia,
solo en loopback, y `POST /chat` responde `503`. No atiende usuarios ni gasta.

- [ ] **Materializar el banco de regresión congelado de la fase 0.** Las cuatro
  divergencias del port que destapó el smoke real aparecieron comparando
  constantes a mano; sin banco, la paridad seguirá dependiendo de eso.
- [ ] **Medir el gate F0** con `scripts/chat_stream_spike.py` contra un Deploy
  Preview. Si falla, mover la fachada a Cloudflare —no llamar al VPS directo:
  el porqué está en la sección 5 del estado.
- [ ] **Crear el rol restringido de Postgres (D2)** con `EXECUTE` solo sobre las
  tres RPC de ciclo de vida y tests de privilegios negativos. Bloquea abrir la
  persistencia y, con ella, el contenedor del host.
- [ ] **Dar de alta el monitor externo del health** (alta manual: UptimeRobot
  rechaza escrituras por API en este plan).
- [ ] **Dar de alta Sentry y Autofix Alfredo para el cuarto runtime
  `residencia-fiscal-chat-backend` al activarlo.** Antes del DSN o del canary:
  crear en Alfredo un workspace de Autofix dedicado y separado del checkout
  operativo `~/residenciafiscal`; crear el proyecto de Sentry y su regla con la
  integración `Autofix Alfredo`; añadir al registro compartido del control
  plane un override explícito `host: alfredo` que resuelva al repo y workspace
  correctos; desplegar y verificar el registro en ambos hosts; y probar una
  entrega extremo a extremo (`202` en Alfredo, job procesado allí y descarte
  `skip_wrong_host` esperado en Finanzas). Los tres proyectos actuales
  (`backend`, `frontend` y `chat`) permanecen en Autofix Finanzas mientras sus
  runtimes sigan fuera de Alfredo; no moverlos por la mera existencia del
  contenedor cerrado.
- [ ] **Actualizar `/privacidad`** en el mismo cambio que enrute al primer
  usuario real. Es prerrequisito bloqueante del canary, no limpieza posterior.
- [ ] **Decidir si se retira.** Si la migración se abandona, el paso único es
  eliminar el contenedor y su directorio de releases del host y registrar la
  decisión.
