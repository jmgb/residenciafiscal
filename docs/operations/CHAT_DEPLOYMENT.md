# Despliegue del chat comparativo

**Estado:** la V1 Netlify-only y su persistencia Supabase están implementadas y
desplegadas en producción. El proyecto remoto, las migraciones, RLS, RPC
transaccionales y una consulta A/B productiva están verificados. El endpoint conserva
los cierres independientes `CHAT_COMPARISON_ENABLED` y `VITE_CHAT_MODE`; siguen
pendientes los requisitos legales indicados en `TASKS.md`. El recorrido Edge →
FastAPI se conserva como alternativa futura fuera del camino `/api/chat`.
**Fecha de corte:** 2026-08-01.

Este runbook explica la V1 Netlify-only y conserva, en una sección separada, el
comparador Python futuro. El rollout técnico a 106 está autorizado y conectado;
no sustituye los gates de revisión jurídica de
[`TASKS.md`](../project/TASKS.md).

## Decisión de runtime para la V1

La primera versión se desplegará íntegramente en una **Netlify Function
estándar**. No dependerá de un servidor Python ni de otro origen:

```text
React
  POST /api/chat
        │
        ▼
Netlify Function TypeScript
  validación + cuota + protocolo SSE 2
        │
        ├── A: corpus v3 + redactor LLM ──────────┐
        └── B: Gemini File Search sobre los PDF ──┤ en paralelo
                                                  ▼
                                      dos respuestas independientes
                                                  │
                                                  ▼
                         Supabase: pregunta + A/B + citas + coste
```

Restricciones deliberadas de la V1:

- A y B empiezan en paralelo y no comparten resultados ni contexto;
- la presentación sigue siendo A → B, aunque B termine antes;
- el deadline interno debe dejar margen al límite no configurable de 60 s de
  Netlify; objetivo inicial: terminar o cancelar antes de 50–55 s;
- A mantendrá Luna con esfuerzo `high` durante la primera observación en uso;
  se medirán durante varios días latencia total, percentiles, timeouts, tokens,
  coste y calidad antes de decidir si existe motivo para bajar el esfuerzo;
- ningún reintento puede prolongar la petición más allá del deadline global;
- si una estrategia falla o agota su tiempo, la otra respuesta se conserva;
- Python sigue preparando y validando el corpus fuera de línea, pero no
  participa en la petición del usuario.

La Function espera a las dos estrategias o a su deadline y después devuelve un
cuerpo **bufferizado** con sintaxis SSE. No usa streaming real de Netlify: una
Function que transmite la respuesta tiene un límite menor que la ejecución
sincrónica estándar y no sirve para este presupuesto de latencia. El parser del
navegador conserva el protocolo 2 sin depender de ese detalle de transporte.

## Arquitectura conservada para una evolución futura

El siguiente diseño ya existe en el repositorio y **no se borra**. Puede volver
a ser preferible si la evaluación demuestra que el chat necesita llamadas de
más de 60 s, reintentos largos, procesos pesados, almacenamiento local
persistente o mayor control operativo del runtime:

```text
React
  POST /api/chat
        │
        ▼
Netlify Edge Function
  rate limit por IP + secreto interno + proxy de stream
        │
        ▼
FastAPI POST /chat
  validación + protocolo SSE 2
        │
        ▼
comparador Python
  A: corpus v3 + neutral-llm-gateway (Luna + high)
  B: Gemini File Search sobre los PDF
        │
        ▼
dos respuestas independientes
  texto + citas verificadas + límites + coste USD
```

En esta alternativa, Netlify no ejecuta el dominio Python. La Edge Function es una fachada fina:
no recupera sentencias, no redacta, no calcula precios y no recibe claves de
OpenAI o Gemini. FastAPI conserva el composition root porque ahí viven el
corpus v3, la verificación literal, el gateway compartido y File Search.

Se usa **Edge Function**, no Function estándar. El spike real del repositorio
demostró streaming de 19,87 segundos en Edge y documentó los límites en
[`NETLIFY_EDGE.md`](NETLIFY_EDGE.md). FastAPI devuelve las cabeceras SSE antes
de ejecutar la comparación; hoy las respuestas de cada proveedor son
terminales, por lo que los eventos de cada bloque se emiten al terminar A y B,
no token a token desde el proveedor.

## Componentes implementados

