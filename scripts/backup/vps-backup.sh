#!/bin/bash
# ============================================================================
# Residencia Fiscal — Backup diario de Supabase a Cloudflare R2
# ============================================================================
# Diseñado para ejecutarse desde systemd (residenciafiscal-backup.timer) en el
# VPS. Loguea a stdout/stderr → journald.
#
# Instalación: scripts/backup/install-backup-timer.sh
# Docs: docs/operations/BACKUPS.md
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${BACKUP_ENV_FILE:-$PROJECT_ROOT/.env}"

R2_BUCKET="${BACKUP_R2_BUCKET:-residenciafiscal-backup}"
POOLER_HOST="${BACKUP_POOLER_HOST:-aws-0-eu-west-1.pooler.supabase.com}"
TEMP_DIR="/tmp/residenciafiscal-backup-$$"

# Schemas que entran en el dump. `private` es donde vive TODO el dato del chat
# (ver docs/operations/SUPABASE_CHAT.md); `public` está vacío hoy pero se incluye
# porque es el destino natural de cualquier tabla futura. `supabase_migrations`
# es el registro de migraciones aplicadas: sin él, un proyecto restaurado cree
# que no tiene ninguna.
BACKUP_SCHEMAS=(public private auth supabase_migrations)

# Schemas que se dejan fuera a propósito, con su motivo. El guardián de cobertura
# del paso 6 alerta si aparece uno que no esté ni aquí ni en BACKUP_SCHEMAS.
#   storage             Supabase Storage no se usa (0 objetos); los PDF son estáticos del build
#   realtime            estado efímero de suscripciones
#   vault               secretos cifrados, no restaurables desde un dump
#   extensions/graphql/graphql_public/pgbouncer/net/cron/supabase_functions
#                       infraestructura gestionada por Supabase, sin dato de negocio
IGNORED_SCHEMAS=(storage realtime vault extensions graphql graphql_public pgbouncer net cron supabase_functions)

cleanup() {
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

mkdir -p "$TEMP_DIR"

# ── Cargar credenciales ───────────────────────────────────────────────────
if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: .env no encontrado en $ENV_FILE" >&2
    exit 1
fi

# NO usar `source` sobre el .env: no es un script bash (ver lib-read-env.sh).
# shellcheck source=lib-read-env.sh
source "$SCRIPT_DIR/lib-read-env.sh"

R2_ACCESS_KEY_ID="$(read_env_var_or_current "$ENV_FILE" R2_ACCESS_KEY_ID)"
R2_SECRET_ACCESS_KEY="$(read_env_var_or_current "$ENV_FILE" R2_SECRET_ACCESS_KEY)"
R2_ACCOUNT_ID="$(read_env_var_or_current "$ENV_FILE" R2_ACCOUNT_ID)"
SUPABASE_DB_PASSWORD="$(read_env_var_or_current "$ENV_FILE" SUPABASE_DB_PASSWORD)"
SUPABASE_REF="$(read_env_var_or_current "$ENV_FILE" SUPABASE_REF)"
BACKUP_RETENTION_DAYS="$(read_env_var_or_current "$ENV_FILE" BACKUP_RETENTION_DAYS)"
CHAT_RETENTION_DAYS="$(read_env_var_or_current "$ENV_FILE" CHAT_RETENTION_DAYS)"

# Si no hay una configuración específica para R2, acompasa los snapshots con
# el plazo de chat aprobado. El fallback histórico de 30 días se mantiene hasta
# que se configure la política explícita.
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-${CHAT_RETENTION_DAYS:-30}}"

missing=()
[[ -z "${R2_ACCESS_KEY_ID:-}"     ]] && missing+=("R2_ACCESS_KEY_ID")
[[ -z "${R2_SECRET_ACCESS_KEY:-}" ]] && missing+=("R2_SECRET_ACCESS_KEY")
[[ -z "${R2_ACCOUNT_ID:-}"        ]] && missing+=("R2_ACCOUNT_ID")
[[ -z "${SUPABASE_DB_PASSWORD:-}" ]] && missing+=("SUPABASE_DB_PASSWORD")
[[ -z "${SUPABASE_REF:-}"         ]] && missing+=("SUPABASE_REF")

