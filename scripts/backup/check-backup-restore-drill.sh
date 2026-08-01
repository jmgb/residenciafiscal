#!/bin/bash
# Simulacro mensual no destructivo: descarga y descomprime el último backup de R2
# mediante restore-from-r2.sh --verify-only. Nunca escribe en la base de datos.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${BACKUP_RESTORE_DRILL_ENV_FILE:-$PROJECT_ROOT/.env}"
RESTORE_SCRIPT="${BACKUP_RESTORE_DRILL_RESTORE_SCRIPT:-$SCRIPT_DIR/restore-from-r2.sh}"
NOTIFY_SCRIPT="${BACKUP_RESTORE_DRILL_NOTIFY_SCRIPT:-$SCRIPT_DIR/notify-backup-failure.sh}"

R2_BUCKET="${BACKUP_R2_BUCKET:-residenciafiscal-backup}"
TEMP_DIR="/tmp/residenciafiscal-backup-restore-drill-$$"

cleanup() {
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

mkdir -p "$TEMP_DIR"

fail_with_alert() {
    local details="$1"
    echo "[$(timestamp)] Backup restore drill FAILED: ${details}" >&2

    if [[ -f "$NOTIFY_SCRIPT" ]]; then
        BACKUP_FAILURE_TITLE="Residencia Fiscal backup restore drill FAILED" \
        BACKUP_FAILURE_REFERENCE="residenciafiscal-backup-restore-drill" \
        BACKUP_FAILURE_DETAILS="$details" \
        BACKUP_FAILURE_SERVICE="residenciafiscal-backup-restore-drill.service" \
            /bin/bash "$NOTIFY_SCRIPT" || true
    else
        echo "[$(timestamp)] WARN: notify script no encontrado: $NOTIFY_SCRIPT" >&2
    fi

    exit 1
}

# NO usar `source` sobre el .env (ver lib-read-env.sh).
# shellcheck source=lib-read-env.sh
source "$SCRIPT_DIR/lib-read-env.sh"
R2_ACCESS_KEY_ID="$(read_env_var_or_current "$ENV_FILE" R2_ACCESS_KEY_ID)"
R2_SECRET_ACCESS_KEY="$(read_env_var_or_current "$ENV_FILE" R2_SECRET_ACCESS_KEY)"
R2_ACCOUNT_ID="$(read_env_var_or_current "$ENV_FILE" R2_ACCOUNT_ID)"
SUPABASE_DB_PASSWORD="$(read_env_var_or_current "$ENV_FILE" SUPABASE_DB_PASSWORD)"
SUPABASE_REF="$(read_env_var_or_current "$ENV_FILE" SUPABASE_REF)"

missing=()
[[ -z "${R2_ACCESS_KEY_ID:-}" ]] && missing+=("R2_ACCESS_KEY_ID")
[[ -z "${R2_SECRET_ACCESS_KEY:-}" ]] && missing+=("R2_SECRET_ACCESS_KEY")
[[ -z "${R2_ACCOUNT_ID:-}" ]] && missing+=("R2_ACCOUNT_ID")
[[ -z "${SUPABASE_DB_PASSWORD:-}" ]] && missing+=("SUPABASE_DB_PASSWORD")
[[ -z "${SUPABASE_REF:-}" ]] && missing+=("SUPABASE_REF")

if [[ ${#missing[@]} -gt 0 ]]; then
    fail_with_alert "Faltan variables R2 en ${ENV_FILE}: ${missing[*]}"
fi

if [[ ! -f "$RESTORE_SCRIPT" ]]; then
    fail_with_alert "No existe el script de restore: $RESTORE_SCRIPT"
fi

export AWS_ACCESS_KEY_ID="$R2_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$R2_SECRET_ACCESS_KEY"
export AWS_DEFAULT_REGION="auto"
R2_ENDPOINT="https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

echo "[$(timestamp)] Buscando el último backup en s3://${R2_BUCKET}/..."

if ! BACKUP_LISTING="$(aws s3 ls "s3://${R2_BUCKET}/" --endpoint-url "$R2_ENDPOINT" 2>&1)"; then
    fail_with_alert "No se pudo listar s3://${R2_BUCKET}/: ${BACKUP_LISTING}"
fi

LATEST_BACKUP="$(
    printf '%s\n' "$BACKUP_LISTING" \
        | awk '{print $4}' \
        | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{6}_full\.sql\.gz$' \
        | sort \
        | tail -1 || true
)"

if [[ -z "$LATEST_BACKUP" ]]; then
    fail_with_alert "No hay backups en s3://${R2_BUCKET}/"
fi

BACKUP_NAME="${LATEST_BACKUP%_full.sql.gz}"
DRILL_LOG="$TEMP_DIR/restore-drill.log"

echo "[$(timestamp)] Ejecutando verify-only sobre ${BACKUP_NAME}..."
if ! BACKUP_ENV_FILE="$ENV_FILE" \
    BACKUP_VERIFY_LIVE_CONTRACT=1 \
    /bin/bash "$RESTORE_SCRIPT" --verify-only "$BACKUP_NAME" > "$DRILL_LOG" 2>&1; then
    fail_with_alert "El verify-only falló para ${BACKUP_NAME}: $(tail -20 "$DRILL_LOG")"
fi

LINES="$(grep -Eo '\([0-9]+ lines\)' "$DRILL_LOG" | tail -1 | tr -cd '0-9' || true)"
if [[ -n "$LINES" ]]; then
    echo "[$(timestamp)] Backup restore drill OK: ${LATEST_BACKUP} (${LINES} lines, contract matches live Supabase)"
else
    echo "[$(timestamp)] Backup restore drill OK: ${LATEST_BACKUP} (contract matches live Supabase)"
fi