| Capa | Ruta | Responsabilidad |
|---|---|---|
| Selector | `frontend/src/lib/chat-engine.ts` | `stub` seguro por defecto; `live` solo con `VITE_CHAT_MODE=live` |
| Cliente | `frontend/src/lib/chat-engine.live.ts` | POST same-origin, validación HTTP y protocolo |
| Parser | `frontend/src/lib/chat-sse-protocol.ts` | Estado A → B, costes decimales y terminal estricto |
| UI | `frontend/src/components/chat/ChatComparisonAnswers.tsx` | Dos columnas/pestañas para A/B; una columna si solo hay una respuesta; fuentes, límites, coste y voto ciego |
| Function V1 | `frontend/netlify/functions/chat/chat.ts` | Entrada, rate limit, registro y protocolo bufferizado |
| Runtime A/B | `frontend/netlify/functions/chat/` | Recuperación, proveedores en paralelo, verificación, coste y aislamiento |
| Persistencia | `frontend/netlify/functions/chat/supabase-chat-store.ts` | Registro de consulta, coste y serialización de mensajes A/B |
| Migraciones | `supabase/migrations/` | Tablas privadas de conversaciones, peticiones y mensajes; RPC atómicas |
| Proxy futuro | `frontend/netlify/prototypes/chat-fastapi-edge.ts` | Prototipo FastAPI fuera del camino productivo |
| HTTP Python | `src/api/chat.py` | Entrada acotada, autenticación y serialización SSE |
| Runtime | `src/api/chat_runtime.py` | Construcción perezosa de A, B, corpus, store y logs |

## Variables de la V1 Netlify-only

Ninguna credencial de backend lleva prefijo `VITE_`. El objetivo es darles
alcance **Functions**, pero la cuenta Netlify Legacy no permite scopes
específicos. En la configuración productiva vigente se guardan como variables
ordinarias del contexto `production` y todos los scopes. Vite solo expone las
variables `VITE_*`, por lo que no llegan al bundle; sí pueden leerlas los
administradores y procesos de build autorizados en Netlify. Si se contrata Pro,
convertirlas a secretos Functions y rotarlas.

| Variable | Uso |
|---|---|
| `CHAT_COMPARISON_ENABLED` | Debe ser exactamente `true`; cualquier otro valor cierra el endpoint |
| `OPENAI_API_KEY` | Redactor Luna `gpt-5.6-luna`, esfuerzo `high` |
| `GEMINI_API_KEY` | Gemini File Search |
| `CHAT_FILE_SEARCH_STORE_NAME` | Nombre remoto `fileSearchStores/...` del rollout de 106 PDF; la versión con autoridad explícita es `fileSearchStores/residenciafiscalrollout106a-zwmb28labwje` |
| `CHAT_FILE_SEARCH_MODEL` | `gemini-3.5-flash-lite` por defecto; allowlist cerrada |
| `CHAT_DEADLINE_MS` | `52000` por defecto; la Function rechaza valores mayores de `55000` |
| `SUPABASE_URL` | URL del proyecto Supabase; solo backend |
| `SUPABASE_SECRET_KEY` | Clave secreta de servidor; sin ella el endpoint falla cerrado |
| `VITE_CHAT_MODE` | Alcance Builds: `live` conecta el cliente; cualquier otro valor usa el stub |
| `VITE_CHAT_SESSION_MESSAGE_LIMIT` | Límite blando del navegador por ventana móvil de 24 h; `10` por defecto |

La clave publicable, `SUPABASE_ACCESS_TOKEN`, `SUPABASE_REF` y
`SUPABASE_DB_PASSWORD` no pertenecen al runtime. El contrato de almacenamiento,
campos y permisos está en [`SUPABASE_CHAT.md`](SUPABASE_CHAT.md).

El precio TypeScript no es una tabla mantenida a mano. Se exporta del catálogo
de `neutral-llm-gateway` con:

```bash
PYTHONPATH=src uv run python -m netlify_chat_pricing_catalog
PYTHONPATH=src uv run pytest -q tests/test_netlify_chat_pricing_catalog.py
```

El límite de mensajes es deliberadamente blando y se aplica en el navegador con
`localStorage`: permite diez mensajes por defecto en una ventana móvil de 24
horas. Es una barrera de abuso y experiencia, no una garantía económica ni una
cuota fuerte por identidad. El rate limit server-side de cinco peticiones por IP
y minuto sigue siendo la protección técnica inmediata del endpoint. El coste
real observado se guarda por petición para control operativo, sin bloquear por
un presupuesto monetario global.

La entrada de A está acotada antes de llamar al proveedor: 500 caracteres de
pregunta, 4 KiB como máximo por sentencia y 48 KiB para instrucciones, pregunta
y contexto completos. El empaquetador descarta campos estructurados enteros por
prioridad; nunca corta una cita literal. Luna conserva `high`, pero su salida
total está limitada a 4.000 tokens. El techo anterior de 1.200 truncó el JSON
en una llamada real porque incluye los tokens de razonamiento; 4.000 conserva
margen sin volver al valor abierto de 6.000. Gemini File Search tiene un techo
independiente de 2.000 tokens de salida.

