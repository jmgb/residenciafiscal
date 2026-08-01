# Backups de la base de datos

> **Estado**: instalado y verificado el 2026-08-01.
> **Método**: tres `systemd timer` de backup y un timer de retención del chat preparado para el VPS `alfredo`.
> **Destino**: bucket `residenciafiscal-backup` de Cloudflare R2.
> **Proyecto Supabase**: `qqrwirtdnomapahglvlv` (`eu-west-1`, PostgreSQL 17).

Supabase respalda la base de datos en su plataforma, pero eso no cubre tener una
copia propia, verificable y fuera de su consola. Este subsistema mantiene un dump
diario en R2, comprueba a diario que ese dump existe, se puede leer y cumple su
contrato estructural, y una vez al mes compara su inventario con el Supabase vivo.

Es el mismo diseño que corre desde febrero de 2026 en Presupuestor y desde julio
en Comunicador, sobre el mismo VPS y la misma cuenta de R2. Las diferencias con
ellos están señaladas donde aparecen.

## Qué responde cada pieza

El sistema contesta cuatro preguntas distintas, y son distintas a propósito: un
backup puede "ejecutarse bien" y dejar en R2 un fichero corrupto.

| Pregunta | Pieza | Cuándo |
|---|---|---|
| ¿Se ha ejecutado el backup? | `residenciafiscal-backup.timer` → `vps-backup.sh` | Diario, 02:30 local del VPS |
| ¿Hay en R2 un backup reciente, legible y estructuralmente íntegro? | `residenciafiscal-backup-freshness.timer` → `check-backup-freshness.sh` | Diario, 03:05 |
| ¿Coincide el backup con el contrato vivo de Supabase? | `residenciafiscal-backup-restore-drill.timer` → `check-backup-restore-drill.sh` | Día 1 de cada mes, 06:35 |
| ¿Se ha aplicado la retención de Supabase? | `residenciafiscal-chat-retention.timer` → `scripts/privacy/purge-chat-data.sh` | Diario, 03:20 |

Los timers usan `Persistent=true` (recuperan la ejecución perdida si el VPS
estaba apagado) y `RandomizedDelaySec=300`. Los huecos horarios están elegidos
para no solaparse con los backups de Presupuestor y Comunicador, que ya ocupan la
franja 03:30–06:03 en la misma máquina.

## Flujo del backup diario

```
residenciafiscal-backup.timer (02:30 local)
        │
        ▼
vps-backup.sh
  1. lee el inventario vivo y rechaza schemas no cubiertos
  2. pg_dump de public + private + auth + supabase_migrations contra el pooler
  3. añade un manifiesto de tablas y RPC; valida CREATE TABLE + COPY + FUNCTION
  4. gzip
  5. aws s3 cp  →  s3://residenciafiscal-backup/YYYY-MM-DD_HHMMSS_full.sql.gz
  6. aws s3 ls  →  verifica que el objeto existe en destino
  7. borra los objetos de más de `${RETENTION_DAYS}` días
        │
        ▼ (si algo falla)
OnFailure → residenciafiscal-backup-failure@.service → Telegram
```

El nombre del objeto lleva **timestamp UTC**, mientras que el timer dispara en
hora local del VPS. Con el VPS en CEST, el backup de las 02:30 aparece en R2 como
`..._0030xx_...`. Es esperado, no un reloj mal puesto.

### Qué entra en el dump y qué no

`BACKUP_SCHEMAS` en `vps-backup.sh` declara los schemas incluidos:

| Schema | Por qué entra |
|---|---|
| `private` | **Todo el dato del chat**: conversaciones, mensajes, peticiones y auditoría de retención ([contrato](SUPABASE_CHAT.md)) |
| `public` | Vacío hoy; es el destino natural de cualquier tabla futura |
| `auth` | Usuarios de Supabase Auth |
| `supabase_migrations` | Registro de migraciones aplicadas; sin él, un proyecto restaurado cree que no tiene ninguna |

**El chat no vive en `public`.** Copiar tal cual el `--schema=public --schema=auth`
de Presupuestor habría producido backups verdes y vacíos de contenido. Por eso el
primer paso del script es un guardián: consulta qué schemas tienen tablas y falla
—con aviso de Telegram— si aparece alguno que no esté ni en `BACKUP_SCHEMAS` ni
justificado en `IGNORED_SCHEMAS`. El fallo ocurre **antes** de subir: un snapshot
parcial nunca se publica como si fuera un backup válido y el snapshot anterior
permanece disponible.

