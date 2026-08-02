# Documentación

Este índice es la puerta de entrada a la documentación técnica y de producto de
Residencia Fiscal. El [`README.md`](../README.md) de la raíz explica qué hace el
proyecto y cómo arrancarlo; aquí se documentan su diseño, sus contratos y su
operación.

## Empieza aquí

| Necesidad | Documento |
|---|---|
| Entender los componentes y flujos | [Arquitectura](ARCHITECTURE.md) |
| Saber dónde debe vivir cada archivo | [Estructura del repositorio](REPOSITORY_STRUCTURE.md) |
| Preparar el entorno y contribuir | [Guía de contribución](../CONTRIBUTING.md) |
| Consultar comandos y reglas para agentes | [Guía de desarrollo](../CLAUDE.md) |
| Revisar el trabajo pendiente | [Backlog](project/TASKS.md) |

## Autoridad y vigencia

No todos los documentos tienen la misma función. Ante una discrepancia, usa
esta jerarquía:

| Pregunta | Fuente que manda |
|---|---|
| ¿Qué dice la resolución o la norma? | PDF/XML oficial inmutable y su hash |
| ¿Qué estructura deben cumplir los datos? | Schema versionado, modelos y tests de contrato |
| ¿Qué debe hacer el producto? | Caso de uso y contrato funcional del área |
| ¿Qué arquitectura y trabajo siguen vigentes? | `ARCHITECTURE.md` y `project/TASKS.md` |
| ¿Qué se midió y con qué límites? | Documento e informe de la fase experimental |
| ¿Cómo se pensó o ejecutó un cambio anterior? | Specs y planes de `superpowers/` |

Los planes y experimentos conservan decisiones y evidencia, pero no sustituyen
el estado actual ni un contrato posterior. Si cambia una decisión, actualiza en
el mismo cambio el documento canónico y `project/TASKS.md`; enlaza la evidencia
en vez de copiar sus cifras en varios sitios.

## Jurisprudencia

El orden recomendado de lectura es:

1. [Arquitectura y estado vigente del chat](jurisprudence/CHAT_SYSTEM_ARCHITECTURE.md).
2. [Caso de uso conversacional](jurisprudence/CHAT_JURISPRUDENCE_USE_CASE.md).
3. [Comparación de estrategias del chat](jurisprudence/CHAT_RETRIEVAL_STRATEGY_COMPARISON.md).
4. [Smoke pagado de la V1 Netlify-only](experiments/CHAT_NETLIFY_V1_PAID_SMOKE.md)
   y [resultados históricos de F0.2](experiments/CHAT_STRATEGY_F02_RESULTS.md).
5. [Roadmap del modelo de datos v3](jurisprudence/JURISPRUDENCE_DATA_V3_ROADMAP.md).
6. [Pipeline del caso canónico](jurisprudence/JURISPRUDENCE_CASE_PIPELINE.md).
7. [Schema v3](jurisprudence/JURISPRUDENCE_CASE_SCHEMA_V3.md).
8. [Recuperación de fase D](jurisprudence/JURISPRUDENCE_RETRIEVAL_PHASE_D.md) y
   [estado y resultados de fases E0/E](jurisprudence/JURISPRUDENCE_PHASE_E0.md).

Documentos especializados:

- [Verificación de citas](jurisprudence/CITATION_VERIFICATION.md).
- [Corpus verbatim](jurisprudence/VERBATIM_CORPUS.md).
- [Pipeline OKF](jurisprudence/OKF_PIPELINE.md) y
  [contrato Markdown OKF](jurisprudence/OKF_MARKDOWN_CONTRACT.md).
- [Catálogo de preguntas](jurisprudence/CHAT_USER_QUESTION_CATALOG.md).
- [Derivados del caso v3](jurisprudence/JURISPRUDENCE_DERIVATIVES_B4.md).
- [Baseline de la muestra de cinco](jurisprudence/JURISPRUDENCE_SAMPLE_PHASE_C.md).
- Evaluación ciega F0.3:
  [protocolo jurídico](experiments/CHAT_STRATEGY_F03_LEGAL_REVIEW_PROTOCOL.md),
  [rúbrica](experiments/CHAT_STRATEGY_F03_RUBRIC.md),
  [paquete](experiments/CHAT_STRATEGY_F03_BLIND_REVIEW.md) y
  [plantilla](experiments/CHAT_STRATEGY_F03_REVIEW_FORM_TEMPLATE.md).
- [Propuesta aislada y no aplicada sobre ausencias esporádicas](experiments/CHAT_DATA_GAP_ABSENCES.md).
- [Smoke pagado de la V1 Netlify-only](experiments/CHAT_NETLIFY_V1_PAID_SMOKE.md).

## Normativa, producto y operación

| Área | Documentos |
|---|---|
| Corpus normativo | [XML del BOE → preceptos](normativa/NORMATIVA.md) |
| Producto | [Arquitectura internacional y posts de sentencias](product/INTERNATIONAL_ARCHITECTURE.md), [páginas de país](product/COUNTRY_PAGES.md), [analítica](product/ANALYTICS.md), [auditoría SEO](product/SEO_AUDIT.md) |
| Modelos | [Paquete `llm_gateway`](development/LLM_GATEWAY.md), [reasoning effort](development/REASONING_EFFORT.md) |
| Infraestructura | [Despliegue del chat](operations/CHAT_DEPLOYMENT.md), [persistencia Supabase](operations/SUPABASE_CHAT.md), [observabilidad del chat](operations/CHAT_OBSERVABILITY.md), [autofix de Sentry](operations/AUTOFIX.md), [backups](operations/BACKUPS.md), [Netlify](operations/NETLIFY.md), [Netlify Edge](operations/NETLIFY_EDGE.md), [Cloudflare](operations/CLOUDFLARE.md), [UptimeRobot](operations/UPTIMEROBOT.md), [informe semanal de tráfico](operations/WEEKLY_TRAFFIC_REPORT.md), [diseño histórico del backend del chat](development/CHAT_BACKEND_DESIGN.md) |
| Identidad | [Guía de marca](brand/brand-guidelines.md), [manifiesto](brand/manifiesto.md) |
| Privacidad y legal | [Marco legal del sitio y decisiones](operations/PRIVACY_AND_LEGAL.md) |
| Evidencia experimental | [`experiments/`](experiments/) |

## Convenciones

- Los nombres de ruta se escriben desde la raíz del repositorio, por ejemplo
  `src/export_jurisprudence_case.py`.
- Los documentos jurídicos originales viven en `sentencias/` y `normativa/`;
  no se modifican durante una actualización de documentación.
- Los resultados regenerables viven en `knowledge/` o `output/`, según estén
  versionados o sean locales.
- Un cambio de contrato debe actualizar el código, su schema en `schemas/`, sus
  tests y el documento de referencia correspondiente.
- `project/TASKS.md` registra estado y bloqueos; no redefine contratos.
- Los planes históricos se conservan como contexto y deben señalar qué partes
  hayan quedado superadas.