Cuando la consulta pide expresamente Tribunal Supremo o Audiencia Nacional, las
dos estrategias restringen la recuperación a autoridad directa. A filtra el
corpus estructurado por la autoridad derivada del prefijo canónico `sts-` /
`san-`; B usa igualdad exacta en `metadata_filter` sobre el campo cerrado
`authority`. No usar `judgment_id="sts-*"` ni `judgment_id="san-*"`: una llamada
real confirmó que el comodín devolvía cero resultados aun existiendo documentos.
Una cita de otro órgano que reproduzca doctrina ajena no se trata como autoridad
directa: la respuesta completa se degrada a parcial y declara el límite. El
filtro por una resolución identificada de forma exacta sigue teniendo prioridad
sobre el filtro general de tribunal.

El store con `authority` se preparó y verificó con 106/106 PDF. Su activación es
atómica a nivel de despliegue: publicar primero el código que usa igualdad exacta
y configurar en ese mismo despliegue
`CHAT_FILE_SEARCH_STORE_NAME=fileSearchStores/residenciafiscalrollout106a-zwmb28labwje`.
El store anterior se conserva durante la observación inicial para rollback.

## Despliegue seguro de la V1

1. Confirmar que `supabase migration list --linked` muestra las migraciones
   locales y remotas, y que ambos advisors terminan sin incidencias.
2. Configurar `SUPABASE_URL`, `SUPABASE_SECRET_KEY` y las variables de proveedor
   como secretos de Functions si el plan lo permite. En el plan Legacy aplicar
   la excepción documentada de variables ordinarias para el contexto
   `production`. Empezar con `CHAT_COMPARISON_ENABLED=false` y
   `VITE_CHAT_MODE=stub`.
3. Desplegar y comprobar que `POST /api/chat` responde `503` y que no se realiza
   ninguna llamada de proveedor.
4. En **Deploy Preview**, configurar `VITE_CHAT_MODE=live`,
   `VITE_CHAT_SESSION_MESSAGE_LIMIT=10` y `CHAT_COMPARISON_ENABLED=true`.
5. Hacer una sola consulta del banco con autorización de coste. Comprobar dos
   respuestas A → B, citas verificadas, tokens/coste visibles, duración menor de
   60 s, tres filas en `private.chat_messages` y una petición registrada.
6. Cuadrar tokens y coste con los paneles de OpenAI y Gemini; probar después
   timeout, fallo aislado, límite por IP y límite blando de sesión.
7. Volver a ambos cierres. Activar Production exige completar privacidad,
   observar Luna `high` durante varios días y una autorización explícita.

La activación productiva fue autorizada expresamente el 31 de julio de 2026. El
smoke real devolvió A y B en paralelo en 20,23 s, con costes respectivos de
0,002849 USD (`ACTUAL`) y 0,001693 USD (`ESTIMATED`). La activación técnica no
cierra por sí sola las tareas legales y de retención de `TASKS.md`.

El protocolo conceptual y las reglas de independencia siguen en
[`CHAT_RETRIEVAL_STRATEGY_COMPARISON.md`](../jurisprudence/CHAT_RETRIEVAL_STRATEGY_COMPARISON.md).
La primera medición local real, los dos fallos de adaptador que descubrió y la
comparación provisional de calidad, latencia y coste están en
[`CHAT_NETLIFY_V1_PAID_SMOKE.md`](../experiments/CHAT_NETLIFY_V1_PAID_SMOKE.md).

## Variables de la arquitectura futura Edge → FastAPI

### Servicio Python

| Variable | Obligatoria al activar | Uso |
|---|---:|---|
| `CHAT_COMPARISON_ENABLED` | sí | Debe ser exactamente `true`; en otro caso `/chat` responde `503` |
| `CHAT_PROXY_SECRET` | sí | Secreto aleatorio largo compartido solo con Netlify |
| `OPENAI_API_KEY` | sí para Luna | Credencial de la estrategia A mediante el gateway |
| `GEMINI_API_KEY` | sí | Credencial de File Search B |
| `CHAT_FILE_SEARCH_MODEL` | no | Por defecto `gemini-3.5-flash-lite`; debe estar en la lista permitida |
| `CHAT_RETRIEVAL_CORPUS` | no | Corpus v3; usa la ruta versionada por defecto |
| `CHAT_FILE_SEARCH_STORE_STATE` | no | Recibo local del store; por defecto `output/file-search/rollout-106-store.json` |
| `CHAT_COMPARISON_OUTPUT_DIR` | no | Informes por `request_id`; conviene un volumen persistente |
| `CHAT_COMPARISON_LOG` | no | JSONL sin consulta ni respuesta; conviene un volumen persistente |