Cada dump lleva además un manifiesto con las tablas actuales de `public` y
`private` y las RPC públicas requeridas: `create_chat_request`,
`complete_chat_request` y `fail_chat_request`. `verify-backup-contract.sh`
comprueba que el SQL contiene exactamente esas tablas, un bloque `COPY` para
cada una y la definición de las tres funciones. Las RPC económicas históricas
no forman parte del contrato.

Quedan fuera a propósito, con su motivo en el propio script: `storage` (Supabase
Storage no se usa: los PDF son estáticos del build), `realtime` (efímero), `vault`
(secretos cifrados, no restaurables desde un dump) y la fontanería gestionada por
Supabase (`extensions`, `graphql`, `pgbouncer`…).

Fuera del alcance de cualquier dump SQL: los PDF del CENDOJ y el corpus, que
viven versionados en git, y el File Search Store de Gemini, que se reconstruye
desde esos PDF.

## Configuración

Los scripts **no llevan credenciales**. Las leen primero del entorno del proceso
y, si faltan, del `.env` de la raíz del checkout —**sin ejecutarlo**, mediante
`lib-read-env.sh`—. Cualquiera que falte aborta el script con la lista de las que
faltan.

| Clave | Uso |
|---|---|
| `SUPABASE_REF` | Ref del proyecto; forma el usuario `postgres.<ref>` |
| `SUPABASE_DB_PASSWORD` | Password de Postgres para `pg_dump` / `psql` |
| `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_ACCOUNT_ID` | Credenciales y endpoint de R2 |
| `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` | Alertas de fallo (opcionales: sin ellas el script avisa por journal y sigue) |
| `CHAT_RETENTION_DAYS` | Plazo aprobado para el purgado del chat; obligatorio para instalar el timer |
| `CHAT_RETENTION_PURGE_ENABLED` | Activa el job de retención; por defecto `false` |
| `CHAT_RETENTION_DRY_RUN` | Simula el purgado y audita candidatos; por defecto `true` |
| `CHAT_RETENTION_BATCH_LIMIT` | Máximo de filas candidatas por familia y ejecución; por defecto `500` |
| `BACKUP_RETENTION_DAYS` | Retención de snapshots R2; si se omite, usa `CHAT_RETENTION_DAYS` y, sin ambos, el fallback histórico de 30 días |

El `.env` del VPS **contiene solo las claves operativas de backup y retención**,
no una copia del `.env` de desarrollo: las credenciales de OpenAI, Gemini, Sentry
o PostHog no tienen nada que hacer en la máquina que hace backups.

Ajustables por entorno sin tocar código: `BACKUP_R2_BUCKET`,
`BACKUP_RETENTION_DAYS` (30), `BACKUP_POOLER_HOST`,
`BACKUP_FRESHNESS_MAX_AGE_HOURS` (30) y las rutas `BACKUP_*_ENV_FILE`.

## Instalación en el VPS

```bash
# 1. Checkout del repo en el VPS
ssh -o RemoteCommand=none alfredo
git clone https://github.com/jmgb/residenciafiscal.git ~/residenciafiscal

# 2. .env mínimo con las claves de backup de la tabla anterior y, si se instala
#    el purgado, CHAT_RETENTION_DAYS con el plazo aprobado
#    (copiar los valores desde el .env local; nunca versionarlo)
vi ~/residenciafiscal/.env
chmod 600 ~/residenciafiscal/.env

# 3. Instalar units y timers (idempotente: repetible tras cada git pull)
sudo bash "$HOME/residenciafiscal/scripts/backup/install-backup-timer.sh"

# Después de aprobar y configurar CHAT_RETENTION_DAYS:
sudo bash "$HOME/residenciafiscal/scripts/privacy/install-chat-retention-timer.sh"
```

El instalador comprueba las claves del `.env`, instala `postgresql-client-17`
desde PGDG si hace falta —el `pg_dump` 16 de Ubuntu 24.04 **se niega** a dumpear
un servidor 17— y AWS CLI v2, copia las units, recarga systemd y activa los tres
timers.

