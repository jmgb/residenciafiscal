# Entregas de la migración del chat a Alfredo

Este registro acompaña a `CHAT_ALFREDO_MIGRATION_PLAN.md`. Describe lo que está
implementado en el repositorio, no lo que está desplegado.

| Entrega | Implementado aquí | Estado operativo |
|---|---|---|
| Contrato | `src/api/chat.py`, `src/chat_strategy_models.py`, `schemas/chat-protocol-2.fixtures.json` verificado contra los dos serializadores | Local/CI |
| HMAC y canary | `src/api/chat_security.py`, `frontend/netlify/prototypes/chat-fastapi-edge-v2.ts` con `CHAT_BACKEND_PERCENT` | Preview pendiente |
| Runtime A/B | composition root existente + ejecución concurrente + retry B acotado | No promovido |
| Evidencia de A | `structured-claims-v4` con gate léxico por afirmación y gate de autoridad judicial | Local/CI |
| Persistencia | `src/api/chat_persistence.py` sobre RPC vigentes | Requiere rol privado |
| Artefacto | `chat_runtime_artifact.py`, `make build-chat-runtime-artifact` | Verificable localmente |
| Salud | `/health/live`, `/health/ready` | Monitor pendiente |
| Privacidad/canary | ADR y gates documentados | Bloqueante antes de usuarios |

Ninguna variable pública del frontend contiene un secreto. El inventario del
host, las rutas reales, DNS, grants, unidades systemd y valores de entorno
permanecen fuera de Git.
