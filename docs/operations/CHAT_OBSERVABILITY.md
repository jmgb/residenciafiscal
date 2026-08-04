# Observabilidad del chat en producción

Cómo se vigila la Netlify Function del chat: qué se envía, qué **no** se envía y
qué hay que configurar para que funcione. Estado: implementado y verificado el
1 de agosto de 2026; Sentry y el resumen del VPS están activos. El 3 de agosto
se reforzó el ledger privado porque los logs de Netlify no bastan por sí solos
para reconstruir el experimento A/B.

## Dos canales, por naturaleza distinta

| Señal | Canal | Por qué |
|-------|-------|---------|
| Fallos (`chat_request_failed`) | Sentry, proyecto `residencia-fiscal-chat` | Agrupa, deduplica y alerta por tasa |
| Fallos aislados (`chat_strategy_failed`) | Sentry, proyecto `residencia-fiscal-chat` | Avisa aunque la otra estrategia permita completar la petición |
| Coste (`chat_cost_reconciled`) | Resumen diario a Telegram | No es un error; Sentry lo mide mal |
| Eventos operativos, best effort | Logs de Netlify | Eventos estructurados, correlacionados y sin contenido fiscal |
| Ejecución de estrategias activas | Supabase privado | Fuente de verdad por petición: versión, respuestas, recuperación, citas y coste |

Se descartó el **drenaje de logs de Netlify**: requiere plan Pro.

Los logs de Netlify no son un ledger. En una comprobación real, la consulta de
logs mostró una línea vacía donde debía aparecer el último evento de coste,
mientras Supabase sí conservaba la ejecución completa. Por tanto, una ausencia
en Netlify no se interpreta como ausencia de llamada ni se usa sola para decidir
entre A y B.

## Contrato del evento de finalización

Cada petición que termina y se persiste emite `chat_cost_reconciled`. El nombre se
conserva por compatibilidad, pero el evento ya no describe solo coste:

- `schema_version=residenciafiscal-chat-observability/1` versiona el contrato
  común de los tres eventos estructurados;
- `request_status=completed` separa el resultado operativo de la contabilidad;
- `cost_measurement_complete` indica si todos los costes son `ACTUAL`;
  `actual_complete` conserva el mismo valor como alias histórico y **no** significa
  que la respuesta haya quedado incompleta;
- `timings_ms` separa registro, comparación, persistencia y total;
- `authority_intent` registra solo el enum seguro `tribunal_supremo` /
  `audiencia_nacional`, nunca el texto que lo originó;
- cada estrategia declara estado, modelo, latencia, tokens, coste, número de
  fuentes y límites, IDs de resoluciones recuperadas, reparto de citas `STS` /
  `SAN`, filtro aplicado y recuento de citas candidatas y verificadas;
- `document_token_accounting=unavailable` distingue el caso en que Gemini aporta
  citas pero no desglosa tokens documentales; no debe interpretarse el cero como
  ausencia de recuperación. El adaptador actual reconoce también
  `total_tool_use_tokens`, el campo observado en Interactions para el contexto
  recuperado, y en ese caso la medición vuelve a ser `reported`;
- `failure_code` distingue `timeout`, excepción, contrato de estrategia,
  verificación de citas y validación de evidencia. `error_name` solo admite un
  nombre de clase saneado; nunca sale el mensaje de la excepción.
- `error_context`, cuando existe, añade diagnóstico técnico seguro: dependencia
  (`supabase`, `openai`, `gemini`, `configuration` o `internal`), operación,
  clasificación (`rpc_not_found`, `invalid_payload`, `provider_timeout`, etc.),
  código/estado HTTP, si es reintentable y, para una configuración incompleta,
  los nombres de las variables ausentes. Nunca incluye el mensaje bruto del
  proveedor.