El bucket `residenciafiscal-backup` debe existir antes del primer backup. Se crea
desde el panel de Cloudflare (R2 → Create bucket, ubicación *Auto*) o con las
credenciales del `.env`:

```bash
aws s3 mb s3://residenciafiscal-backup \
  --endpoint-url "https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
```

**El checkout del VPS no se actualiza solo.** Tras cambiar cualquier script o
unit hay que sincronizar las rutas operativas indicadas abajo y volver a lanzar
el instalador; si no, el VPS sigue ejecutando la versión anterior sin decir nada.

> **Deuda del arranque (2026-07-31).** El sistema se instaló antes de que
> `scripts/backup/` estuviera commiteado, así que el checkout del VPS conserva
> copias operativas sin seguimiento de git. No se debe hacer un `git pull` ni
> borrar esas copias a ciegas. Hasta reconciliar el checkout, los despliegues se
> hacen copiando únicamente `scripts/backup/` y reinstalando las units:
>
> ```bash
> rsync -av --itemize-changes scripts/backup/ \
>   alfredo:residenciafiscal/scripts/backup/
> ssh -o RemoteCommand=none alfredo \
>   'sudo bash "$HOME/residenciafiscal/scripts/backup/install-backup-timer.sh"'
> ```

## Operativa

```bash
# Backup manual ahora
ssh -o RemoteCommand=none alfredo 'sudo systemctl start residenciafiscal-backup.service'

# Estado y próxima ejecución de los tres timers
ssh -o RemoteCommand=none alfredo \
  'systemctl list-timers "residenciafiscal-backup*" --no-pager'

# Logs recientes
ssh -o RemoteCommand=none alfredo \
  'journalctl -u residenciafiscal-backup.service --since "48 hours ago" --no-pager -o short-iso'

# Forzar el check de frescura
ssh -o RemoteCommand=none alfredo 'sudo systemctl start residenciafiscal-backup-freshness.service'

# Ejecutar el purgado del chat ahora
ssh -o RemoteCommand=none alfredo 'sudo systemctl start residenciafiscal-chat-retention.service'

# Listar backups en R2 (desde local, con el .env del repo)
./scripts/backup/restore-from-r2.sh

# Simulacro no destructivo de un backup concreto
./scripts/backup/restore-from-r2.sh --verify-only 2026-07-31_003012
```

### Restaurar

⚠️ **Sobrescribe la base de datos del proyecto.** El script pide escribir `yes`.

```bash
./scripts/backup/restore-from-r2.sh 2026-07-31_003012
```

Descarga el objeto de R2, lo descomprime y lo aplica con `psql` contra el pooler.
Un restore real deja el proyecto en el estado del dump: revisa antes que el
backup elegido es el que quieres y que nadie está escribiendo en producción.

### Simulacro mensual

El timer ejecuta `restore-from-r2.sh --verify-only` sobre el último backup:
descarga, descomprime, valida `CREATE TABLE`/`COPY`/RPC y compara el manifiesto
con el inventario actual de Supabase. **No** ejecuta el SQL en ninguna base, así
que todavía no demuestra que todas las sentencias se apliquen sin error. Para
eso se mantiene un restore trimestral manual en una base aislada.

Registro de simulacros:

| Fecha | Backup verificado | Resultado |
|---|---|---|
| 2026-07-31 | `2026-07-31_163321_full.sql.gz` | OK — 3.074 líneas descomprimidas |
| 2026-08-01 | `2026-08-01_112422_full.sql.gz` | OK — 3.492 líneas; contrato coincide con Supabase y sin DDL económico prohibido |

## Verificación de la instalación (2026-08-01)

Los tres servicios se lanzaron a mano tras desplegar el verificador, con
`Result=success` en los tres:

- **Backup**: objeto `2026-08-01_112422_full.sql.gz` (32 KB) subido y verificado
  en R2; retención de 15 días aplicada; guardián sin schemas huérfanos.
- **Frescura**: `Backup freshness OK … (0h old, gzip and SQL contract ok)`.
- **Simulacro**: `Backup restore drill OK … (3492 lines, contract matches live Supabase)`.

