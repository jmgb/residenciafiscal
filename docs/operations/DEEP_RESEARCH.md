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

La implementación está desplegada bajo una bandera explícita para un piloto
controlado. La promoción general sigue pendiente de completar C2, C3 y C6; C
nunca entra en la comparación síncrona ni retrasa A/B.

## Estado operativo (2026-08-03)

Las variables de C están activas en el `.env` local y en el contexto
`production` de Netlify. El secreto HMAC está configurado como secreto de
Netlify y coincide con el secreto del supervisor de Alfredo. El deploy de
producción incluye el frontend y las funciones de C.

La compuerta efectiva está abierta en Alfredo tras verificación operativa:
`ALFREDO_DEEP_RESEARCH_ISOLATION_ATTESTED=true`. El contenedor dedicado
`alfredo-codex-agent` ejecuta `codex-cli 0.146.0` con usuario 1000, rootfs de
solo lectura, sin Docker socket ni capacidades, límites de CPU/memoria/PIDs,
workspace efímero en tmpfs y únicamente el estado de Codex como volumen
persistentemente writable. El bundle y el schema se montan como solo lectura.

El smoke E2E del 2026-08-03 completó correctamente el recorrido completo con el
job `deep-7a2a8fc2-2cd3-44ac-9e3f-14206a6d3ea8`: estado `completed`, salida
`completa`, modelo `gpt-5-codex`, 5 afirmaciones, 7 evidencias y callback HMAC
reconciliado en Supabase. Es evidencia de integración operativa, no sustituye
la muestra de calidad C2 ni la evaluación comparativa C3. El coste de esa
ejecución quedó como no disponible y no se presenta como cero.

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
     el contenedor dedicado sin root, rootfs de solo lectura, sin herramientas
     de agente, bundle/schema read-only y egress HTTPS disponible para el
     proveedor autenticado de Codex.
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
En Alfredo, el sandbox `bwrap` interno de Codex no puede crear namespaces bajo
la política del VPS; por eso el runner usa
`--dangerously-bypass-approvals-and-sandbox` únicamente dentro del contenedor
Docker endurecido. El aislamiento efectivo lo proporcionan Docker, los mounts
read-only/tmpfs, el usuario sin privilegios y la ausencia de socket; la red
conserva salida porque Codex necesita contactar con su proveedor. El schema
declara `type` junto a cada `const` para ser compatible con la validación de
structured output de Codex 0.146.0.

La separación de red documentada para el piloto local (`bwrap` con red
deshabilitada) no es la frontera del runtime de Alfredo: allí el contenedor
Docker endurecido protege filesystem, capacidades, mounts y socket, mientras
conserva egress HTTPS para que Codex contacte con su proveedor autenticado.
Por tanto, la attestation confirma aislamiento del contenedor y del bundle,
pero no equivale a afirmar que el proceso Codex carezca de red de proveedor.

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
