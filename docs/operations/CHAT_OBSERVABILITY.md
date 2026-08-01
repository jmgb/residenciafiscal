# Observabilidad del chat en producción

Cómo se vigila la Netlify Function del chat: qué se envía, qué **no** se envía y
qué hay que configurar para que funcione. Estado: implementado y verificado el
1 de agosto de 2026; pendiente de activar en Netlify y en el VPS.

## Dos canales, por naturaleza distinta

| Señal | Canal | Por qué |
|-------|-------|---------|
| Fallos (`chat_request_failed`) | Sentry, proyecto `residencia-fiscal-chat` | Agrupa, deduplica y alerta por tasa |
| Coste (`chat_cost_reconciled`) | Resumen diario a Telegram | No es un error; Sentry lo mide mal |
| Ambos, en crudo | Logs de Netlify | Siguen emitiéndose por consola, sin cambios |

Se descartó el **drenaje de logs de Netlify**: requiere plan Pro.

## Qué llega a Sentry, y qué no

La Function **no usa `@sentry/node`**, y es deliberado. El SDK captura
breadcrumbs de consola y contexto del runtime por defecto, y este runtime loguea
eventos estructurados por consola; desactivar cada captura automática es más
frágil que escribir el payload. `netlify/functions/chat/observability.ts`
construye el envelope con `fetch`, así que **lo que sale es exactamente lo que se
lee en `buildEnvelope`**.

Viaja: `failure_code`, `stage`, `status`, `request_id`, `error_name`, entorno y
fingerprint.

No viaja, nunca: la pregunta, la respuesta, el `message` de la excepción del
proveedor, cabeceras, cookies ni cuerpo de la petición. El motivo es concreto: un
error de OpenAI o Gemini puede traer el prompt incrustado, y una pregunta del
chat es dato fiscal. `error.name` se sanea contra `[A-Za-z][A-Za-z0-9_]{0,39}` y
cualquier otra cosa se descarta como `unknown`.

Tres decisiones que evitan un incidente:

- **`await` antes de responder.** En Lambda el contenedor se congela al devolver
  la `Response`; un envío sin esperar se pierde.
- **Sin tracing** (`tracesSampleRate` no existe aquí). El deadline es de 52 s y
  no se gasta en telemetría.
- **Fallo cerrado y aislado.** Sin `CHAT_SENTRY_ENABLED=true` y sin DSN válido no
  se envía nada, y todo el sink va en `try/catch`: Sentry caído no puede tumbar
  el chat, porque el fallo ya quedó en el log estructurado.

## Alertas: dos reglas, no una

Con el tráfico actual una alerta **solo** por tasa no saltaría nunca. Por eso hay
dos en `residencia-fiscal-chat`:

1. `Chat: fallo nuevo en la Function` — primer fallo y regresiones.
2. `Chat: tasa de fallos elevada` — 5 eventos en 1 hora.

## Resumen diario de gasto

`scripts/daily_chat_cost_telegram.py` lee la RPC `chat_daily_stats`, que devuelve
**solo** recuentos, sumas y percentiles: el script no consulta tablas, así que no
puede leer contenido aunque quiera. El día es natural español (`Europe/Madrid`),
no UTC.

```bash
python3 scripts/daily_chat_cost_telegram.py --day 2026-08-01 --dry-run
```

El umbral `CHAT_DAILY_COST_ALERT_USD` **solo destaca el mensaje**: el coste
observado es contabilidad, no control de admisión, y no gobierna ninguna cuota.

## Qué falta para activarlo

1. En Netlify, como **variables ordinarias del contexto `production` y todos los
   scopes**, y redeploy:
   - `CHAT_SENTRY_ENABLED=true`
   - `CHAT_SENTRY_DSN=<DSN del proyecto residencia-fiscal-chat>`

   No lleva scope Functions **porque la cuenta Netlify Legacy no permite scopes
   específicos**; es la misma restricción que ya documenta
   [`CHAT_DEPLOYMENT.md`](CHAT_DEPLOYMENT.md#variables-de-la-v1-netlify-only) para
   el resto de credenciales del backend. Aquí importa menos que en las demás: un
   DSN de Sentry **identifica** el proyecto, no autentica nada privilegiado, así
   que no es un secreto como `OPENAI_API_KEY`. Lo que sí es obligatorio es que
   **nunca lleve prefijo `VITE_`**: no por confidencialidad, sino porque es
   configuración de un runtime de servidor y no debe viajar al bundle.
2. En el VPS, instalar el timer diario con las units de `scripts/agentic/`:
   `residenciafiscal-daily-chat-cost-telegram.{service,timer}`.

## Verificación hecha

- Sentry devolvió `200` al envelope que produce el código de producción, y la
  issue aparece como `chat_request_failed: comparison_error (compare)`.
- El resumen diario leyó el ledger real: 2 consultas, `$0,006482`, y dejó a la
  vista el `ESTIMATED` de Gemini ya documentado en
  [`TASKS.md`](../project/TASKS.md).
- Tests deterministas en `frontend/tests/netlify-chat-observability.test.ts` y
  `tests/test_daily_chat_cost_telegram.py`, incluido uno que hace fallar el
  handler real con una excepción que contiene la pregunta y comprueba que no
  aparece en el cuerpo enviado a Sentry.