Contenido real del nuevo objeto, descargado desde R2: 4 tablas `private`
(`chat_conversations`, `chat_messages`, `chat_requests` y
`chat_retention_purge_audit`), ninguna tabla `public` y las tres RPC válidas.
No contiene DDL ejecutable para `chat_daily_budgets`, `reserve_chat_request` ni
campos de reserva monetaria. El schema `supabase_migrations` conserva, como dato
de auditoría dentro de un bloque `COPY`, el texto de migraciones históricas que
sí mencionaban esos nombres; esas cadenas no se ejecutan al restaurar y el
verificador las distingue expresamente de una definición SQL vigente.

Próximas ejecuciones automáticas de los tres timers de backup: 02:31, 03:09 y el
día 1 a las 06:39 (hora local del VPS, con el desfase aleatorio ya aplicado). El
timer de retención está instalado y activo; el 2026-08-01 ejecutó el primer
purgado real con 15 días de retención, cero candidatos y cero borrados.

## Privacidad

El dump se lleva a R2 **las preguntas de los usuarios y las respuestas de ambas
estrategias** (`private.chat_messages`), sin IP ni user-agent. Eso tiene tres
consecuencias que hay que tener presentes al tocar la política de datos:

- Los backups son una copia de datos personales con la vida propia definida por
  `BACKUP_RETENTION_DAYS` fuera de Supabase. Un borrado en la base no los alcanza.
- Si algún día se promete un plazo de conservación en `/privacidad`, el plazo
  aplicable es el mayor de los dos: el de la base y el de los backups.
- Ante una solicitud de supresión, la respuesta honesta incluye que la copia
  desaparece de los backups como mucho al agotarse `BACKUP_RETENTION_DAYS`.

El bucket es privado, sin URL pública, y R2 cifra en reposo. Los dumps **no** se
cifran con clave propia antes de subirlos: quien tenga las credenciales R2 lee el
contenido.

## Límites conocidos

1. **Sin recuperación a un punto en el tiempo.** Son snapshots diarios: se pierde
   lo escrito entre el último backup y el incidente.
2. **Restauración manual.** No hay automatismo; requiere una persona.
3. **El simulacro mensual no aplica el SQL.** Verifica descarga, estructura y paridad con el contrato vivo; el restore ejecutable sigue siendo trimestral y aislado.
4. **Retención plana**: snapshots diarios hasta `BACKUP_RETENTION_DAYS`. Sin retención semanal ni mensual.
5. **Depende del VPS.** Si `alfredo` está caído, no hay backup esa noche; el
   check de frescura del día siguiente lo delata.
6. **El checkout del VPS puede quedarse atrás** respecto al repo. Presupuestor
   resolvió esto con un timer de `git pull`; aquí, de momento, es manual.

## Troubleshooting

**`status=203/EXEC`** — la unit apunta a un script que no existe o perdió el bit
de ejecución. Las units ejecutan `/bin/bash <script>` justo para no depender del
bit; comprueba la ruta y que el checkout está actualizado.

**`status=127` con `<palabra>: command not found`** — señal de que algún script
está haciendo `source` del `.env`. No debería poder pasar: los scripts usan
`lib-read-env.sh` y hay un test que lo impide. Si aparece, el VPS está corriendo
una versión vieja: `git pull` y reinstalar.

**`HeadObject 400` contra R2** — falta `AWS_DEFAULT_REGION=auto`. Todos los
scripts la fijan; si aparece, revisa que no se esté ejecutando una copia antigua.

**El check de frescura alerta con el backup en verde** — mira el objeto real en
R2. Causas habituales: el nombre no cumple `YYYY-MM-DD_HHMMSS_full.sql.gz`, el
gzip está incompleto, o el reloj del VPS no cuadra con el timestamp UTC.

**`server version mismatch` en `pg_dump`** — el cliente es más antiguo que el
servidor. Relanza el instalador, que trae `postgresql-client-17` desde PGDG.

## Gate en el repositorio

`tests/test_backup_scripts.py` corre en `make fast-check` y en CI. Comprueba que
cada `ExecStart` apunta a un script existente, que el instalador copia y activa
todas las units, que ningún script ejecuta el `.env`, que todos fijan la región
`auto`, que cada servicio declara su `OnFailure` y que el dump incluye los
schemas que `SUPABASE_CHAT.md` declara. También ejecuta el verificador contra
dumps sintéticos y demuestra que detecta tablas sin bloque `COPY` y divergencias
frente al inventario esperado. La prueba operativa final sigue siendo el objeto
real generado y leído desde R2.