El evento puede contener IDs públicos de sentencias, contadores y enums. No puede
contener pregunta, respuesta, citas literales, `limits` ni diagnósticos brutos del
proveedor. El contenido necesario para una revisión autorizada sigue en el ledger
privado con su retención propia.

## Qué llega a Sentry, y qué no

La Function **no usa `@sentry/node`**, y es deliberado. El SDK captura
breadcrumbs de consola y contexto del runtime por defecto, y este runtime loguea
eventos estructurados por consola; desactivar cada captura automática es más
frágil que escribir el payload. `netlify/functions/chat/sentry-envelope.ts`
construye el envelope y `observability.ts` lo envía con `fetch`, así que lo que
sale está acotado por un contrato revisable.

Viaja: `schema_version`, `failure_code`, `stage` o `strategy`, `status` cuando
existe, `request_id`, `error_name`, `error_context` seguro, latencia, entorno y
fingerprint.

Las respuestas de error del endpoint incluyen `x-chat-request-id`, que permite
cruzar la consola del navegador con Netlify/Sentry sin devolver al cliente el
diagnóstico interno ni el contenido de la consulta.

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

Una petición puede terminar `completed` aunque A o B devuelva `error`. Después de
persistir el ledger y antes del evento de coste, la Function envía en paralelo
un `chat_strategy_failed` por cada estrategia fallida. Su fingerprint agrupa por
estrategia y código (`timeout`, excepción, contrato, cita o evidencia), sin incluir
el mensaje del proveedor. Un fallo de Sentry no cambia la respuesta HTTP.

Si `SENTRY_RELEASE` no está configurado, la Function usa `COMMIT_REF` y después
`DEPLOY_ID`, variables nativas del despliegue de Netlify. Así un error queda
asociado a una versión sin mantener una variable manual.

## Alertas: dos reglas, no una

Con el tráfico actual una alerta **solo** por tasa no saltaría nunca. Por eso hay
dos en `residencia-fiscal-chat`:

1. `Chat: fallo nuevo en la Function` — primer fallo global o aislado y regresiones.
2. `Chat: tasa de fallos elevada` — 5 eventos globales o aislados en 1 hora.

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

#### Una alerta de prueba se marca sola

`--failure-alert` acepta cualquier `--failure-exit-code` desde la terminal, así
que probarla producía un mensaje **idéntico** al de un job roto; solo lo salvaba
que alguien escribiera «PRUEBA» a mano en el texto. Una alerta que se puede
confundir con un simulacro deja de leerse como alerta.

El aviso se marca ahora solo: si falta `INVOCATION_ID` —que systemd exporta al
servicio y heredan sus hijos—, la ejecución viene de la terminal y la primera
línea sale como `🧪 PRUEBA`, con una frase que declara que no ha fallado nada.
El marcador va **delante** porque la notificación push solo enseña el principio.

`--dry-run` funciona también con `--failure-alert`, para probar el texto sin
gastar un mensaje en el canal real.

### El silencio del timer también se vigila

Todo lo anterior solo actúa cuando el resumen **corre y falla**. Si el timer no
llega a dispararse —máquina apagada, timer parado, unit desinstalada por un
`git pull` sin reinstalar—, no hay fallo que capturar y el silencio vuelve a ser
indistinguible del éxito.

`scripts/check_daily_chat_cost_freshness.py` cierra ese hueco a las 10:15, una
hora después del digest, con su propio par de units
(`residenciafiscal-daily-chat-cost-freshness.{service,timer}`). Es el equivalente
del check de frescura independiente que ya protege los backups. Alerta cuando:

- el estado lleva `--max-staleness-days` (1 por defecto) sin avanzar,
- el timer vigilado no está `active`, aunque el estado aún parezca fresco,
- no existe estado de ningún envío previo.

Si todo está al día **no manda nada**: un guardián que habla a diario deja de
leerse. `--report` fuerza el veredicto para comprobarlo a mano.

