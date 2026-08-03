# Backups de la base de datos

`scripts/backup/` respalda a diario el proyecto Supabase en el bucket R2
`residenciafiscal-backup` mediante tres `systemd timer` del VPS `alfredo`:
backup, check de frescura independiente y simulacro mensual no destructivo. Los
scripts **no** llevan credenciales y **nunca** hacen `source` del `.env` —lo
parsean con `lib-read-env.sh`—, y las units ejecutan `/bin/bash <script>` para no
depender del bit executable del checkout.

El dump cubre `private`, `public`, `auth` y `supabase_migrations`: **el dato del
chat vive en `private`**, así que un dump de `public` saldría verde y vacío. Al
crear un schema nuevo hay que añadirlo a `BACKUP_SCHEMAS` en `vps-backup.sh`; el
guardián de cobertura del propio script y `tests/test_backup_scripts.py` avisan
si alguien lo olvida. Cada snapshot valida tablas, bloques `COPY` y las tres RPC
vigentes antes de subirlo; el simulacro mensual compara ese contrato con
Supabase. El checkout operativo del VPS quedó reconciliado con `origin/main` el
2 de agosto de 2026 y **sigue sin actualizarse solo**: tras cambiar un script
hay que hacer `git pull` allí, y relanzar `install-backup-timer.sh` si cambió
una unit, porque systemd ejecuta su propia copia. Que eso se olvide ya no pasa
en silencio: `check-operational-drift.sh` compara a diario el checkout, las
units instaladas y `origin/main`, y alerta por Telegram. Nunca reconcilia solo.
Arquitectura, operativa, límites y consecuencias de privacidad:
[`docs/operations/BACKUPS.md`](../../docs/operations/BACKUPS.md).
