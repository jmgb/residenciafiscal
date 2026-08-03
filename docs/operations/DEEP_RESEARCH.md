# Investigación profunda con Codex

La investigación profunda es un job asíncrono separado del chat A/B. El
navegador inicia el trabajo y consulta su estado; Netlify no ejecuta Codex ni
recibe sus credenciales:

```text
React → Netlify /api/deep-research
     → POST /jobs firmado → Alfredo
     → runtime jurídico dentro del contenedor Codex
          → Codex + MCP local del corpus
          → verificador determinista del perfil
     → callback HMAC → Supabase privado → polling de React
```

El callback persiste el resultado y crea de forma idempotente un mensaje
`assistant`/`deep_research` en `private.chat_messages`. El frontend obtiene el
estado por polling; Alfredo no abre una conexión directa con el navegador.

## Contrato vigente

| Elemento | Valor |
|---|---|
| Perfil | `residenciafiscal-deep-research-v2` |
| Modelo | `gpt-5.6-luna` |
| Esfuerzo | `high` |
| Bundle | `rollout-106/2` |
| Borrador de Codex | `residenciafiscal-deep-research-draft/2` |
| Resultado confiable | `residenciafiscal-deep-research-output/2` |
| Fuentes | JSON local únicamente |

Frontend y Alfredo fijan y validan el modelo y el esfuerzo. Codex no puede
declarar esos metadatos: el runtime instalado del perfil los añade al resultado
después de ejecutar y verificar el borrador. Latencia y coste se calculan
también fuera del modelo. Las tarifas y su `pricing_version` se generan desde el
catálogo versionado de `llm_gateway` y viajan dentro del bundle; el runtime no
mantiene ninguna tabla de precios propia. Si no hay uso medible, el coste queda
`UNAVAILABLE`, nunca como cero.

## Corpus y herramientas

El bundle v2 no contiene PDF ni Markdown duplicados. Conserva únicamente:

- `retrieval/rollout-106.corpus.json`, índice para encontrar candidatos;
- `cases/*.case.json`, representación estructurada de cada sentencia;
- `verbatim/*.pages.json`, texto canónico por página para las citas;
- `metadata/model-pricing.json`, tarifa y versión derivadas del catálogo común;
- índices JSON auxiliares de cuestiones y jurisdicción, no expuestos como
  acceso genérico al agente.

Esto reduce el ZIP aproximadamente de 19 MB a 3 MB y evita que el modelo lea la
misma sentencia en tres formatos. El PDF original se usa al construir el bundle
para comprobar su SHA-256, pero no se incluye ni se ofrece a Codex.

Codex solo ve un servidor MCP local con tres herramientas de lectura:

1. `corpus.search_corpus(query, limit)` busca en el índice y devuelve candidatos
   acotados, no el texto completo.
2. `corpus.read_case(judgment_id)` abre el JSON estructurado de un candidato.
3. `corpus.read_verbatim_page(judgment_id, page)` devuelve el `raw_page_text`,
   número de página y SHA-256 necesarios para una cita exacta.

No existe una herramienta de lectura arbitraria de rutas. Los identificadores
y las rutas se validan contra allowlists y permanecen dentro del bundle
inmutable y de solo lectura.

## Prevención de alucinaciones

La pregunta llega por `stdin` como JSON de datos no confiables, separada de la
instrucción de desarrollador. La instrucción obliga a buscar, leer y comprobar
la página verbatim, limita la selección a cinco sentencias y permite responder
de forma parcial, pedir precisión o abstenerse si el corpus no basta.

La salida estructurada de Codex es solo un borrador. Antes de devolver el
resultado a Alfredo, el runtime jurídico del contenedor comprueba de forma
determinista:

- que solo se hayan usado las tres herramientas MCP permitidas;
- que una respuesta sustantiva haya buscado el corpus y leído páginas verbatim;
- que cada afirmación tenga evidencias y no existan evidencias huérfanas;
- que cada sentencia, página y SHA-256 existan en el bundle;
- que `document_id` y SHA-256 coincidan también con el manifiesto canónico del
  rollout, no solo con el propio JSON verbatim;
- que `text_sha256` de cada página y `pages_sha256` del documento coincidan con
  el contenido JSON exacto; esta misma validación bloquea también la creación
  del bundle si un artefacto verbatim fue editado o truncado;
