# Entregas de la migración del chat a Alfredo

Este registro acompaña a `CHAT_ALFREDO_MIGRATION_PLAN.md`. Describe lo que está
implementado en el repositorio, no lo que está desplegado.

| Entrega | Implementado aquí | Estado operativo |
|---|---|---|
| Contrato | `src/api/chat.py`, `src/chat_strategy_models.py`, `schemas/chat-protocol-2.fixtures.json` verificado contra los dos serializadores | Local/CI |
| HMAC y canary | `src/api/chat_security.py`, `frontend/netlify/prototypes/chat-fastapi-edge-v2.ts` con `CHAT_BACKEND_PERCENT` | Preview pendiente |
| Runtime A/B | composition root existente + ejecución concurrente + retry B acotado | No promovido |
| Evidencia de A | `structured-claims-v4` con gate léxico por afirmación y gate de autoridad judicial | Local/CI |
| Prompts | `structured-claims-v4` y `file-search-authority-v8` portados literales, con pistas terminológicas y filtro por sentencia | Local/CI |
| Esquema estricto | `tests/test_chat_schema_strict_mode.py` offline + `make smoke-chat-schema` con doble confirmación | Smoke real ejecutado |
| Stream largo | `scripts/chat_stream_spike.py` | Gate F0 sin medir |
| Persistencia | `src/api/chat_persistence.py` sobre RPC vigentes | Requiere rol privado |
| Artefacto | `chat_runtime_artifact.py`, `make build-chat-runtime-artifact` | Verificable localmente |
| Salud | `/health/live`, `/health/ready` | Monitor pendiente |
| Privacidad/canary | ADR y gates documentados | Bloqueante antes de usuarios |

## Smoke real del 4 de agosto de 2026

Cinco llamadas de pago validaron el runtime portado antes de cualquier preview.
No se registran preguntas ni respuestas de usuarios: las consultas fueron
sintéticas y de banco.

| Comprobación | Resultado |
|---|---|
| `structured-claims-v4` contra el modo estricto real | acepta el array de claims anidado |
| Índices por afirmación | cada claim cita solo sus fuentes, nunca todas |
| Gate de relevancia literal | retiró una afirmación y degradó el estado a `parcial` |
| Gate de autoridad judicial | detecta el órgano, lo declara y degrada el estado |
| Filtro de File Search | `authority=` y `judgment_id=` devuelven resultados |
| Verificación de citas de B | 12 candidatas, 3 literales publicadas |
| Coste | `ACTUAL` con importe y tokens; `ESTIMATED` cuando el proveedor no desglosa |
| Regresión de gimnasio | `san-2347-2022`, página 7, en la respuesta |

El smoke destapó dos huecos del port que estaban abiertos y ya están cerrados:
la tabla de sinónimos léxicos y la expansión de términos al elegir anclajes. Sin
ellas la recuperación no alcanzaba la sentencia declarada en el plan y el
redactor se abstenía por falta de extracto.

Ninguna variable pública del frontend contiene un secreto. El inventario del
host, las rutas reales, DNS, grants, unidades systemd y valores de entorno
permanecen fuera de Git.
