# Tareas pendientes

Backlog operativo del proyecto. Las tareas SEO y de despliegue deben verificarse
contra el dominio público después de cada deploy.

> **Si retomas el backend del chat**, empieza por las dos entradas bloqueadas de
> «Producto y arquitectura»: la **fase 0b** (decisión sobre cuotas y presupuesto)
> y el **corpus OKF**, que decide de qué lee el chat. Ambas están anotadas con lo
> que hay que leer y por qué. La fase 0 ya está ejecutada y medida.
>
> El diseño y el plan viven en `docs/superpowers/`, que está en `.gitignore`: esos
> dos ficheros son excepciones añadidas con `git add -f`. Si creas más documentos
> ahí, no se versionarán solos.

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
  Netlify Edge Function en `/api/chat`, router LLM a facetas del corpus + filtro
  determinista, y citas por marcadores `[S<n>]` que el servidor resuelve al ROJ real.
  El caso de uso principal y el contrato de respuesta/recuperación están en
  [`docs/CHAT_JURISPRUDENCE_USE_CASE.md`](CHAT_JURISPRUDENCE_USE_CASE.md): el
  chat ayuda al abogado a investigar casos comparables por cuestión, hechos y
  pruebas con referencias a sentencia y página; no predice su caso.
  - Diseño: [`docs/superpowers/specs/2026-07-29-chat-backend-design.md`](superpowers/specs/2026-07-29-chat-backend-design.md)
  - Plan de ejecución: [`docs/superpowers/plans/2026-07-29-chat-backend.md`](superpowers/plans/2026-07-29-chat-backend.md)
  - [x] **Fase 0 — spike de plataforma (gate).** Ejecutado el 2026-07-29 contra un
    Deploy Preview. Cuatro de cinco criterios pasan y **la decisión de runtime queda
    confirmada**: p95 de CPU 15,3 ms, streaming de 19,87 s, cabeceras en 0,30 s y los
    tres paquetes cargan en Deno. Mediciones en
    [`docs/operations/NETLIFY_EDGE.md`](operations/NETLIFY_EDGE.md).
  - [ ] **Fase 0b — decidir el mecanismo de cuotas y presupuesto (BLOQUEANTE).** El
    quinto criterio falló: `onlyIfMatch` de Netlify Blobs **no da compare-and-swap**
    bajo concurrencia. Cinco peticiones simultáneas dejaron un contador de cinco
    incrementos en dos, y todas creyeron haber escrito. Sin resolverlo, el techo de
    gasto no es una garantía. Tres opciones en la sección 4 del diseño: clave por
    petición con recuento por listado (validada en el mismo spike, cuesta 130–420 ms),
    almacén con atomicidad real (proveedor externo) o cuotas best-effort.

    > **Para quien retome esto.** Lee en este orden: la sección 5 de
    > [`docs/operations/NETLIFY_EDGE.md`](operations/NETLIFY_EDGE.md) (la evidencia del
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

    > **La fuente del chat ya está decidida, pero aún no implementada.** Debe ser
    > `residenciafiscal-case/3` con anclajes verbatim; no el JSONL ni el perfil v2
    > directamente. El plan antiguo genera `lib/corpus.ts` desde el JSONL y por
    > eso sus tareas 3–6 y las partes del protocolo están marcadas como
    > parcialmente superadas.
    >
    > Las piezas de plataforma y varios módulos siguen siendo reutilizables. La
    > recuperación cambia de sentencias completas a cuestiones jurídicas, y las
    > tarjetas llevan hechos, valoración, resultado por cuestión y fragmentos
    > verbatim. Cada marcador debe resolverse a **sentencia + cuestión + página**.
    >
    > Depende de diseñar y validar v3 primero con 1 sentencia, después con 5, y
    > solo entonces ampliar a 106, además de la revisión humana.
  - [ ] **Fase 2 — evaluación.** Banco de 40 preguntas versionado. Bloquean los gates
    binarios (0 identificadores inventados, 0 párrafos sin fuente, fuera de corpus,
    adversariales, presupuesto); `recall@12` se publica como línea base medida.
    El catálogo inicial de comportamiento y preguntas está en
    [`docs/CHAT_USER_QUESTION_CATALOG.md`](CHAT_USER_QUESTION_CATALOG.md).
    - [x] Seleccionar y contestar manualmente 40 preguntas contra la muestra de
      cinco, con casos, contracasos, límites y gaps de datos:
      [`docs/experiments/CHAT_QUESTION_PILOT_5.md`](experiments/CHAT_QUESTION_PILOT_5.md).
    - [ ] Convertir la verdad de referencia manual en un artefacto
      machine-readable cuando exista el schema v3.
    - [ ] Evolucionar `ChatSource` y el protocolo a v2 con `issueId`,
      `anchorId`, página, fidelidad y hash de fuente; adaptar persistencia y UI
      sin perder varios anclajes de una misma sentencia.
  - [ ] **Fase 3 — activación.** Poner `VITE_CHAT_ENGINE_MODE=live` en Netlify. El
    rollback es quitar la variable y redesplegar.
- [ ] **Llevar el corpus OKF de 1 a 106 sentencias.** Está parado esperando **revisión
  humana y migración del schema orientada al chat**, y bloquea la fase 1 del chat. Estado en
  [`docs/OKF_PIPELINE.md`](OKF_PIPELINE.md).
  - [ ] Diseñar `residenciafiscal-case/3` a partir del caso de uso principal y
    de los doce gaps del piloto de 40 preguntas; probarlo con 1 sentencia y
    después regenerar las 5 antes de autorizar las 106. Roadmap canónico:
    [`docs/JURISPRUDENCE_DATA_V3_ROADMAP.md`](JURISPRUDENCE_DATA_V3_ROADMAP.md).
    - [x] Documentar arquitectura, responsabilidades, rollout, gates y estrategia
      RAG.
    - [x] Escribir el contrato campo por campo
      `docs/JURISPRUDENCE_CASE_SCHEMA_V3.md`.
    - [x] Implementar modelos Pydantic, JSON Schema, fixtures y tests.
    - [x] Implementar contrato, extractor crudo, JSON Schema, fixtures y tests
      de `residenciafiscal-verbatim/1`.
    - [x] Generar `residenciafiscal-verbatim/1` en JSON para `SAN 1210/2023`.
    - [x] Construir y validar el caso v3 híbrido de `SAN 1210/2023`.
    - [x] Renderizar su Markdown e índice por cuestión desde el modelo canónico.
    - [x] Validar 18 preguntas aplicables del piloto contra esa sentencia.
    - [ ] Regenerar las cinco con el mismo pipeline y ejecutar las 40 preguntas.
    - [ ] Comparar recuperación estructurada/léxica con embeddings antes de
      elegir la estrategia definitiva.
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
    `sentencias/okf_muestra_5.json`. Siguen pendientes la aprobación jurídica
    humana y la clasificación de 17 citas; por eso no se autorizan las 106.
  - [ ] Materializar el corpus verbatim por páginas definido en
    [`docs/VERBATIM_CORPUS.md`](VERBATIM_CORPUS.md): JSON canónico y Markdown
    opcional. Medir 1 y 5 antes de decidir almacenamiento para 106.
- [ ] Diseñar las landings por país con un modelo de datos reutilizable, URLs canónicas
  ASCII (`/espana`, `/portugal`, etc.) y redirecciones para variantes con caracteres especiales.
- [x] Definir el contrato del endpoint de chat, manejo de errores, cancelación de peticiones,
  límites de uso y estrategia de fallback del proveedor LLM. Cerrado en las secciones 5 y 6
  del diseño: eventos SSE, los dos `429` (el del limitador nativo llega sin ejecutar la
  función y no es SSE), `502` antes del primer token frente a `event: error` a mitad de
  stream, cancelación por `AbortSignal` y degradación a búsqueda léxica si el router falla.

## SEO y contenido

- [ ] Añadir metadatos, canonical, Open Graph, schema.org y enlaces internos específicos
  para cada landing de país.
- [ ] Mostrar en cada landing las fuentes legales, fecha de revisión, alcance y limitaciones
  del contenido, con un proceso editorial para mantenerlo actualizado.

## Colaboración internacional

El proyecto invita a expertos de cualquier jurisdicción a aportar la jurisprudencia
de su país. Contrato y perfiles en
[`CONTRIBUTING.md`](../CONTRIBUTING.md#aportar-la-jurisprudencia-de-otro-país);
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

- [ ] Exigir `RESIDENCIAFISCAL_API_TOKEN` en producción, proteger `/analizar` con rate
  limiting y evitar que las consultas sensibles aparezcan completas en logs o analítica.
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
  - Las 20 páginas de país deben comprobarse al revés: que siguen respondiendo
    `noindex, follow` y que **no** aparecen en el sitemap.
- [x] Documentar y automatizar el pipeline reproducible de actualización del corpus y su deploy.
- [ ] **Corregir `CLAUDE.md`, desfasado respecto al código.** Detectado al diseñar el
  backend del chat, y ya indujo a error una estimación de coste:
  - Enumera 5 resultados finales; `config.py:156-164` define 7 (faltan `OTROS` y
    `FUERA_DE_ALCANCE`).
  - Su tabla de costes da `$0.006` por PDF con `gpt-5.6-luna`, pero `model_pricing.py:23`
    tarifa ese modelo a `$1/M` de entrada y `$6/M` de salida, y los registros reales del
    JSONL rondan `$0.017` por sentencia.

## SEO y operación

- [ ] Crear una landing específica por país (`/españa`, `/portugal`, etc.) con información detallada sobre la residencia fiscal, criterios, obligaciones y particularidades de cada país.
- [x] Configurar Sentry para la API y el frontend y documentar sus variables de
  entorno (`c0fb582`). Queda pendiente reflejarlo en `README.md` y `CLAUDE.md`.
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
- [ ] Evaluar si merece la pena generar los redirects de Netlify desde `countryRoutes.json` para
  evitar mantener una segunda lista manual en `netlify.toml`.
- [ ] Evaluar si merece la pena añadir tests de aislamiento que garanticen que cada país consulta
  únicamente su propio corpus cuando existan corpus nacionales adicionales.

## Criterio de cierre SEO

- El home y `/metodologia` responden `200` y tienen canonical propia.
- El sitemap sólo contiene URLs públicas, canónicas y rastreables.
- `/c/` permanece fuera del índice por ser contenido de conversación dinámico.
- El WAF no bloquea Googlebot, crawlers LLM ni monitores autorizados.