- que cada cita sea una subcadena literal de `raw_page_text`, sin normalizar,
  corregir, unir ni completar texto;
- que una cita contenga al menos 20 caracteres sustantivos y que cada
  `claim.text` sea exactamente la cita de su primera evidencia;
- que no se usen más de cinco sentencias.

Además, el texto que ve el usuario no se toma del canal libre `text` del
borrador: se reconstruye exclusivamente, y en orden, a partir de pasajes
literales del corpus. V2 es deliberadamente extractiva: Codex selecciona los
fragmentos relevantes, pero no publica una paráfrasis jurídica que un
verificador determinista no pueda validar semánticamente. `limits` tampoco se
publica desde el borrador: queda vacío o se sustituye por el aviso fijo de
resultado parcial. Para `pregunta`, `abstención` y `error`, el texto libre del
modelo se descarta y se usa una plantilla fija sin contenido jurídico.

Un fallo invalida toda la ejecución: el runtime termina con error y Alfredo no
publica como respuesta jurídica el texto no verificable.

El wrapper consume el JSONL de Codex mientras se ejecuta y corta el proceso si
supera `12` turnos, `80` llamadas MCP, `12` sentencias distintas, `120` páginas
o `200000` microusd de coste cuando el proveedor reporta uso. El coste solo
puede comprobarse en el primer evento que incluya telemetría; los demás límites
se aplican durante las llamadas. El schema limita además claims, citas y texto
para que incluso una salida válida con Unicode extremo quepa en el callback de
250 kB. Una telemetría vacía, desconocida o con todos los contadores a cero se
marca `UNAVAILABLE`; nunca se muestra como coste estimado cero.

## Red y aislamiento

El modelo no dispone de herramientas de Internet: se deshabilitan web search,
navegador, apps, plugins, shell, ejecución unificada, computer use, generación
de imágenes y multiagente. El único servidor MCP es el proceso stdio local del
corpus, declarado de solo lectura y mundo cerrado.

El proceso padre de Codex sí necesita egress HTTPS para comunicarse con el
proveedor del modelo. Por eso `egress=provider-only` describe el contrato de
capacidades, no una afirmación de que el contenedor no tenga red física. La
frontera adicional es el contenedor dedicado: usuario sin privilegios, rootfs y
bundle de solo lectura, workspace tmpfs, capacidades eliminadas y sin Docker
socket. El agente no tiene una herramienta con la que aprovechar esa red para
navegar o consultar fuentes externas.

Codex se ejecuta con configuración efímera y sin configuración ni reglas del
usuario. Se deshabilita la herencia del entorno para shell; el MCP no solicita
variables de entorno ni secretos.

## Variables

En Netlify `production`, sin prefijo `VITE_` salvo la bandera de build:

| Variable | Valor |
|---|---|
| `DEEP_RESEARCH_ENABLED` | `true` después del gate operativo |
| `ALFREDO_JOBS_URL` | URL HTTPS de `/jobs` de Alfredo |
| `ALFREDO_HMAC_SECRET` | secreto compartido del contrato VA–Alfredo |
| `DEEP_RESEARCH_CALLBACK_URL` | `https://residenciafiscal.org/api/deep-research-callback` |
| `DEEP_RESEARCH_BUNDLE_ID` | `rollout-106/2` |
| `VITE_DEEP_RESEARCH_ENABLED` | `true` para mostrar la UI |

`SUPABASE_URL` y `SUPABASE_SECRET_KEY` son obligatorias porque las RPC de jobs
son privadas.

En Alfredo:

```text
ALFREDO_EXECUTE_JOBS=true
ALFREDO_CONTAINER_ROUTING_ENABLED=true
ALFREDO_DEEP_RESEARCH_ENABLED=true
ALFREDO_DEEP_RESEARCH_ISOLATION_ATTESTED=true
ALFREDO_TARGET_CODEX_CONTAINER=alfredo-codex-agent
ALFREDO_DEEP_RESEARCH_BUNDLE_ROOT=/opt/residenciafiscal/deep-research
ALFREDO_DEEP_RESEARCH_RUNNER_PATH=/opt/residenciafiscal/deep-research/runtime/current/deep_research_codex_runtime.py
```