No reimplementa la lectura del estado, la **importa** del propio digest: un
guardián que parsea el fichero por su cuenta acaba divergiendo de quien lo
escribe, y entonces miente en la dirección peor, diciendo que todo está bien.
Corre con `python3` del sistema por el mismo motivo que el aviso de fallo.

**Su límite es real y no se disimula**: comparte máquina con lo que vigila, así
que no puede avisar de un apagón *mientras* dura; `Persistent=true` lo dispara al
arrancar y el aviso sale entonces. Vigilarlo desde fuera exigiría mover el timer
al VPS `alfredo`, que es la decisión que la sección de activación descarta a
propósito por no ampliar la superficie de la clave de servicio.

#### El guardián tampoco puede morir callado

Nació más frágil que lo que vigila: si reventaba, systemd lo marcaba `failed` y
nadie lo leía —la misma clase de silencio que existe para eliminar, un nivel más
arriba—. Dos cierres, y el segundo importa más que el primero:

- **Un fallo propio se avisa por Telegram**, nombrando su unit y cortando el
  detalle en 500 caracteres. Si ni el aviso sale, queda el journal y un exit
  distinto de cero (`1`); ahí termina la cadena, y termina a propósito.
- **El canal se comprueba en cada pasada**, no solo cuando hay algo que avisar.
  Con todo al día el check sale por el camino del silencio **antes** de tocar el
  `.env`, así que sin esta comprobación un `TELEGRAM_TOKEN` desaparecido no se
  descubriría hasta la primera alerta de verdad: el peor momento posible. Si
  falta, el check no puede avisar por Telegram de que no puede avisar por
  Telegram, así que falla ruidosamente con exit `3`. Se comprueban los **mismos
  alias** que acepta `send_telegram` (`TG_BOT_TOKEN`, `TG_CHAT_ID`): mirar solo
  el nombre canónico declararía roto un canal que funciona.

`--dry-run` exime de esa comprobación —en seco no hay envío que proteger, y
exigirla impediría probar el check sin `.env`—, y tampoco entrega el aviso de
fallo: probar el guardián no puede costar una alerta falsa en el canal.

El guardián hereda además el **marcador de prueba** del resumen diario: un aviso
suyo disparado a mano sale como `🧪 PRUEBA`. Es un emisor de alertas más, y si
probarlo mete en el canal un mensaje indistinguible de uno real, se gasta la
credibilidad de todos.

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
   `residenciafiscal-daily-chat-cost-telegram.{service,timer}` y su guardián
   `residenciafiscal-daily-chat-cost-freshness.{service,timer}`.

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

   Instala las **cuatro** units de una vez, a propósito: el guardián existe para
   vigilar que el digest corra, y un guardián que se instala aparte es un
   guardián que se olvida de instalar.

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
- El marcador de prueba, comprobado en la cadena real el 2 de agosto de 2026:
  bajo `systemd-run --user`, el aviso sale sin marca; el mismo comando desde la
  terminal sale como `🧪 PRUEBA`. La premisa se verificó aparte leyendo
  `INVOCATION_ID` dentro de una unit.
- El guardián, ya endurecido, el 2 de agosto de 2026: un fallo real provocado
  con una fecha imposible produjo su aviso (`ValueError`) y exit `1` sin
  entregarlo en seco; una ejecución normal con el `.env` verdadero **no** dio
  falso positivo de canal, que era el riesgo de haber errado los alias; y un
  aviso de desfase se **entregó de verdad** en Telegram, marcado `🧪 PRUEBA`.
- El guardián de frescura, contra el estado real de la máquina el mismo día:
  con el estado al día calló (`--report` confirmó «al día», timer `active`); con
  un estado del 2026-07-28 avisó de 4 días; sin estado avisó de que no se había
  enviado nunca; y **con el timer del digest parado de verdad** avisó aunque el
  estado estuviera fresco, quedando el timer restaurado a `active`. Una
  ejecución del service terminó en `0/SUCCESS` sin mandar nada.
