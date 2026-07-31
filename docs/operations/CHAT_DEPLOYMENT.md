# Despliegue del chat comparativo

**Estado:** la V1 Netlify-only está decidida pero todavía no implementada. El
recorrido Edge → FastAPI descrito más abajo está implementado y probado con
dobles de proveedor, pero deja de ser el objetivo de despliegue inicial y se
conserva como alternativa futura. Producción permanece cerrada en `stub`.
**Fecha de corte:** 2026-07-31.

Este runbook explica cómo se conecta el chat del navegador con el comparador
Python. No autoriza el rollout a las 106 sentencias ni sustituye los gates de
presupuesto y revisión jurídica de [`TASKS.md`](../project/TASKS.md).

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

El runbook operativo de esta V1 se completará a la vez que su Function y sus
tests. Hasta entonces no se deben reutilizar las variables o los pasos de
FastAPI como si describieran el deploy Netlify-only.

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
| UI | `frontend/src/components/chat/ChatComparisonAnswers.tsx` | Dos bloques separados, fuentes, límites y coste |
| Proxy | `frontend/netlify/edge-functions/chat.ts` | Rate limit, secreto interno y streaming sin inspeccionar texto |
| HTTP Python | `src/api/chat.py` | Entrada acotada, autenticación y serialización SSE |
| Runtime | `src/api/chat_runtime.py` | Construcción perezosa de A, B, corpus, store y logs |

El protocolo conceptual y las reglas de independencia siguen en
[`CHAT_RETRIEVAL_STRATEGY_COMPARISON.md`](../jurisprudence/CHAT_RETRIEVAL_STRATEGY_COMPARISON.md).

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
| `CHAT_FILE_SEARCH_STORE_STATE` | no | Recibo local del store; por defecto `output/file-search/f0-store.json` |
| `CHAT_COMPARISON_OUTPUT_DIR` | no | Informes por `request_id`; conviene un volumen persistente |
| `CHAT_COMPARISON_LOG` | no | JSONL sin consulta ni respuesta; conviene un volumen persistente |

El servicio necesita además los cinco `*.pages.json` de
`knowledge/jurisprudencia-v3/verbatim/`. Falla cerrado si falta el corpus, el
recibo del store, una credencial o un verbatim necesario.

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
3. Montar los artefactos de la muestra de cinco y un almacenamiento persistente
   para informes y logs. Confirmar que el File Search Store sigue existiendo.
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

- La Edge Function limita a cinco peticiones por IP y minuto. Este límite evita
  abuso básico, pero **no garantiza un techo global de gasto**.
- El backend exige el secreto cuando el chat está habilitado; así no se puede
  saltar el rate limit llamando directamente al origen.
- El navegador envía solo `role` y `content`; el backend usa únicamente la
  última pregunta de usuario para el comparador actual.
- El historial es por ahora visual, no contexto de inferencia: una pregunta
  como «¿y en ese caso?» debe reformularse de forma autosuficiente. Incorporar
  contexto multi-turn exige un contrato de privacidad y grounding separado;
  no se resuelve reenviando todo el historial por defecto.
- Sentry elimina cuerpo, cabeceras y variables locales. Los logs de estrategia
  guardan métricas, modelo y coste, nunca consulta ni respuesta.
- Los diagnósticos brutos de proveedor pueden conservarse en el informe interno,
  pero el contrato SSE sustituye los límites de una estrategia en `error` por
  un mensaje genérico; nunca expone excepciones al navegador.
- El coste visible es marginal por estrategia y no incluye preparar el corpus.
- El modo live no debe activarse hasta resolver la fase 0b. El rate limit por IP
  y la bandera de cierre son defensa en profundidad, no un presupuesto atómico.

## Rollback de la arquitectura futura

1. Poner `VITE_CHAT_MODE=stub` en Netlify y redesplegar.
2. Poner `CHAT_COMPARISON_ENABLED=false` en el backend.
3. Conservar informes y logs para reconciliar llamadas ya iniciadas.

Ambas barreras son independientes: si una configuración queda rezagada, la
otra mantiene cerrado el gasto.
