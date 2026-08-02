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
python3 scripts/daily_chat_cost_telegram.py --catch-up --dry-run
```

El umbral `CHAT_DAILY_COST_ALERT_USD` **solo destaca el mensaje**: el coste
observado es contabilidad, no control de admisión, y no gobierna ninguna cuota.

### Un día perdido no desaparece en silencio

El timer lo lanza el runner en modo `--catch-up`, no con el día suelto.
`Persistent=true` dispara la unit **una sola vez** al arrancar, así que una
máquina apagada tres días enviaría un resumen y perdería dos sin dejar rastro.

El estado es una línea con el último día resumido, en
`reports/daily_chat_cost_telegram/last_day.txt` —directorio ya ignorado por
git—. Un estado ausente o corrupto no bloquea el envío: se comporta como el
primer arranque y manda solo ayer, sin reconstruir la historia entera. Un reloj
adelantado tampoco inventa días.

La recuperación está acotada a `MAX_CATCH_UP_DAYS = 7` para que un apagón largo
no dispare decenas de mensajes; **lo que queda fuera se declara** en un aviso
propio con el rango omitido, porque el dato sigue en el ledger y se recupera con
`--day`. Callarlo sería el mismo fallo que se quiso evitar.

Ese tope fija el `TimeoutStartSec` de la unit: siete días, cada uno con su
timeout de RPC y de Telegram, más el aviso de omitidos, no caben en los 300 s
iniciales. Con `600` systemd ya no puede matar el job a mitad —lo que dejaría el
estado sin avanzar y sin salir la alerta de fallo—, y un test enlaza las tres
constantes para que subir `MAX_CATCH_UP_DAYS` sin tocar la unit ponga el gate en
rojo.

Un `last_sent` posterior a ayer es imposible y solo lo deja un reloj adelantado
durante una ejecución. **No se trata como «nada pendiente»**, porque eso dejaría
el resumen mudo hasta que el tiempo real alcanzase esa fecha: se considera
estado inválido, se manda ayer y se reescribe el estado al día real.

### Un fallo del timer no puede parecer silencio

Si el envío falla, el resumen simplemente no llega, y eso es indistinguible de
un día tranquilo. El runner captura el fallo y avisa por Telegram con
`--failure-alert`, usando **`python3` del sistema**: si lo que se ha roto es el
entorno, el aviso tiene que salir igual. Es el mismo patrón del informe semanal
de tráfico.

No se usa `OnFailure=agent-unit-failure-notify@`, la plantilla que sí emplean
otras units de la máquina: apunta al checkout y al `.env` de *presupuestor*, y
acoplaría la alerta de este proyecto a otro repositorio.

El aviso corta el detalle en 500 caracteres y nombra la unit y el `exit`, para
que el journal se consulte con un comando ya escrito.

## Activación (completada el 2 de agosto de 2026)

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
   Ambas están puestas en `production` desde el 2 de agosto de 2026.
2. Instalar el timer diario con las units de `scripts/agentic/`:
   `residenciafiscal-daily-chat-cost-telegram.{service,timer}`.

   **No va en el VPS `alfredo`, y es deliberado.** Allí viven los timers de
   *sistema* del backup y de la retención, cuyo `.env` solo tiene
   `SUPABASE_REF` y `SUPABASE_DB_PASSWORD` para `pg_dump`. El resumen diario
   llama a la RPC `chat_daily_stats` por HTTP y necesita `SUPABASE_URL` y
   `SUPABASE_SECRET_KEY`: llevarlo al VPS ampliaría la superficie de la clave de
   servicio sin ganar nada. Va como unit **de usuario en la máquina de
   informes**, junto a `residenciafiscal-weekly-ga4-telegram.timer`, que ya
   corre ahí y comparte `.env`, ruta y patrón.

   ```bash
   bash scripts/agentic/install-daily-chat-cost-telegram-timer.sh
   ```

   El instalador es idempotente y valida antes que el `.env` tiene las cuatro
   claves que el resumen necesita —`SUPABASE_URL`, `SUPABASE_SECRET_KEY`,
   `TELEGRAM_TOKEN` y `TELEGRAM_CHAT_ID`—, así que se relanza tras cada
   `git pull` que toque las units. Es el gemelo de
   `install-weekly-ga4-telegram-timer.sh`.

## Verificación hecha

- Sentry devolvió `200` al envelope que produce el código de producción, y la
  issue aparece como `chat_request_failed: comparison_error (compare)`.
- El resumen diario leyó el ledger real: 2 consultas, `$0,006482`, y dejó a la
  vista el `ESTIMATED` de Gemini ya documentado en
  [`TASKS.md`](../project/TASKS.md).
- El 2 de agosto de 2026, ya con el timer instalado, una ejecución real de
  `systemctl --user start residenciafiscal-daily-chat-cost-telegram.service`
  terminó en `Result=success` y entregó ese mismo resumen en Telegram. El
  siguiente disparo automático queda fijado a las 09:15.
- Ese mismo día, con la recuperación ya cableada: un `--catch-up` en seco con
  estado del 1 de junio recuperó los 7 días permitidos y declaró los 55
  omitidos; una ejecución real del service con el estado al día imprimió «Sin
  resúmenes pendientes» sin reenviar nada; y `--failure-alert` entregó su aviso
  en Telegram.
- Tests deterministas en `frontend/tests/netlify-chat-observability.test.ts` y
  `tests/test_daily_chat_cost_telegram.py`, incluido uno que hace fallar el
  handler real con una excepción que contiene la pregunta y comprueba que no
  aparece en el cuerpo enviado a Sentry.
