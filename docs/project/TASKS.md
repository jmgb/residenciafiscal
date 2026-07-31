# Tareas pendientes

Backlog operativo del proyecto. Las tareas SEO y de despliegue deben verificarse
contra el dominio público después de cada deploy.

> **Si retomas el backend del chat**, separa dos líneas: el experimento de
> comparación entre el corpus v3 y Gemini File Search, y la activación
> productiva. Esta última sigue bloqueada por la **fase 0b** (cuotas y
> presupuesto), la ampliación del corpus y la revisión humana. La fase 0 de
> plataforma ya está ejecutada y medida.
>
> El diseño y el plan viven en `docs/superpowers/`, que está en `.gitignore`: esos
> dos ficheros son excepciones añadidas con `git add -f`. Si creas más documentos
> ahí, no se versionarán solos.

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

## Producto y arquitectura

- [ ] **Sustituir el motor `stub` del chat por un backend real.** Diseñado y planificado:
  Netlify Edge Function en `/api/chat`, recuperación con fuentes trazables y
  citas por marcadores `[S<n>]` que el servidor resuelve al ROJ real.
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
      - [x] Fijar el gateway al commit inmutable `208eac03` posterior a `v0.5.0`:
        conserva las correcciones de transporte/cómputo y añade validación por
        modelo, esfuerzo `max` y el catálogo de precios del 2026-07-31.
        Sustituir el SHA por una etiqueta cuando exista una release que lo incluya.
      - [x] Limpiar referencias operativas residuales a `src/model_pricing.py`,
        ya borrado, en documentación y configuración de imports.
      - [ ] Antes de activar el chat, comparar respuestas Luna + `max` sobre el
        mismo banco de preguntas y evidencia recuperada; medir calidad,
        latencia, tokens y coste. Nunca usar esta prueba para analizar PDF ni
        preparar casos del corpus.
    - [ ] Repetir las ocho con el mismo modelo; solo si pasan, ejecutar las 40.
  - Diseño: [`docs/superpowers/specs/2026-07-29-chat-backend-design.md`](../superpowers/specs/2026-07-29-chat-backend-design.md)
  - Plan de ejecución: [`docs/superpowers/plans/2026-07-29-chat-backend.md`](../superpowers/plans/2026-07-29-chat-backend.md)
  - [x] **Fase 0 — spike de plataforma (gate).** Ejecutado el 2026-07-29 contra un
    Deploy Preview. Cuatro de cinco criterios pasan y **la decisión de runtime queda
    confirmada**: p95 de CPU 15,3 ms, streaming de 19,87 s, cabeceras en 0,30 s y los
    tres paquetes cargan en Deno. Mediciones en
    [`docs/operations/NETLIFY_EDGE.md`](../operations/NETLIFY_EDGE.md).
  - [ ] **Fase 0b — decidir el mecanismo de cuotas y presupuesto (BLOQUEANTE).** El
    quinto criterio falló: `onlyIfMatch` de Netlify Blobs **no da compare-and-swap**
    bajo concurrencia. Cinco peticiones simultáneas dejaron un contador de cinco
    incrementos en dos, y todas creyeron haber escrito. Sin resolverlo, el techo de
    gasto no es una garantía. Tres opciones en la sección 4 del diseño: clave por
    petición con recuento por listado (validada en el mismo spike, cuesta 130–420 ms),
    almacén con atomicidad real (proveedor externo) o cuotas best-effort.

    > **Para quien retome esto.** Lee en este orden: la sección 5 de
    > [`docs/operations/NETLIFY_EDGE.md`](../operations/NETLIFY_EDGE.md) (la evidencia del
    > fallo y la alternativa medida) y la sección 4 del diseño (las tres opciones con
    > sus contrapartidas). **Es una decisión de producto, no técnica**: cuánto vale
    > que el techo de gasto sea una garantía dura frente a 130–420 ms de latencia
    > extra o un proveedor más en el stack. No la tomes tú solo; pregúntala.
    >
    > Una vez decidida, la tarea 9 del plan deja de estar bloqueada. Su API pública
    > (`consumirCuota`, `reservar`, `reconciliar`, microdólares enteros, fallo
    > cerrado) sigue siendo válida y sus tests de concurrencia también: solo cambia
    > el mecanismo de escritura por debajo.
    >
    > El trabajo vive en la rama `spike/chat-edge-platform`, **sin push**. El código
    > del spike se borró a propósito; `NETLIFY_EDGE.md` explica cómo reconstruirlo si
    > hace falta volver a medir.
  - [ ] **Fase 1 — implementación detrás del stub.** 15 tareas TDD: nueve módulos puros
    con Vitest y un `chat.ts` delgado. Producción sigue simulada. La tarea del
    presupuesto queda bloqueada por la fase 0b; el resto no depende de ella.

    > **La fuente del chat ya está decidida e implementada en el comparador
    > local, pero no en el backend productivo.** Debe ser
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
    > El diseño y la validación con 1 y 5 sentencias ya están completados. La
    > ampliación a 106 y la aprobación jurídica humana siguen pendientes.
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
    - [x] Implementar `chat-engine.live.ts` y el parser SSE individual del
      protocolo 2;
      validar en la frontera que cada evento `sources` contiene exclusivamente
      `ChatSourceV2`, sin aceptar fuentes legadas desde el backend. Tolera
      eventos y UTF-8 partidos, exige un único terminal, distingue errores HTTP
      no SSE y envía solo `role` y `content`. El motor sigue sin seleccionarse.
    - [ ] Extender el protocolo 2 al modo comparativo A/B con `strategy`,
      `answer_start`, `answer_done`, coste y terminal global; adaptar
      `ChatMessage`/UI antes de conectar el selector al backend.
  - [ ] **Fase 3 — activación.** Poner `VITE_CHAT_ENGINE_MODE=live` en Netlify. El
    rollback es quitar la variable y redesplegar.
