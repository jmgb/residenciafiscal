# Informe semanal de tráfico

Cada **lunes a las 09:00 (Europe/Madrid)** llega a Telegram un resumen del
tráfico de `residenciafiscal.org`: visitas, usuarios únicos y qué parte de esos
usuarios ya había visitado el sitio antes.

Es el mismo runner que tienen Presupuestor, Doctor y Comunicador, con un timer
propio por proyecto: cada repositorio manda su propio mensaje y ninguno depende
de los demás.

## Piezas

| Fichero | Papel |
|---------|-------|
| `scripts/weekly_ga4_telegram.py` | Consulta la analítica, compone el mensaje y escribe el histórico. Solo librería estándar mientras GA4 esté apagado. |
| `scripts/agentic/weekly_ga4_telegram_runner.sh` | Entrada del timer: comprueba el interruptor, elige dependencias y avisa por Telegram si el envío falla. |
| `scripts/agentic/residenciafiscal-weekly-ga4-telegram.{service,timer}` | Unidades `systemd --user` de la máquina que dispara los informes. |
| `scripts/agentic/install-weekly-ga4-telegram-timer.sh` | Instalador idempotente de las unidades. |
| `scripts/ga4_list_properties.py` | Descubre el ID numérico de las propiedades GA4 visibles. Solo se usa al conectar GA4. |
| `tests/test_weekly_ga4_telegram.py` | Contrato de ventanas, formato, consulta, mensaje e histórico. Sin red. |

## Qué mide y de dónde sale

El sitio tiene **dos analíticas** y el informe publica **una línea por cada
una**, sin promediarlas ni elegir una como buena:

- **GA4**, propiedad `547477728` (measurement ID `G-XKX3N9KVJH`).
- **PostHog**, proyecto `237205` («Residencia Fiscal») en la organización europea.

La ventana son los **siete días cerrados anteriores** al día de ejecución, y se
compara con los siete inmediatamente anteriores. El lunes 3 de agosto se informa
del 27 de julio al 2 de agosto frente al 20–26 de julio: nunca entra el día en
curso, que estaría a medias.

```
✅ Análisis Tráfico 2026-08-03

GA4: 168 visitas (+40,0%), 81 usuarios (+35,0%), 2 recurrentes (2,5%). 24 de 96 sesiones con interacción (25,0%).
PostHog: 7 visitas (nuevo), 1 usuario (nuevo), 0 recurrentes (0,0%).

Fuente: GA4 (propiedad 547477728) y PostHog (residenciafiscal.org).
```

| Magnitud | En GA4 | En PostHog |
|---|---|---|
| Visitas | `screenPageViews` | eventos `$pageview` con `$host = residenciafiscal.org` |
| Usuarios | `activeUsers` | `person_id` distintos |
| Recurrentes | cubo `returning` de `newVsReturning` | usuarios cuya primera visita registrada es anterior al inicio de la ventana |
| Sesiones con interacción | `engagedSessions` sobre `sessions` | — |

La recurrencia se mide contra la **semana**, no contra la sesión: quien entra por
primera vez y vuelve dos días después sigue siendo nuevo esa semana.

Las **sesiones con interacción** son la cláusula que separa personas de
rastreadores, y por eso solo aparece en GA4: un bot entra una vez, no interactúa
y se va. En la semana medida fueron 12 de 53 sesiones en Estados Unidos frente a
8 de 28 en España. Un porcentaje que se desploma sin que caiga el total de
visitas es la señal de una oleada de rastreo, no de menos público.

## Por qué las dos cifras no se parecen

En la primera semana con las dos fuentes activas, GA4 vio **81 usuarios** y
PostHog **1**. La diferencia no es un error del informe; es lo que cada
herramienta cuenta. El desglose de GA4 de esa semana:

- 53 de los 81 usuarios eran de **Estados Unidos**, y 13 de España.
- Las ciudades son centros de datos: Council Bluffs (Google), Ashburn y Boardman
  (AWS), San José, Chicago.
- Exactamente **una sesión por usuario** en el bloque estadounidense, con 4,2 s
  de media. España, en cambio, 28 sesiones para 13 usuarios.

Es decir: **tráfico automatizado que ejecuta JavaScript** (rastreadores de
buscadores, agentes LLM, herramientas SEO). GA4 filtra solo los bots de su lista
conocida y estos no están en ella. PostHog apenas los registra porque necesita
persistir una cookie de primera parte entre eventos.

Ninguna de las dos es «la verdad»: GA4 infla con bots y PostHog infravalora a
las personas que bloquean cookies o cambian de navegador. Verlas juntas es lo
que hace visible ese sesgo. Para juzgar tráfico humano, mirar España y las
sesiones con interacción, no el total.

## Excluir nuestras propias visitas

Visitar **`https://residenciafiscal.org/?no_analytics=1`** una vez en cada
navegador y dispositivo deja una marca en `localStorage` y a partir de ahí ni
GA4 ni PostHog se cargan ahí nunca más, incluida esa misma carga.
`?no_analytics=0` la retira.

