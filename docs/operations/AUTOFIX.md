# Autofix de incidencias de producción

Residencia Fiscal usa el mismo control plane que Presupuestor para convertir
incidencias accionables de Sentry en fixes pequeños, verificados y publicados
mediante pull request. Está activo para los tres runtimes:

- `residencia-fiscal-backend`: API FastAPI.
- `residencia-fiscal-frontend`: SPA React.
- `residencia-fiscal-chat`: Netlify Function del chat.

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