- [ ] **Llevar el corpus v3 de 5 a 106 sentencias.** El contrato y la muestra ya
  están congelados. La expansión está parada hasta autorizar el manifiesto real
  de los 106 PDF y organizar la revisión humana; bloquea la activación
  productiva del chat. Estado y siguiente gate:
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
    clasificadas; sigue pendiente la aprobación jurídica humana y por eso no se
    autorizan las 106.
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
  - Decisión pendiente que conviene cerrar de paso: unificar la clave de
    jurisdicción. El dato usa ISO (`es`) y las rutas del frontend usan slug
    (`/espana`); añadir un campo `code` a `frontend/src/data/countryRoutes.json`
    es un cambio de una línea.

## SEO y contenido

- [ ] Añadir metadatos, canonical, Open Graph, schema.org y enlaces internos específicos
  para cada landing de país.
- [ ] Mostrar en cada landing las fuentes legales, fecha de revisión, alcance y limitaciones
  del contenido, con un proceso editorial para mantenerlo actualizado.

## Colaboración internacional

El proyecto invita a expertos de cualquier jurisdicción a aportar la jurisprudencia
de su país. Contrato y perfiles en
[`CONTRIBUTING.md`](../../CONTRIBUTING.md#aportar-la-jurisprudencia-de-otro-país);
página pública en `/colaborar`, la **única ruta indexable** de la invitación
(las landings de país son `noindex`).

- [ ] **Traducir la plantilla `aportar_pais.yml` al inglés.** La invitación es
  mundial pero el formulario está solo en español, así que Brasil, Haití y toda
  jurisdicción no hispanohablante se topan con un formulario que no entienden.
  Mismo problema, un nivel más abajo: el schema de extracción también está en
  español, y un corpus no hispano necesita traductor jurídico antes que
  desarrollador.
- [ ] **Verificar en GitHub el prerrellenado de la issue.** `contribution.ts`
  construye `?template=aportar_pais.yml&title=…&pais=<País>`; el formato de query
  y el YAML están validados, pero **no se ha comprobado contra GitHub en vivo**
  que rellene el campo `pais`. Abrir la URL una vez tras el deploy.
- [ ] **Crear la etiqueta `corpus` en el repositorio** y añadirla a
  `labels:` de la plantilla. Hoy usa `help wanted` porque GitHub solo aplica
  etiquetas que ya existen. Con varias propuestas de país a la vez, una etiqueta
  por país ordena el backlog.
- [ ] **Difundir `/colaborar` fuera de GitHub.** Con las landings en `noindex`, el
  descubrimiento depende de `/colaborar`, de `llms.txt` y de canales externos
  (colegios de abogados, asociaciones de fiscalistas, LinkedIn). Sin difusión, la
  invitación solo la ve quien ya está dentro.
- [ ] **Decidir si activar GitHub Discussions.** Una propuesta de país es una
  conversación antes que una tarea; hoy todo entra como issue. Requiere activarlo
  en la web del repositorio.

## Seguridad y datos

- [ ] Proteger el futuro endpoint del chat con autenticación/cuotas y rate
  limiting, y evitar que las consultas sensibles aparezcan completas en logs o analítica.
- [ ] **Requisitos legales previos a activar el chat real.** Bloquean la fase 3: con el
  motor en `stub` no sale nada de Netlify, con el real la pregunta viaja a OpenAI.
  - [ ] Aviso de que no es asesoramiento jurídico, visible junto al chat. Hoy ese papel
    lo cumple el aviso de contenido simulado, que **desaparece** al activar `live`: si no
    se sustituye, la activación quita una advertencia en vez de cambiarla.
  - [ ] Política de privacidad que declare el envío de la consulta a OpenAI como
    encargado del tratamiento, con `store: false` y sin conservación en servidor. Los
    criterios de residencia invitan a escribir dónde vive uno y dónde está su familia.
  - [ ] Aviso en la caja de entrada de no incluir datos identificativos: es la única
    mitigación que actúa antes de que el dato salga.
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
  entorno (`c0fb582`). Queda pendiente reflejarlo en `README.md` y `CLAUDE.md`.
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
- [ ] Configurar PostHog para el frontend y documentar sus variables de entorno.
- [x] Tras un deploy correcto, comprobar que `robots.txt`, `sitemap.xml` y `llms.txt`
  devuelven `200` desde `https://residenciafiscal.org/`.
- [ ] Registrar `https://residenciafiscal.org/sitemap.xml` en Google Search Console
  y revisar la primera descarga y los errores de cobertura.
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

## Criterio de cierre SEO

- El home y `/metodologia` responden `200` y tienen canonical propia.
- El sitemap sólo contiene URLs públicas, canónicas y rastreables.
- `/c/` permanece fuera del índice por ser contenido de conversación dinámico.
- El WAF no bloquea Googlebot, crawlers LLM ni monitores autorizados.