Se eligió una marca por navegador y no un filtro de IP interna en GA4 porque la
IP doméstica es dinámica y no cubre los datos móviles; además el filtro de GA4
no afectaría a PostHog. La marca viaja con el navegador, que es lo que de verdad
identifica «nuestras propias visitas».

La lógica vive en `frontend/src/lib/analytics-optout.ts` y la consumen las dos
analíticas a través de la misma puerta, `isGoogleAnalyticsEnabled`. Degrada a
«sin marca» si `localStorage` lanza —Safari privado, almacenamiento
bloqueado—, porque la analítica nunca debe romper la página.
`frontend/tests/analytics-optout.test.ts` fija ese contrato.

Esto **no** filtra bots, que son la mayor parte del ruido: no hay forma fiable
de excluirlos desde el cliente. Para eso está la cláusula de sesiones con
interacción.

### Los históricos son cortos

GA4 empezó a registrar el 29 de julio de 2026 y PostHog el 1 de agosto. Hasta
que ambas acumulen dos semanas completas, la variación semanal aparecerá como
`nuevo` (base cero) en lugar de un porcentaje. No es un fallo.

## GA4: cómo está conectado

### El patrón de los repos hermanos

No hay OAuth ni claves de API: GA4 se lee con una **cuenta de servicio de Google
Cloud** a la que se le da rol **Lector** dentro de Google Analytics. La cuenta se
comparte entre proyectos; lo que cambia en cada repo es la propiedad.

| Repo | Cuenta de servicio | Propiedad |
|------|--------------------|-----------|
| Presupuestor | `presupuestor-claude-skill@presupuestor-485509` | `502126208` |
| Comunicador | la misma | `539999056` |
| Doctor | `claude-mcp-access@doctor-489817` (cuenta GA distinta) | `343049249` y las cinco traducciones |

Cada repo guarda el JSON de la cuenta en `credentials/ga4.json` —ignorado por
git— y declara en su `.env`:

```dotenv
GOOGLE_APPLICATION_CREDENTIALS=credentials/ga4.json
GA4_PROPERTY_ID=<id numérico>
```

El `G-XXXXXXX` del frontend es el *measurement ID* y **no** sirve aquí: la API
pide el ID numérico de la propiedad.

### Cómo quedó en este repo

La cuenta de servicio tiene rol **Lector a nivel de la cuenta «Nichos»**, así que
ve las siete propiedades de esa cuenta y los próximos sitios de nicho no exigen
repetir el trámite. La credencial está en `credentials/ga4.json` y el `.env`
declara `GA4_PROPERTY_ID=547477728`.

Para redescubrir IDs —al añadir un sitio o al comprobar un permiso—:

```bash
uv run --with google-analytics-admin --with google-auth \
    python scripts/ga4_list_properties.py
```

Sin `GA4_PROPERTY_ID` el informe se queda solo en PostHog y no falla.

El skill global `google-analytics` lee ese mismo `.env`, así que también responde
consultas puntuales sobre este sitio desde la raíz del repositorio.

### Trampa de la API: `activeUsers` no es aditivo

El total de usuarios y el desglose `new` / `returning` se piden en **dos
informes distintos**. Sumar los cubos de `newVsReturning` no da el total: GA4
deduplica por dimensión, y además deja un cubo sin etiquetar —17 de 98 en la
primera semana— que el histórico guarda como `unclassified_users`. Por eso el
total se lee sin dimensión y el desglose solo aporta los recurrentes.

## Operación

```bash
# Ver el mensaje sin enviarlo (útil para revisar redacción o una fecha concreta)
bash scripts/agentic/weekly_ga4_telegram_runner.sh --dry-run
bash scripts/agentic/weekly_ga4_telegram_runner.sh --dry-run --date 2026-08-03

# Instalar o reinstalar las unidades tras un git pull que las toque
bash scripts/agentic/install-weekly-ga4-telegram-timer.sh

# Estado y ejecución manual
systemctl --user list-timers residenciafiscal-weekly-ga4-telegram.timer
systemctl --user start residenciafiscal-weekly-ga4-telegram.service
journalctl --user -u residenciafiscal-weekly-ga4-telegram.service -n 50 --no-pager
```

Para silenciar el informe sin desinstalar nada, `WEEKLY_GA4_TELEGRAM_ENABLED=false`
en `.env`.

Si el envío falla, el runner intenta un segundo mensaje de aviso con el
intérprete del sistema, para que un entorno de `uv` roto no deje el fallo en
silencio.

## Histórico y privacidad

Cada ejecución escribe `reports/weekly_ga4_telegram/<fecha>.json` y actualiza
`latest.json`, con las dos ventanas y las cifras de ambas.

**`reports/` está en `.gitignore` a propósito**: este repositorio es público y
las cifras de tráfico son información de negocio. El histórico vive solo en la
máquina que ejecuta el timer.

Las claves (`POSTHOG_*`, `TELEGRAM_*`) están únicamente en `.env`, que tampoco se
versiona. El script **nunca hace `source` del `.env`**: lo parsea línea a línea,
igual que los scripts de backup, para que un valor con `$(...)` no se ejecute.
