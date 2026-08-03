# Tareas pendientes

Backlog operativo del proyecto. Las tareas SEO y de despliegue deben verificarse
contra el dominio público después de cada deploy.

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
> una Netlify Function estándar, con A y B en paralelo y deadline interno
> inferior a 60 s. El recorrido Edge → FastAPI ya implementado no se borra: se
> conserva como alternativa futura si hacen falta llamadas más largas o mayor
> control operativo, pero no debe desplegarse como V1.
>
> El diseño está promocionado en
> [`docs/development/CHAT_BACKEND_DESIGN.md`](../development/CHAT_BACKEND_DESIGN.md);
> el plan de ejecución quedó como scratch local en `docs/superpowers/`, que está
> en `.gitignore` y no se versiona (regla de promoción en `CLAUDE.md`).

> **Si retomas el corpus normativo**, las cuatro entradas de «Corpus normativo»
> son independientes entre sí y se pueden coger por separado. El schema v3 ya
> está congelado: añadir las normas citadas exige una extensión opcional
> compatible o una versión nueva. La tarea más silenciosa sigue siendo el
> guardarraíl de la redescarga.

## Prioridad alta

- [x] **Rotar el token de Sentry filtrado en la historia de git.** El token real
  commiteado dentro de `.mcp.json` el 2026-03-19 (commits `13dc89c` y
  `098e492`) se revocó y sustituyó el 2026-07-29. La variable canónica vigente
  es `SENTRY_TOKEN`.
  - Purgar la historia **no sustituye a rotar**: un force-push no borra el objeto
    del servidor, que sigue siendo alcanzable por su SHA. El secreto histórico
    permanece documentado como revocado.
- [x] Mantener un único `.env` en la raíz: `frontend/.env` ya no existe y Vite
  carga la configuración desde el directorio raíz.
- [x] Verificar el deploy público de `https://residenciafiscal.org/`: home y recursos
  públicos responden correctamente detrás de Netlify y Cloudflare, también desde EE. UU.
- [x] Implementar la ruta pública `/metodologia` con el método, el corpus de 106
  sentencias y sus limitaciones.
- [x] Añadir `/metodologia` a `frontend/public/sitemap.xml`
  y enlazarla desde `frontend/public/llms.txt`.
