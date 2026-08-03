# Investigación profunda C

La opción C es un job asíncrono separado de A/B. El navegador solo inicia el
trabajo y consulta su estado; Netlify no ejecuta Codex ni recibe credenciales de
Alfredo. El recorrido es:

```text
React → Netlify /api/deep-research
     → POST /jobs firmado → supervisor privado de Alfredo
     → Codex en el container dedicado
     → callback HMAC → Supabase privado → polling de React
```

La funcionalidad está cerrada por configuración hasta completar el piloto C2,
la comprobación de aislamiento y la decisión de promoción. C nunca entra en la
comparación síncrona ni retrasa A/B.

## Variables de Netlify

Configurar en `production`, sin prefijo `VITE_`, y redeployar:

| Variable | Valor |
|---|---|
| `DEEP_RESEARCH_ENABLED` | `true` solo después del gate operativo |
| `ALFREDO_JOBS_URL` | URL HTTPS de `/jobs` del supervisor de Alfredo |
| `ALFREDO_HMAC_SECRET` | El mismo secreto HMAC del contrato VA–Alfredo |
| `DEEP_RESEARCH_CALLBACK_URL` | `https://residenciafiscal.org/api/deep-research-callback` |
| `DEEP_RESEARCH_BUNDLE_ID` | ID exacto del manifiesto, por ejemplo `rollout-106/1` |

Además, configurar `VITE_DEEP_RESEARCH_ENABLED=true` como variable de build
para que el botón solo aparezca cuando el backend también está preparado.

`SUPABASE_URL` y `SUPABASE_SECRET_KEY` siguen siendo obligatorias porque las
RPC de jobs son backend-only. El callback valida la firma, el `job_id`, el
JSON Schema y la forma de cada evidencia antes de hacer visible el resultado.

## Preparar Alfredo

1. Desplegar `app/` del repositorio `pymechat-alfredo` con el commit que contiene
   el perfil `residenciafiscal-deep-research-v1`.
2. Aplicar el unit de Alfredo con:

   - `ALFREDO_EXECUTE_JOBS=true`
   - `ALFREDO_CONTAINER_ROUTING_ENABLED=true`
   - `ALFREDO_DEEP_RESEARCH_ENABLED=true`
   - `ALFREDO_DEEP_RESEARCH_ISOLATION_ATTESTED=true` solo después de verificar
     un contenedor dedicado sin root, rootfs de solo lectura, sin herramientas
     de agente y con egress del proveedor resuelto por el controlador/broker.
   - `ALFREDO_TARGET_CODEX_CONTAINER=alfredo-codex-agent`
   - `ALFREDO_DEEP_RESEARCH_BUNDLE_ROOT=/opt/residenciafiscal/deep-research`
   - `ALFREDO_DEEP_RESEARCH_SCHEMA_PATH=/opt/residenciafiscal/deep-research/output.schema.json`

3. Construir y verificar el bundle localmente:

   ```bash
   make deep-research-bundle
   make deep-research-bundle-verify
   ```

4. Transferirlo sin clonar el repositorio completo:

   ```bash
   bash scripts/deploy_deep_research_bundle.sh
   ```

El instalador rechaza hashes incorrectos, rutas inseguras y sobrescrituras. El
bundle se deja con directorios `0555` y archivos `0444`; el schema se copia al
container de Codex también como `0444`. La activación del flag del worker y la
transferencia son pasos separados para poder verificar primero el aislamiento.
La compuerta de attestation mantiene C cerrada aunque alguien active por error
solo las flags de ejecución o routing.

## Estados y cancelación

La UI muestra `En cola`, `Buscando en el corpus`, `Leyendo fuentes`,
`Verificando evidencias`, `Completada`, `Cancelada` o `Error`. La cancelación
remota cubre jobs todavía en cola; un job ya reclamado por el worker devuelve un
conflicto y no se marca falsamente como cancelado.

Cuando C nace desde una comparación A/B, el job conserva únicamente el `request_id` opaco de esa
comparación. Al completar C, el bloque de valoración ofrece A, B, C, empate o ambas insuficientes;
el mismo RPC ciego registra como máximo un voto y no declara una ganadora automáticamente.

El resultado no contiene razonamiento interno. Solo se persisten durante quince
días la pregunta, el estado y la salida estructurada; las RPC privadas incluyen
el purgado correspondiente.
