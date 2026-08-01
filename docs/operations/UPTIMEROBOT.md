# UptimeRobot — residenciafiscal.org

Monitorización externa del frontend, configurada el 2026-07-30 sobre la cuenta
compartida de UptimeRobot (`UPTIMEROBOT_ALERT_EMAIL` en `.env`; plan Free: 50
monitores y 5 minutos de intervalo mínimo).

Solo se vigila el frontend. La API FastAPI de este repositorio corre en local
(`make dev`) y no está desplegada, así que no hay nada más que comprobar desde
fuera.

## Monitores

| ID | Nombre | Tipo | URL | Palabra clave | Intervalo |
| --- | --- | --- | --- | --- | --- |
| 803628459 | `ResidenciaFiscal Frontend` | KEYWORD | `https://residenciafiscal.org` | `Residencia Fiscal` | 300 s |
| 803628460 | `ResidenciaFiscal Corpus` | KEYWORD | `https://residenciafiscal.org/data/corpus.json` | `"ecli":"ES:` | 300 s |

Ambos usan `GET`, `ALERT_NOT_EXISTS` (cae si la palabra clave **desaparece**),
timeout 30 s, grace period 30 s y avisan al contacto de email `7503923`, sin
umbral ni recurrencia. Es la misma configuración que el resto de frontends de la
cuenta.

## Por qué keyword y no un monitor HTTP simple

El fallback SPA de Netlify (`/*` → `/index.html`, status 200) hace que **cualquier
ruta inexistente responda 200 con HTML**. Comprobado en producción:
`/data/noexiste.json` devuelve 200. Un monitor HTTP seguiría en verde con el
corpus borrado o con un `index.html` roto. La palabra clave distingue «responde»
de «sirve lo que debe»:

- la home cae si el HTML servido deja de contener la marca;
- el corpus cae si `data/corpus.json` deja de ser el JSON del corpus —incluido el
  caso en que el build lo pierde y Netlify devuelve el `index.html` del fallback,
  que no contiene `"ecli":"ES:`.

El corpus se vigila aparte porque el chat no funciona sin él y su desaparición no
rompe la home.

## La home responde ahora con un `301`

Desde el 1 de agosto de 2026, `https://residenciafiscal.org/` redirige de forma
permanente a `/espana`: la raíz servía la shell sin contenido prerenderizado
(ver [`../product/COUNTRY_PAGES.md`](../product/COUNTRY_PAGES.md)). El monitor
`803628459` apunta a la raíz, así que **depende de que UptimeRobot siga la
redirección**, cosa que hace por defecto. La palabra clave existe en el destino:
`/espana` contiene `Residencia Fiscal` en su `<title>` y en su contenido.

Conviene saber una cosa incómoda: ese monitor estaba en verde **antes** del
cambio aunque la raíz sirviera una página en blanco, porque la marca aparecía en
el `<title>` de la shell. Una palabra clave que vive en el `head` comprueba que
Netlify responde, no que la página tenga contenido.

**Comprobar tras el primer deploy con el `301`** que el monitor sigue en verde;
si no, apuntarlo directamente a `https://residenciafiscal.org/espana`.

## Cloudflare: el User-Agent importa

La zona está detrás de Cloudflare con una regla de WAF que bloquea User-Agents de
scanner (ver [`CLOUDFLARE.md`](CLOUDFLARE.md)). Un `curl` sin `-A` recibe **403**.
El User-Agent de UptimeRobot (`Mozilla/5.0 (compatible; UptimeRobot/2.0; …)`)
devuelve 200; se verificó antes de crear los monitores. Si algún día los monitores
caen en bloque con 403, revisar primero las reglas custom del WAF, no Netlify.

Al comprobar el sitio a mano, usar siempre un UA explícito:

```bash
curl -sI -A 'Mozilla/5.0 (compatible; UptimeRobot/2.0; http://uptimerobot.com/)' \
  https://residenciafiscal.org/
```

## API: usar la v3, no la v2

La API v2 (`https://api.uptimerobot.com/v2/newMonitor`) devuelve
`access_denied: You are not allowed to use some settings with your current plan`
en **cualquier** escritura con este plan, incluso en un monitor HTTP mínimo. Las
lecturas de la v2 sí funcionan. La v3 crea y edita sin problema:

```bash
# Listar monitores
curl -s -H "Authorization: Bearer $UPTIMEROBOT_API_KEY" \
  'https://api.uptimerobot.com/v3/monitors?limit=50'

# Crear un monitor keyword
curl -s -X POST -H "Authorization: Bearer $UPTIMEROBOT_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"friendlyName":"Nombre","url":"https://ejemplo.org","type":"KEYWORD",
       "keywordType":"ALERT_NOT_EXISTS","keywordValue":"texto","keywordCaseType":1,
       "httpMethodType":"GET","successHttpResponseCodes":["2xx","3xx"],
       "interval":300,"timeout":30,"gracePeriod":30,
       "assignedAlertContacts":[{"alertContactId":7503923,"threshold":0,"recurrence":0}]}' \
  https://api.uptimerobot.com/v3/monitors
```

La v3 limita la tasa de forma agresiva: varias escrituras seguidas devuelven
`429 ThrottlerException`. Espaciar las llamadas al crear o editar en lote.

`POST /v3/monitors` responde con `authType: HTTP_BASIC` aunque no se envíen
credenciales; los monitores se dejaron en `authType: NONE` con un `PATCH`
posterior para igualarlos al resto de la cuenta.

## Credenciales

`.env` (nunca versionado) define:

- `UPTIMEROBOT_API_KEY` — clave de cuenta (prefijo `u…`), válida para v2 y v3.
- `UPTIMEROBOT_ALERT_EMAIL` — destinatario de las alertas.

## Qué no cubre

- No comprueba el chat de extremo a extremo, solo que el HTML y el corpus se
  sirven.
- No vigila Netlify Functions ni Edge Functions: hoy no hay ninguna en producción.
- El plan Free no incluye avisos de caducidad de SSL o dominio ni comprobación
  multirregión; los monitores se ejecutan desde Norteamérica.
- No hay página de estado pública ni alertas por Telegram; el único canal es el
  email.