- [x] **P1 — Primera ampliación de rutas de país por presencia en el corpus**
  (1 de agosto de 2026). Se añadieron cinco: **Mónaco** (`/monaco`, sin
  convenio), **Marruecos**, **Rusia**, **Emiratos Árabes Unidos** y **Kuwait**.
  Son las jurisdicciones que más aparecen en las resoluciones y no tenían ruta.
  Cada una es una entrada en `countryRoutes.json` (`name`, `code`, `path`,
  `treatyBoeId`, `title`, `description`, `sitemap`); el bloque del convenio, el
  prerenderizado, los redirects y el sitemap salen solos. Contrato en
  [`COUNTRY_PAGES.md`](../product/COUNTRY_PAGES.md).

  **Dos correcciones al criterio que estaba escrito aquí**, ambas medidas:

  1. **La saga de becarios infla el recuento por menciones.** 31 de las 106
     sentencias son el mismo pleito —becas ICEX y ausencias esporádicas— y en
     ellas el país es el destino de la beca, no la jurisdicción en disputa. Eso
     descarta Kenia, Taiwán, Irán, Túnez, Egipto, Corea del Sur, Ucrania,
     Noruega, Rumanía, Israel, China, Turquía, Arabia Saudí, Dinamarca y
     Bélgica: una sentencia cada uno, misma doctrina, sin análisis de su
     convenio. El campo fiable es `judgment.countries`, no contar el nombre del
     país en el texto.
  2. **Una ruta nueva no trae hoy ni una sentencia a la página.** El bloque «lo
     aplican N sentencias» de `TaxTreaty.tsx` sale de `normativa.json`, y solo
     cuatro preceptos de convenio tienen sentencias enlazadas: Reino Unido (4),
     Suiza (2), EE. UU. (1) y el CDI argentino de 1992 (1). Mientras 41 de las
     106 no citen ningún artículo en su registro estructurado, una página nueva
     es el articulado del convenio y nada más.

  Quedan fuera y necesitan trabajo previo, no una entrada en JSON: **Gibraltar**
  (el acuerdo fiscal de 2019 no está en `normativa/es/`), **Guinea Ecuatorial**
  (sin convenio) y **Ucrania** (solo existiría el convenio con la URSS de 1986,
  `BOE-A-1986-25055`, y aplicárselo hay que verificarlo, no deducirlo).
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
- [ ] **P1 — Cruzar cada página de país con las sentencias del corpus que lo
  mencionan.** Vale más que setenta rutas nuevas: es contenido único y
  verificable —Reino Unido aparece en 115 pasajes, Suiza en 111, Argentina en
  57, Francia en 39— frente al articulado de un convenio, que está también en el
  BOE y en cualquier despacho. Requiere decidir cómo se extrae la mención
  (el nombre del país en los hechos probados no siempre es la jurisdicción en
  disputa) y respetar el invariante de literalidad.
  - El campo que sirve es `judgment.countries`, pero **es texto libre sin
    normalizar**: conviven `JAPÓN`, `Méjico`, `Tailandia;Dinamarca` y
    `Reino Unido (CDI 1975; referido también CDI 2013)`. Normalizarlo a ISO
    3166-1 alfa-2 —la misma clave `code` que ya usa `countryRoutes.json`— es el
    primer paso, y solapa con tipar las 36 determinaciones residenciales.

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
  - [x] **F0.2 — redacción comparable y banco corto.** A redacta sobre unidades
    estructuradas con IDs de evidencia; B usa File Search sobre PDF. Se
    ejecutaron ocho preguntas con el mismo modelo, se bloquearon respuestas sin
    citas verificables y se midieron coste y latencia. El banco de 40 y 3.6
    quedan aplazados hasta fijar una rúbrica neutral y revisar los gaps:
    [`CHAT_STRATEGY_F02_RESULTS.md`](../experiments/CHAT_STRATEGY_F02_RESULTS.md).
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
    - [ ] Repetir las ocho con la configuración destinada al producto —A con
      Luna + `high`; B con un modelo Gemini permitido por File Search— y una
      segunda revisión ciega. Esta ejecución compara stacks completos, no
      permite atribuir las diferencias exclusivamente al recuperador. Solo si
      pasa los gates, ejecutar las 40.
  - Diseño: [`docs/development/CHAT_BACKEND_DESIGN.md`](../development/CHAT_BACKEND_DESIGN.md)
  - Plan de ejecución: `docs/superpowers/plans/2026-07-29-chat-backend.md`
    (scratch local, sin versionar)
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
  - [ ] **Fase 2 — evaluación.** El banco de 40 preguntas está versionado, pero
    sus etiquetas heredadas evalúan el router y no son todavía una rúbrica
    neutral para comparar respuestas A/B. Bloquean los gates binarios
    (0 identificadores inventados, 0 párrafos sin fuente, fuera de corpus,
    adversariales, presupuesto); `recall@12` se publica como línea base medida.
    El catálogo inicial de comportamiento y preguntas está en
    [`docs/jurisprudence/CHAT_USER_QUESTION_CATALOG.md`](../jurisprudence/CHAT_USER_QUESTION_CATALOG.md).
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
      transmisión del stream; se conserva fuera del camino V1 en
      `netlify/prototypes/chat-fastapi-edge.ts`.
    - [x] Implementar `/api/chat` como Netlify Function TypeScript autosuficiente:
      portar solo el runtime online de A y B, sin trasladar a TypeScript el
      pipeline Python de preparación del corpus.
    - [x] Ejecutar A y B en paralelo con aislamiento de errores, conservar el
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
    - [ ] Mantener Luna `high` en la V1 y medir durante varios días latencia
      total, percentiles, timeouts, tokens, coste y calidad. Evaluar un esfuerzo
      menor solo después, si la evidencia muestra que falta margen bajo 60 s.
      - [x] Ejecutar un smoke local pagado con A/B realmente en paralelo: 13,552 s
        de pared, A `ACTUAL` USD 0,002491 y B `ESTIMATED` USD 0,002278. Corrigió
        `labels` incompatible con Gemini API y el truncado de Luna `high` con
        1.200 tokens. Evidencia:
        [`CHAT_NETLIFY_V1_PAID_SMOKE.md`](../experiments/CHAT_NETLIFY_V1_PAID_SMOKE.md).
    - [x] Cubrir con tests deterministas la paridad de recuperación, fuentes,
      estados, modelo, tokens, coste, cancelación y respuesta parcial. El smoke
      productivo pagado del 31 de julio confirmó además A/B en paralelo y
      persistencia/reconciliación en Supabase; el prototipo Python se conserva
      únicamente como referencia de la arquitectura futura.
    - [x] Cablear el selector seguro: solo `VITE_CHAT_MODE=live` activa el cliente;
      cualquier otro valor conserva el stub.
    - [ ] Añadir un Deploy Preview reproducible para validar cambios futuros sin
      probar primero en producción. La V1 ya está desplegada y el smoke
      productivo terminó en 20,23 s; esta tarea es un guardarraíl para próximos
      cambios, no un bloqueo técnico de la versión vigente.
    - [ ] Diseñar y evaluar contexto multi-turn con privacidad y grounding. El
      contrato actual es deliberadamente single-turn: el historial se muestra
      localmente, pero solo la última pregunta autosuficiente sale del navegador.
    - [ ] **Futuro, no autorizado — plan de opción C agentiva.** C queda separada
      de las respuestas rápidas A/B y no se activa por defecto ni entra en el
      runtime Netlify síncrono. La arquitectura acordada es un worker asíncrono
      privado en el VPS de Alfredo, con job autenticado, timeout, cancelación y
      resultado reconciliable con el mismo contrato privado de retención.
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
      - [ ] **C1 — construir el bundle de investigación.** Exportar únicamente
        casos v3, verbatim, PDF permitidos e índices jurídicos necesarios desde
        una versión congelada del corpus. Validar manifiesto, hashes, límites
        de tamaño y ausencia de secretos antes de copiarlo al VPS.
        - [x] Implementar `deep-research-bundle.py` y los targets
          `make deep-research-bundle` / `make deep-research-bundle-verify`.
          El builder produce ZIP determinista, no sobrescribe snapshots y el
          verificador comprueba la allowlist y todos los hashes. La primera
          instantánea local del rollout 106 queda validada; la transferencia y
          validación en Alfredo siguen pendientes.
      - [ ] **C2 — piloto offline con Codex.** Ejecutar una muestra pequeña de
        preguntas difíciles, separada del holdout A/B, en un contenedor o
        microVM con usuario sin privilegios, filesystem de solo lectura, red de
        herramientas deshabilitada y directorio temporal efímero. Codex CLI/SDK
        podrá usarse aquí como explorador controlado, con sandbox `read_only`,
        ejecución no interactiva y salida JSON Schema; esto será un piloto
        interno de calidad, no el runtime jurídico definitivo.
      - [ ] **C3 — evaluar y decidir.** Ejecutar C solo después de cerrar el
        baseline jurídico ciego A/B. Mantener constantes corpus, fecha de corte,
        ausencia de internet, contrato, presupuesto, versión de agente/modelo,
        herramientas e instrucciones. Bloquear cualquier resultado con
        identificadores inventados, autoridad incorrecta, citas no literales o
        afirmaciones sustantivas sin apoyo verificable. Medir utilidad, cobertura,
        claridad, latencia, coste y cancelaciones; promover solo una mejora
        relevante, repetible y proporcional al coste operativo.
      - [ ] **C4 — sustituir el explorador por herramientas jurídicas.** Si el
        piloto supera los gates, implementar el worker de producto con
        herramientas estrechas (`buscar_sentencias`, `buscar_en_sentencia`,
        `leer_paginas`, `leer_unidad_v3`, `comparar_resoluciones` y
        `verificar_cita`), sin shell ni acceso general al repositorio. Exigir
        salida estructurada con estado, respuesta, límites, afirmaciones y
        evidencias; pasar toda cita por el verificador determinista y retirar
        cualquier afirmación sin apoyo válido. No persistir ni mostrar cadena
        de pensamiento; conservar solo trazas operativas seguras.
      - [ ] **C5 — integrar la experiencia bajo demanda.** Desde A/B mostrar
        únicamente un botón explícito «Iniciar investigación profunda» o una
        oferta tras respuestas parciales, abstenciones o discrepancias. No
        añadir C a la comparación síncrona ni retrasar A/B. Mostrar estados de
        búsqueda/lectura/verificación y, al terminar, añadir un bloque o pestaña
        C independiente con fuentes, límites, coste y latencia; permitir votar
        A, B, C o empate sin declarar automáticamente una ganadora.
      - [ ] **C6 — promoción controlada.** Antes de tráfico real revisar
        autenticación del worker, retención, tratamiento de datos, observabilidad,
        rollback y presupuesto. La promoción requiere decisión explícita y
        documentada; si C no compensa su coste o pierde reproducibilidad,
        permanece como diagnóstico offline o herramienta interna de evaluación.
      - Contrato, seguridad, UX y gates:
        [`CHAT_RETRIEVAL_STRATEGY_COMPARISON.md`](../jurisprudence/CHAT_RETRIEVAL_STRATEGY_COMPARISON.md#plan-de-opción-c-investigación-agentiva).
  - [x] **Fase 3 — activación técnica.** `VITE_CHAT_MODE=live` y el backend están
    activos en Production desde el 31 de julio de 2026. El rollback es volver a
    `stub` y deshabilitar el backend. La activación técnica no cierra privacidad,
    retención ni revisión jurídica.
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
- [ ] Diseñar las landings por país con un modelo de datos reutilizable, URLs canónicas
  ASCII (`/espana`, `/portugal`, etc.) y redirecciones para variantes con caracteres especiales.
- [x] Definir el contrato del endpoint de chat, manejo de errores, cancelación de peticiones,
  límites de uso y estrategia de fallback del proveedor LLM. Cerrado en las secciones 5 y 6
  del diseño: eventos SSE, los dos `429` (el del limitador nativo llega sin ejecutar la
  función y no es SSE), `502` antes del primer token frente a `event: error` a mitad de
  stream, cancelación por `AbortSignal` y degradación a búsqueda léxica si el router falla.
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

- [ ] **Completar la tabla país → convenio: hoy alcanza 16 de los 98 convenios
  publicados.** `CONVENIOS_POR_PAIS`, en `normativa_citas.py`, solo mapea los
  países que litigan en el corpus actual. Los otros 82 convenios están
  publicados con su artículo de residencia y **ninguna cita puede llegar a
  ellos**: si entra una sentencia sobre Portugal o Italia, su «art. 4 CDI»
  quedará sin resolver aunque el precepto exista. Hoy no falla porque el corpus
  solo litiga con esos 16 países.
  - Los identificadores y títulos oficiales están en
    `normativa/es/manifest.json` (campo `titulo` de los registros con
    `grupo: cdi`). **Verifica cada país contra el título**, no lo deduzcas con
    una regex: los 96 convenios escriben el país de trece formas distintas y un
    país equivocado enlazaría una sentencia con el derecho de otro Estado. Por
    eso la tabla es curada y no generada.
  - Cierra con un test que exija que **ningún convenio publicado quede sin
    alias**, para que la tabla no vuelva a quedarse atrás en silencio. Modelo:
    `test_todos_los_convenios_generales_tienen_su_articulo_de_residencia` en
    `tests/test_normativa_boe.py`.
  - Ojo con los países que tienen convenio antiguo y moderno: el rango de
    ejercicios de `ConvenioPais` es lo que decide cuál aplica. Reino Unido y
    Argentina ya están así; comprueba si hay más al ampliar.

- [ ] **Guardarraíl contra la pérdida silenciosa de una norma al redescargar.**
  `descargar_normativa.py` reescribe `manifest.json` desde cero y descubre los
  convenios vigentes filtrando por título el índice del BOE. Si España denuncia
  un convenio, la siguiente descarga simplemente lo omite, `export_normativa`
  publica un precepto menos y **el test de «corpus al día» pasa**, porque compara
  la salida con la entrada nueva. La pérdida no la ve nadie.
  - Comparar el manifiesto nuevo con el anterior y **fallar ante una desaparición
    no declarada**, con una vía explícita para aceptarla (declararla en
    `CDI_DEROGADO` si sigue citándose, o registrarla como baja).
  - Misma lógica que el error que ya salta cuando el XML del diario no delimita
    ningún precepto: una omisión silenciosa es peor que un fallo ruidoso.

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
  - [x] Clave de jurisdicción unificada (1 de agosto de 2026): las 29 entradas de
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

- [x] **La raíz `/` servía una página en blanco y no era canónica de nada**
  (medido y resuelto el 1 de agosto de 2026). `dist/index.html` conserva el
  `<div id="root">` **vacío** —el prerenderizado escribe una copia por ruta en su
  subdirectorio, pero no toca la shell—, declaraba `canonical` hacia sí misma y
  no está en el sitemap: la home era una URL sin contenido que no apuntaba a
  `/espana`. Ahora `netlify.toml` la redirige con un `301` a `/espana`, que es la
  que el sitemap publica con prioridad `1.0`. `force` es imprescindible, porque
  el fichero existe y Netlify lo serviría antes que la redirección;
  `tests/test_frontend_cache_policy.py` lo fija junto al orden respecto al
  fallback `/*`.
  - **Verificar tras el deploy** que el monitor `803628459` de UptimeRobot sigue
    en verde: apunta a la raíz y ahora depende de que siga la redirección
    ([`UPTIMEROBOT.md`](../operations/UPTIMEROBOT.md)).
- [x] Marcar con `BreadcrumbList` las rutas estáticas indexables `/manifiesto`,
  `/metodologia` y `/colaborar`, además de `/espana/fuentes`, que cuelga de
  España. `/privacidad` queda fuera por ser `noindex`: los datos estructurados
  son para el buscador. `tests/entry-server.test.tsx` recorre las rutas
  indexables y comprueba además que lo `noindex` no emite nada.

- [x] Añadir metadatos, canonical, Open Graph y enlaces internos específicos para cada
  landing de país (1 de agosto de 2026): `title` y `description` propios en
  `countryRoutes.json`, prerenderizados por ruta y con las 29 en el sitemap.
  **Falta `schema.org`**, que era la otra mitad de esta tarea.
- [x] Marcar cada landing de país con datos estructurados (`schema.org`) (1 de agosto de
  2026): `BreadcrumbList` en `CountryPage` y en `SpainPage` —`/espana` monta el chat y
  no la plantilla compartida, así que se quedaba fuera siendo la landing de mayor
  prioridad— y `Legislation` en `TaxTreaty`, este último solo cuando el convenio de
  **esa** página está resuelto: al navegar entre países, el render previo al efecto
  llegaba a declarar el convenio de la jurisdicción anterior. Sin `FAQPage` ni
  `Article`. Se componen en
  `frontend/src/lib/structured-data.ts`, se emiten desde el árbol de React —así el HTML
  prerenderizado y la SPA no divergen— y `tests/entry-server.test.tsx` comprueba que
  llegan al HTML servido. La fecha se publica como `legislationDateVersion`, nunca como
  `legislationDate`: el corpus conoce la redacción vigente, no la firma del convenio.
  Contrato en [`COUNTRY_PAGES.md`](../product/COUNTRY_PAGES.md).
- [x] Mostrar en cada landing las fuentes legales del convenio con España: título oficial,
  artículo de residencia, redacción vigente, texto literal y enlace al BOE, o la
  declaración explícita de que no hay convenio en vigor. Todo sale del corpus normativo
  versionado, así que el «proceso editorial» es regenerarlo (`make export-normativa`).
  Alcance y limitaciones siguen en la propia página: no hay jurisprudencia de ese país.
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
- [ ] **Crear la etiqueta `corpus` en el repositorio** y añadirla a
  `labels:` de la plantilla. Hoy usa `help wanted` porque GitHub solo aplica
  etiquetas que ya existen. Con varias propuestas de país a la vez, una etiqueta
  por país ordena el backlog.
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
  V1 guarda una pregunta y sus dos respuestas por turno. Migraciones, RLS, RPC,
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
  pregunta autosuficiente viaja a OpenAI para A y a Google/Gemini para B; la
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
    pregunta no vacía, no el historial local. Supabase guarda esa pregunta y las
    dos respuestas A/B del turno, sin IP, user-agent ni diagnósticos brutos.
- [x] Añadir validación automática del schema del corpus, detección de duplicados y
  trazabilidad de cada criterio hasta su sentencia de origen.

## Calidad y despliegue

- [x] Configurar CI con lint, typecheck, tests y build del frontend y la API.
- [ ] Añadir smoke tests de navegador para `/`, `/metodologia`, `/colaborar` y las landings
  públicas, incluyendo comprobación de redirecciones, sitemap, robots y corpus publicado.
  - `/colaborar` es la que más lo necesita: es la única landing cuyo valor depende de ser
    indexable, así que hay que comprobar que su redirect sirve el prerender y que la meta
    `robots` llega como `index, follow`. Si el redirect falla, la SPA responde igual y el
    fallo no se nota hasta que Search Console no indexa nada.
  - Las páginas de país sin corpus deben comprobarse al revés: que siguen respondiendo
    `noindex, follow` y que **no** aparecen en el sitemap.
- [x] Documentar y automatizar el pipeline reproducible de actualización del corpus y su deploy.
- [x] **Corregir `CLAUDE.md`, desfasado respecto al código.** Ya documenta los
  siete resultados finales y marca como desfasada la tabla histórica de costes;
  las tarifas vigentes proceden exclusivamente del catálogo versionado de
  `llm_gateway`.

## SEO y operación

- [ ] Crear una landing específica por país (`/españa`, `/portugal`, etc.) con información detallada sobre la residencia fiscal, criterios, obligaciones y particularidades de cada país.
- [x] Configurar Sentry para la API y el frontend y documentar sus variables de
  entorno (`c0fb582`), reflejado en `README.md` y `CLAUDE.md` el 1 de agosto de
  2026 con la tabla de variables. El límite que describía esta entrada —«la
  Netlify Function del chat no está instrumentada»— **ya no rige**: la Function
  manda a su propio proyecto `residencia-fiscal-chat` desde el 1 de agosto y
  quedó activada en producción el 2 de agosto
  ([`CHAT_OBSERVABILITY.md`](../operations/CHAT_OBSERVABILITY.md)).
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
  - Añadir pruebas con mocks, documentar únicamente los nombres de variables en
    `.env.example` y ejecutar un único smoke real explícito después de verificar
    dominio y destinatario.
- [x] Configurar PostHog para el frontend y documentar sus variables de entorno.
  Estaba implementado (`PostHogAnalytics.tsx`, montado una vez en `AppLayout`, con
  su suite) y sin documentar; documentado el 1 de agosto de 2026 en
  [`ANALYTICS.md`](../product/ANALYTICS.md) junto a GA4. **El frontend no lee
  ninguna variable**: el ID de GA4 y la clave de proyecto de PostHog son públicos
  por diseño y viajan en el bundle; las `POSTHOG_*` del `.env` son de servidor y
  las usa el informe semanal. La puerta de activación es única
  (`isGoogleAnalyticsEnabled`) para las dos analíticas.
- [x] Tras un deploy correcto, comprobar que `robots.txt`, `sitemap.xml` y `llms.txt`
  devuelven `200` desde `https://residenciafiscal.org/`.
- [x] **Autoalojar Space Grotesk e Inter** (2 de agosto de 2026, punto 8 de
  [`SEO_AUDIT.md`](../product/SEO_AUDIT.md)). Salían de Google Fonts: dos
  conexiones a un tercero y una hoja de estilo bloqueante delante del primer
  pintado, más dos excepciones en la CSP. Ahora vienen de
  `@fontsource-variable/*` (`src/main.tsx`) y la CSP queda en `font-src 'self'`
  y `style-src 'self' 'unsafe-inline'`.
  - **Un fichero por familia, no uno por peso.** Son las versiones variables
    (`wght` 100–900 y 300–700): 48 KB de Inter y 22 KB de Space Grotesk cubren
    los siete pesos del brandbook. Los otros seis subconjuntos viajan en el
    deploy, pero su `unicode-range` los deja sin pedir.
  - **El `preload` no puede escribirse en `index.html`**: el woff2 emitido lleva
    hash de contenido. Lo inyecta `scripts/inject-font-preload.mjs` leyendo el
    CSS ya compilado, y va **antes** de `prerender.mjs` en el `postbuild` porque
    de esa shell salen las ~150 copias por ruta. Solo precarga los dos
    subconjuntos `latin`, que son los que pinta el castellano.
  - **No se afirma mejora de LCP**: sin datos de campo de Core Web Vitals solo
    consta que desaparecen las dos conexiones externas y el CSS bloqueante.
    Comprobado en Chromium contra el build: 0 peticiones a Google Fonts y
    exactamente los 2 woff2 precargados.
  - Queda fuera a propósito `frontend/og/*.html`, que sí sigue pidiendo Google
    Fonts: es el generador local del PNG (`npm run og`), no se sirve a nadie y no
    toca la CSP. Migrarlo obligaría a regenerar los dos PNG en el mismo commit.
  - **El cambio de CSP exige redeploy**; hasta entonces rige la anterior, que era
    compatible por más permisiva.
- [x] **Registrar el sitemap en Google Search Console** (1 de agosto de 2026).
  La propiedad `sc-domain:residenciafiscal.org` **no existía: se creó y
  verificó por API el mismo día**, sin pasar por la UI. La Site Verification
  API está deshabilitada en el proyecto GCP `presupuestor-485509` (inaccesible
  para la cuenta local), así que se habilitó junto a la de Search Console en
  `doctor-489817` —que sí es del usuario— y la verificación la hizo su service
  account `claude-mcp-access@doctor-489817`: token DNS, registro TXT creado por
  la API de Cloudflare y `webResource.insert`. Esa SA delegó después la
  propiedad a las cuentas personales y a
  `presupuestor-claude-skill@presupuestor-485509`, la del skill
  `google-search-console`, que quedó `siteOwner` y envió el sitemap. Google lo
  descargó con **0 errores y 0 avisos**. Detalle operativo completo en
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
    habilitadas en `doctor-489817` y el procedimiento (token → TXT → verify →
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

- [ ] Evaluar si merece la pena mostrar automáticamente en la barra lateral el país activo
  cuando quede fuera de los tres países visibles inicialmente.
- [x] Generar los redirects de Netlify desde `countryRoutes.json` para evitar mantener una
  segunda lista manual en `netlify.toml`.
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

- [x] **Cerrar una única arquitectura SEO para todos los países** (2 de agosto
  de 2026). España es la primera instancia de
  `/<pais>/{fuentes,normativa,convenios,sentencias,doctrina}`. La plantilla,
  constructores de ruta, canonicales, breadcrumbs, prerender, sitemap y gates
  se reutilizan para cada jurisdicción; las ramas sin corpus suficiente no se
  materializan y devuelven 404. Alineados el diseño rector, `CLAUDE.md`,
  arquitectura, estructura del repositorio, páginas de país, normativa y esta
  auditoría/backlog.

- [ ] **Pedir indexación manual en la UI de GSC** (2026-08-03, ~15 min). Unas
  diez URLs prioritarias: `/espana/normativa`, `lirpf-a9`, las fichas de CDI
  con más demanda (Andorra, Portugal, Francia, Emiratos), `/colaborar` y dos o
  tres páginas de país. La API no permite solicitar indexación; solo la
  interfaz.
- [x] **Confirmado que el sitemap registra 149 URLs y no 38** (2 de agosto de
  2026, por la API de Search Console, sin esperar al informe del lunes). Google
  descargó la versión antigua el 1 de agosto a las 19:38 —antes del deploy de
  normativa—; tras el reenvío del 2 de agosto, `sitemaps list` devuelve
  `submitted: 149`, `errors: 0` y `warnings: 0`, con `lastDownloaded` el mismo 2
  de agosto a las 11:36 UTC. `indexed: 0` es lo esperado en un sitemap recién
  descargado y no mide la indexación real.
- [x] **Materializar el 301 de la raíz.** Ya existía antes de esta ejecución:
  `/` → `/espana` como `301!` generado por `build-netlify-redirects.mjs`, con
  test. La fase B hereda esta base y no debe duplicarla (§5.1 del diseño).
- [ ] **Primeros backlinks** (continuo desde 2026-08-03). Repositorio público
  de GitHub, perfiles y comunidades de fiscalidad internacional o expats. Sin
  autoridad entrante, la cola de indexación de un dominio nuevo seguirá lenta
  con independencia de los ajustes técnicos.
- [x] **Gate A.** Verificado contra §9 del
  diseño: schemas válidos, cobertura completa, sin solapes de periodos, ningún
  `countries` desconocido, diff vacío al regenerar dos veces.
- [x] **Gate C1 técnico.** Build preview con `X-Robots-Tag: noindex`,
  404 real de toda ruta `internal_preview` en producción, allowlist sin fugas.
  Este gate no concede publicación.
- [ ] **Decisión de producto: ficha documental sin análisis** (§6.3 del
  diseño; decidir antes de arrancar la fase B, orientativo semana del
  2026-08-10). Solo metadatos primarios y citas literales verificadas, sin
  resultados ni resúmenes del agente. Es la única vía de contenido
  jurisprudencial indexable mientras no haya revisor; exige su propia decisión
  jurídica de alcance, pero no revisión caso a caso.
- [ ] **Fase B — piloto de 3 bilaterales** (tras el Gate A; orientativo desde
  la semana del 2026-08-10). `/espana/convenios`, tres bilaterales que cubran
  convenio único, sucesión (Japón/Rumanía/China) y fuente del diario; sus
  páginas de país se convierten en hubs en el mismo lote. Ampliar por lotes
  solo si el Gate B pasa. Los componentes se implementan desde el inicio por
  jurisdicción, aunque `es` sea la única instancia con datos.
- [ ] **Checkpoint GSC de las fichas de CDI** (2026-09-01). Si las 97 aparecen
  de forma masiva como «Crawled – currently not indexed», activar la
  diferenciación prevista; hasta entonces no podar el sitemap (§12.1 del
  diseño y decisión del 2 de agosto de no reducir URLs).
- [x] **Actualizar los documentos de §13 del diseño con cada fase**, no al
  final: `COUNTRY_PAGES.md`, `SEO_AUDIT.md`, `NORMATIVA.md`, `ARCHITECTURE.md`
  y este backlog (las tareas absorbidas por el plan se marcan al implementarse).
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
- [x] **Limpieza menor de excepciones históricas** (2026-08-02). El diseño del
  chat backend se promocionó a
  [`docs/development/CHAT_BACKEND_DESIGN.md`](../development/CHAT_BACKEND_DESIGN.md)
  —seguía referenciado desde `NETLIFY_EDGE.md`, este backlog y
  `frontend/CLAUDE.md`— y el plan de ejecución se desversionó (queda como
  scratch local). `docs/superpowers/` ya no contiene ningún fichero versionado
  y la regla de `CLAUDE.md` se cumple sin excepciones.

## Criterio de cierre SEO

- El home y `/metodologia` responden `200` y tienen canonical propia.
- El sitemap sólo contiene URLs públicas, canónicas y rastreables.
- `/c/` permanece fuera del índice por ser contenido de conversación dinámico.
- El WAF no bloquea Googlebot, crawlers LLM ni monitores autorizados.
