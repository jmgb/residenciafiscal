#!/bin/bash
# Comprueba que el último backup en R2 es reciente y legible.
# Corre en un timer independiente del backup: responde "¿hay en R2 un backup
# reciente y descomprimible?", no "¿terminó bien el job de anoche?".

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${BACKUP_FRESHNESS_ENV_FILE:-$PROJECT_ROOT/.env}"
NOTIFY_SCRIPT="${BACKUP_FRESHNESS_NOTIFY_SCRIPT:-$SCRIPT_DIR/notify-backup-failure.sh}"
VERIFY_SCRIPT="$SCRIPT_DIR/verify-backup-contract.sh"

R2_BUCKET="${BACKUP_R2_BUCKET:-residenciafiscal-backup}"
MAX_AGE_HOURS="${BACKUP_FRESHNESS_MAX_AGE_HOURS:-30}"
TEMP_DIR="/tmp/residenciafiscal-backup-freshness-$$"

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
    echo "[$(timestamp)] Backup freshness FAILED: ${details}" >&2

    if [[ -f "$NOTIFY_SCRIPT" ]]; then
        BACKUP_FAILURE_TITLE="Residencia Fiscal backup freshness FAILED" \
        BACKUP_FAILURE_REFERENCE="residenciafiscal-backup-freshness" \
        BACKUP_FAILURE_DETAILS="$details" \
        BACKUP_FAILURE_SERVICE="residenciafiscal-backup-freshness.service" \
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

missing=()
[[ -z "${R2_ACCESS_KEY_ID:-}" ]] && missing+=("R2_ACCESS_KEY_ID")
[[ -z "${R2_SECRET_ACCESS_KEY:-}" ]] && missing+=("R2_SECRET_ACCESS_KEY")
[[ -z "${R2_ACCOUNT_ID:-}" ]] && missing+=("R2_ACCOUNT_ID")

if [[ ${#missing[@]} -gt 0 ]]; then
    fail_with_alert "Faltan variables R2 en ${ENV_FILE}: ${missing[*]}"
fi

export AWS_ACCESS_KEY_ID="$R2_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$R2_SECRET_ACCESS_KEY"
export AWS_DEFAULT_REGION="auto"
R2_ENDPOINT="https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

echo "[$(timestamp)] Comprobando último backup en s3://${R2_BUCKET}/..."

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

BACKUP_STAMP="${LATEST_BACKUP%_full.sql.gz}"
BACKUP_DATE="${BACKUP_STAMP%%_*}"
BACKUP_TIME="${BACKUP_STAMP#*_}"
BACKUP_TIME_FORMATTED="${BACKUP_TIME:0:2}:${BACKUP_TIME:2:2}:${BACKUP_TIME:4:2}"
BACKUP_EPOCH="$(date -u -d "${BACKUP_DATE} ${BACKUP_TIME_FORMATTED} UTC" +%s)"
NOW_EPOCH="$(date -u +%s)"
AGE_SECONDS=$((NOW_EPOCH - BACKUP_EPOCH))
MAX_AGE_SECONDS=$((MAX_AGE_HOURS * 3600))

if (( AGE_SECONDS < 0 )); then
    fail_with_alert "El último backup ${LATEST_BACKUP} tiene fecha futura"
fi

if (( AGE_SECONDS > MAX_AGE_SECONDS )); then
    AGE_HOURS=$((AGE_SECONDS / 3600))
    fail_with_alert "El último backup ${LATEST_BACKUP} tiene ${AGE_HOURS}h, más de ${MAX_AGE_HOURS}h"
fi

LOCAL_BACKUP="${TEMP_DIR}/${LATEST_BACKUP}"

if ! aws s3 cp "s3://${R2_BUCKET}/${LATEST_BACKUP}" "$LOCAL_BACKUP" --endpoint-url "$R2_ENDPOINT" >/dev/null; then
    fail_with_alert "No se pudo descargar ${LATEST_BACKUP} desde R2"
fi

if ! gzip -t "$LOCAL_BACKUP"; then
    fail_with_alert "El backup ${LATEST_BACKUP} no pasa gzip -t (corrupto o incompleto)"
fi

if [[ ! -f "$VERIFY_SCRIPT" ]]; then
    fail_with_alert "No existe el verificador de contrato: $VERIFY_SCRIPT"
fi

LOCAL_SQL="${TEMP_DIR}/${LATEST_BACKUP%.gz}"
if ! gunzip -c "$LOCAL_BACKUP" > "$LOCAL_SQL"; then
    fail_with_alert "No se pudo descomprimir ${LATEST_BACKUP} para validar su contrato"
fi

if ! VERIFY_OUTPUT="$(/bin/bash "$VERIFY_SCRIPT" "$LOCAL_SQL" 2>&1)"; then
    fail_with_alert "El backup ${LATEST_BACKUP} no cumple el contrato: ${VERIFY_OUTPUT}"
fi

AGE_HOURS=$((AGE_SECONDS / 3600))
echo "[$(timestamp)] Backup freshness OK: ${LATEST_BACKUP} (${AGE_HOURS}h old, gzip and SQL contract ok)"
