# Autofix de incidencias de producción

Residencia Fiscal usa el mismo control plane que Presupuestor para convertir
incidencias accionables de Sentry en fixes pequeños, verificados y publicados
mediante pull request. Está activo para los tres runtimes:

- `residencia-fiscal-backend`: API FastAPI.
- `residencia-fiscal-frontend`: SPA React.
- `residencia-fiscal-chat`: Netlify Function del chat.

## Nombres que no son equivalentes

Tres identificadores parecidos describen piezas distintas y no se deben usar
como sinónimos:

| Identificador | Sistema | Qué representa |
|---|---|---|
| `residencia-fiscal-chat` | Sentry/Autofix | La Netlify Function productiva |
| `residenciafiscal-chat` | Docker | El contenedor FastAPI cerrado de Alfredo |
| `residencia-fiscal-chat-backend` | Sentry/Autofix | El futuro proyecto del FastAPI de Alfredo; todavía no existe en Sentry |

La presencia del contenedor no mueve ni renombra el proyecto de la Function.
Cuando se active el FastAPI, su proyecto nuevo se asignará a Autofix Alfredo;
los tres proyectos actuales permanecen en Autofix Finanzas mientras sus
runtimes sigan fuera de Alfredo.

## Flujo

```text
Sentry
  → listener del control plane
  → cola persistente
  → filtro de ruido y de entorno
  → worktree aislado del repositorio
  → agente de código
  → test de regresión + validaciones relacionadas
  → pull request
  → gate de CI
  → merge y resolución de la issue
```

El listener y el runner viven fuera de este repositorio. Aquí son canónicos el
contrato [`.autofix.yml`](../../.autofix.yml), las reglas de desarrollo de
[`CLAUDE.md`](../../CLAUDE.md) y los workflows de CI.

## Cuándo se publica automáticamente

Un cambio de código solo puede llegar a `main` si incluye un test de regresión
y las validaciones relacionadas ejecutadas por el agente pasan. El runner
espera el veredicto de GitHub Actions: un check rojo deja el PR abierto con
`needs-human-review` y mantiene la issue de Sentry abierta. Un PR que solo añade
diagnóstico tampoco se mergea automáticamente.

Los eventos resueltos, no productivos, no accionables, duplicados o sin contexto
técnico se archivan sin lanzar un agente. Los arreglos nunca se escriben en un
checkout de despliegue ni despliegan directamente; se preparan en un worktree
temporal y el despliegue sigue dependiendo del flujo normal del repositorio.

### Límite actual del chat

El enrutado de `residencia-fiscal-chat` funciona, pero sus eventos sintéticos se
minimizan a propósito y no llevan stacktrace ni `culprit`. El filtro actual del
control plane los archiva como `skip_missing_stacktrace_and_culprit`, por lo que
«activo» significa hoy que Autofix recibe y clasifica la incidencia, no que
llegue a invocar al agente. El backlog exige hacer accionable el contrato
estructurado seguro sin enviar pregunta, respuesta, mensaje bruto del proveedor,
body, cabeceras ni cookies.

## Guardrails del repositorio

- No ejecutar tests marcados `manual_real_llm` ni comandos que gasten
  presupuesto de modelos.
- No relajar autenticación, límites de tamaño, allowlists ni privacidad de
  Sentry para hacer desaparecer un error.
- No añadir secrets a los workflows de CI.
- Mantener el diff limitado a la incidencia y usar `make fast-check` cuando el
  alcance del cambio lo permita.

## Verificación operativa

La suite local protege el contrato con:

```bash
uv run pytest -q tests/test_autofix_contract.py
```

Una incidencia que no llegue al runner debe revisarse en este orden: proyecto
presente en `.autofix.yml`, regla activa en Sentry, entrada del proyecto en el
registro del control plane, checkout dedicado actualizado y servicios del host
sanos. La observabilidad y el tratamiento de datos del runtime del chat se
documentan en [CHAT_OBSERVABILITY.md](CHAT_OBSERVABILITY.md).