El servicio necesita además los 106 `*.pages.json` de
`knowledge/jurisprudencia-v3/verbatim/`. Falla cerrado si falta el corpus, el
recibo del store, una credencial, un verbatim necesario o si los IDs del corpus
y del store no coinciden exactamente.

### Netlify

Configurar con alcance **Functions**:

- `CHAT_BACKEND_URL`: origen HTTPS del servicio FastAPI, sin `/chat`;
- `CHAT_PROXY_SECRET`: exactamente el mismo secreto del backend.

Configurar con alcance **Builds**:

- `VITE_CHAT_MODE=stub` para producción mientras no haya autorización;
- `VITE_CHAT_MODE=live` únicamente en el contexto de Deploy Preview durante la
  integración. Una variable `VITE_*` es pública: nunca contiene secretos.

Las claves de proveedores se quedan en el servicio Python. La Edge Function no
las necesita.

## Despliegue seguro de la arquitectura futura

Estos pasos quedan conservados para una reevaluación posterior; no son el
procedimiento de despliegue de la V1 Netlify-only.

1. Desplegar FastAPI en un runtime Python 3.13 con `CHAT_COMPARISON_ENABLED=false`.
2. Verificar `/health` y que `POST /chat` devuelve `503`; no se incurre en coste.
3. Montar los 106 artefactos verbatim y un almacenamiento persistente para
   informes y logs. Confirmar que el File Search Store sigue existiendo y que
   sus IDs coinciden exactamente con el corpus.
4. Configurar credenciales y el secreto en el backend; configurar URL y el
   mismo secreto en Netlify con alcance Functions.
5. Habilitar el backend y desplegar un **Deploy Preview** con
   `VITE_CHAT_MODE=live`. No cambiar todavía el contexto Production.
6. Enviar una única pregunta del banco. Deben aparecer, en orden, «Corpus
   estructurado» y «Gemini File Search», cada uno con estado, fuentes propias y
   coste USD. El JSONL debe contener dos registros con el mismo `request_id` y
   no debe contener la pregunta ni la respuesta.
7. Probar error aislado de una estrategia, `429`, cancelación y rollback.
8. Volver a `stub` hasta cerrar los gates de producto. La puesta en producción
   exige una decisión explícita separada.

## Seguridad, privacidad y coste

- La Function limita a cinco peticiones por IP y minuto y registra la consulta
  antes de llamar a los proveedores. Si Supabase no está disponible, no se llama
  a ningún proveedor.
- El navegador aplica un límite blando configurable mediante
  `VITE_CHAT_SESSION_MESSAGE_LIMIT`: diez mensajes por ventana móvil de 24 horas
  por defecto. No sustituye una futura cuota fuerte por usuario autenticado.
- El navegador envía un identificador aleatorio de conversación, la
  jurisdicción y solo `id`, `role` y `content` de la última pregunta. El backend
  no recibe el resto del historial local.
- El historial es por ahora visual, no contexto de inferencia: una pregunta
  como «¿y en ese caso?» debe reformularse de forma autosuficiente. Incorporar
  contexto multi-turn exige un contrato de privacidad y grounding separado;
  no se resuelve reenviando todo el historial por defecto.
- Sentry elimina cuerpo, cabeceras y variables locales. Supabase guarda la
  pregunta aceptada y una respuesta por estrategia con modelo, tokens, coste,
  duración, citas y límites; no guarda IP, user-agent, cookies ni diagnósticos
  brutos del proveedor.
- La V1 no persiste diagnósticos brutos del proveedor. El contrato SSE sustituye
  los límites de una estrategia en `error` por un mensaje genérico y nunca
  expone excepciones al navegador.
- El coste visible es marginal por estrategia y no incluye preparar el corpus.
- El modo live no debe activarse en Production hasta validar la migración y la
  concurrencia en Deploy Preview. Rate limit, bandera y límite blando de sesión
  son capas independientes.

## Rollback de la arquitectura futura

1. Poner `VITE_CHAT_MODE=stub` en Netlify y redesplegar.
2. Poner `CHAT_COMPARISON_ENABLED=false` en el backend.
3. Conservar informes y logs para reconciliar llamadas ya iniciadas.

Ambas barreras son independientes: si una configuración queda rezagada, la
otra mantiene cerrado el gasto.