if [[ ${#missing[@]} -gt 0 ]]; then
    echo "ERROR: Variables de entorno faltantes en $ENV_FILE:" >&2
    printf '  - %s\n' "${missing[@]}" >&2
    exit 1
fi

if [[ ! "$RETENTION_DAYS" =~ ^[1-9][0-9]{0,3}$ ]] || (( RETENTION_DAYS > 3650 )); then
    echo "ERROR: BACKUP_RETENTION_DAYS/CHAT_RETENTION_DAYS debe ser un entero entre 1 y 3650" >&2
    exit 1
fi

# ── AWS CLI apuntando a R2 ────────────────────────────────────────────────
export AWS_ACCESS_KEY_ID="$R2_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$R2_SECRET_ACCESS_KEY"
# R2 exige región "auto"; se fija explícito para que el .env no interfiera.
export AWS_DEFAULT_REGION="auto"
R2_ENDPOINT="https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

# ── Main ──────────────────────────────────────────────────────────────────
BACKUP_TS=$(date -u +"%Y-%m-%d_%H%M%S")
BACKUP_FILE="${BACKUP_TS}_full.sql.gz"

echo "[$(timestamp)] === Residencia Fiscal VPS Backup ==="
echo "[$(timestamp)] Timestamp: $BACKUP_TS (UTC)"
echo "[$(timestamp)] Destino:   s3://${R2_BUCKET}/${BACKUP_FILE}"

# 1. pg_dump contra el pooler de Supabase (puerto 5432 = session mode)
DB_URL="postgresql://postgres.${SUPABASE_REF}:${SUPABASE_DB_PASSWORD}@${POOLER_HOST}:5432/postgres"

SCHEMA_ARGS=()
for schema in "${BACKUP_SCHEMAS[@]}"; do
    SCHEMA_ARGS+=("--schema=$schema")
done

echo "[$(timestamp)] Dumping schemas: ${BACKUP_SCHEMAS[*]}..."
PGPASSWORD="$SUPABASE_DB_PASSWORD" pg_dump \
    --dbname="$DB_URL" \
    "${SCHEMA_ARGS[@]}" \
    --no-password \
    -f "${TEMP_DIR}/full.sql"

# 2. Cabecera de metadatos + gzip
echo "[$(timestamp)] Comprimiendo backup..."
{
    echo "-- Residencia Fiscal Full Backup"
    echo "-- Timestamp: $BACKUP_TS"
    echo "-- Project: $SUPABASE_REF"
    echo "-- Schemas: ${BACKUP_SCHEMAS[*]}"
    echo "-- Generated by: VPS systemd timer (residenciafiscal-backup.timer)"
    echo ""
    cat "${TEMP_DIR}/full.sql"
} | gzip > "${TEMP_DIR}/${BACKUP_FILE}"

SIZE=$(du -h "${TEMP_DIR}/${BACKUP_FILE}" | cut -f1)
echo "[$(timestamp)] Comprimido: ${BACKUP_FILE} (${SIZE})"

# 3. Subir a R2
echo "[$(timestamp)] Subiendo a R2..."
aws s3 cp \
    "${TEMP_DIR}/${BACKUP_FILE}" \
    "s3://${R2_BUCKET}/${BACKUP_FILE}" \
    --endpoint-url "$R2_ENDPOINT"

# 4. Verificar que el objeto existe en destino
aws s3 ls \
    "s3://${R2_BUCKET}/${BACKUP_FILE}" \
    --endpoint-url "$R2_ENDPOINT" > /dev/null
echo "[$(timestamp)] Upload verificado."

# 5. Retención
echo "[$(timestamp)] Limpiando backups de más de ${RETENTION_DAYS} días..."
CUTOFF_DATE=$(date -u -d "${RETENTION_DAYS} days ago" +%Y-%m-%d)

aws s3 ls "s3://${R2_BUCKET}/" --endpoint-url "$R2_ENDPOINT" | \
while read -r line; do
    FILE=$(echo "$line" | awk '{print $4}')
    if [[ -n "$FILE" ]]; then
        FILE_DATE=$(echo "$FILE" | cut -d'_' -f1)
        if [[ "$FILE_DATE" < "$CUTOFF_DATE" ]]; then
            echo "[$(timestamp)] Eliminando backup antiguo: $FILE"
            aws s3 rm "s3://${R2_BUCKET}/$FILE" --endpoint-url "$R2_ENDPOINT"
        fi
    fi
done

# 6. Guardián de cobertura: ¿ha aparecido un schema con tablas que nadie declaró?
#
# Va al final y a propósito: el objeto ya está subido y verificado, así que un
# schema nuevo alerta por Telegram sin dejar la noche sin backup. El fallo que
# evita es el peor de todos, porque es silencioso: alguien crea un schema, mete
# datos y el dump sigue saliendo verde sin ellos. Pasó aquí en pequeño — el chat
# se persiste en `private`, no en `public`.
echo "[$(timestamp)] Comprobando cobertura de schemas..."
KNOWN_SCHEMAS=("${BACKUP_SCHEMAS[@]}" "${IGNORED_SCHEMAS[@]}")
KNOWN_LIST="$(printf "'%s'," "${KNOWN_SCHEMAS[@]}")"
KNOWN_LIST="${KNOWN_LIST%,}"

UNKNOWN_SCHEMAS="$(
    PGPASSWORD="$SUPABASE_DB_PASSWORD" psql "$DB_URL" -At --no-password -c "
        SELECT n.nspname
        FROM pg_namespace n
        JOIN pg_class c ON c.relnamespace = n.oid AND c.relkind IN ('r', 'p')
        WHERE n.nspname NOT LIKE 'pg\_%'
          AND n.nspname <> 'information_schema'
          AND n.nspname NOT IN (${KNOWN_LIST})
        GROUP BY n.nspname
        ORDER BY n.nspname
    " 2>&1
)" || UNKNOWN_SCHEMAS="ERROR: no se pudo consultar la lista de schemas"

if [[ -n "$UNKNOWN_SCHEMAS" ]]; then
    echo "[$(timestamp)] === Backup subido, pero la cobertura es incompleta ===" >&2
    echo "[$(timestamp)] Schemas con tablas fuera del dump: ${UNKNOWN_SCHEMAS//$'\n'/, }" >&2
    echo "[$(timestamp)] Añádelos a BACKUP_SCHEMAS o justifícalos en IGNORED_SCHEMAS." >&2
    exit 1
fi

echo "[$(timestamp)] === Backup completado exitosamente ==="
