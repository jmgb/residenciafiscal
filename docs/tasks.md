# Tareas pendientes

Backlog operativo del proyecto. Las tareas SEO y de despliegue deben verificarse
contra el dominio público después de cada deploy.

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
  - [ ] **Fase 1 — implementación detrás del stub.** 15 tareas TDD: nueve módulos puros
    con Vitest y un `chat.ts` delgado. Producción sigue simulada. La tarea del
    presupuesto queda bloqueada por la fase 0b; el resto no depende de ella.
  - [ ] **Fase 2 — evaluación.** Banco de 40 preguntas versionado. Bloquean los gates
    binarios (0 identificadores inventados, 0 párrafos sin fuente, fuera de corpus,
    adversariales, presupuesto); `recall@12` se publica como línea base medida.
  - [ ] **Fase 3 — activación.** Poner `VITE_CHAT_ENGINE_MODE=live` en Netlify. El
    rollback es quitar la variable y redesplegar.
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
- [ ] Añadir smoke tests de navegador para `/`, `/metodologia` y las landings públicas,
  incluyendo comprobación de redirecciones, sitemap, robots y corpus publicado.
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

## Criterio de cierre SEO

- El home y `/metodologia` responden `200` y tienen canonical propia.
- El sitemap sólo contiene URLs públicas, canónicas y rastreables.
- `/c/` permanece fuera del índice por ser contenido de conversación dinámico.
- El WAF no bloquea Googlebot, crawlers LLM ni monitores autorizados.