## Preparación y despliegue

Construir y verificar el snapshot local:

```bash
make deep-research-bundle
make deep-research-bundle-verify
```

Transferir el bundle, el schema y los cuatro módulos allowlisted del perfil, sin
depender de ningún checkout para ejecutar jobs:

```bash
bash scripts/deploy_deep_research_bundle.sh
```

El instalador rechaza hashes incorrectos, entradas no declaradas, rutas
inseguras y la sobrescritura de un bundle distinto. Bundle, schema, wrapper,
MCP y verificador se instalan en el host bajo
`/opt/residenciafiscal/deep-research`; el contenedor los ve mediante bind mounts
de solo lectura. No se usa `docker cp`: el rootfs endurecido del contenedor es
también de solo lectura. Toda la instrucción jurídica y su QA viven en ese
runtime montado; el supervisor genérico de Alfredo se limita a validar el
contrato, transportar `stdin`/JSONL y realizar el callback.

Los cuatro módulos y su `output.schema.json` se copian primero a
`runtime/releases/<sha256>/`; el hash de la release cubre los cinco archivos.
Solo cuando la release está completa, el instalador cambia `runtime/current`
mediante rename atómico; ningún job nuevo puede combinar runtime y schema de
versiones distintas. Antes de activar una release, el instalador inspecciona
Docker y falla si el rootfs no es read-only o si el origen host exacto de
`runtime` no está montado en la misma ruta del contenedor con `RW=false`. Un
reintento valida también hashes y permisos `0555`/`0444` de la release existente.

El contenedor dedicado debe conservar estos dos mounts separados:

```text
/opt/residenciafiscal/deep-research/rollout-106 -> misma ruta (read-only)
/opt/residenciafiscal/deep-research/runtime     -> misma ruta (read-only)
```

Al recrearlo para añadir el segundo mount se mantiene el contenedor anterior,
parado y renombrado, hasta superar el smoke. El rollback consiste en detener el
nuevo, devolver al anterior su nombre original y reactivar el perfil v1; no se
borra el volumen de autenticación de Codex.

Después se despliega `app/` de Alfredo por su procedimiento habitual y se
verifica que el unit tenga las variables anteriores. La bandera de aislamiento
solo debe permanecer activa cuando el contenedor endurecido y los mounts hayan
sido comprobados.

## Estados, cancelación y persistencia

La UI muestra `En cola`, `Buscando en el corpus`, `Leyendo fuentes`,
`Verificando evidencias`, `Completada`, `Cancelada` o `Error`. La cancelación
remota cubre jobs aún en cola; un job ya reclamado devuelve conflicto y no se
marca falsamente como cancelado.

El callback valida HMAC, `job_id`, modelo, esfuerzo, versión y forma completa
del resultado. Luego actualiza el job y crea en la misma transacción la fila de
mensaje de asistente. La pregunta, el estado y la salida estructurada tienen la
retención definida por las RPC privadas; no se conserva razonamiento interno ni
cadena de pensamiento.

El callback acepta únicamente salidas v2. Una salida v1, aunque esté autenticada
y declare Luna + `high`, termina el job con error para impedir que un worker
obsoleto rebaje las garantías del verificador determinista. Los resultados v1
históricos ya persistidos siguen siendo legibles, pero no pueden volver a entrar
por el callback.

## Verificación operativa tras un cambio

1. Comprobar el manifiesto instalado: bundle `rollout-106/2`, formato
   `json-only` y hashes válidos.
2. Confirmar en Alfredo el perfil v2, `gpt-5.6-luna`, esfuerzo `high` y las tres
   herramientas exactas.
3. Lanzar un job que requiera una cita y revisar que el audit contenga
   `search_corpus` y `read_verbatim_page` completadas.
4. Confirmar callback HTTP 204, estado `completed`, resultado v2 y una fila
   `assistant`/`deep_research` en `private.chat_messages`.
5. Probar una cita alterada y comprobar que Alfredo falla cerrado sin publicar
   la respuesta.

El smoke histórico del 2026-08-03 validó el recorrido v1. No acredita por sí
solo esta versión v2: tras desplegarla debe repetirse el smoke anterior antes de
abrirla a tráfico general.
