#!/bin/bash
# Notifica fallos del subsistema de backup por Telegram.
# Usado por `OnFailure=` de systemd y por los checks de frescura / restore drill.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

ENV_FILE="${BACKUP_FAILURE_ENV_FILE:-$PROJECT_ROOT/.env}"
REFERENCE="${BACKUP_FAILURE_REFERENCE:-residenciafiscal-backup-failure}"
TITLE="${BACKUP_FAILURE_TITLE:-Residencia Fiscal backup FAILED}"
DETAILS="${BACKUP_FAILURE_DETAILS:-}"
SERVICE_NAME="${BACKUP_FAILURE_SERVICE:-residenciafiscal-backup.service}"

# shellcheck source=lib-read-env.sh
source "$SCRIPT_DIR/lib-read-env.sh"

html_escape() {
    sed \
        -e 's/&/\&amp;/g' \
        -e 's/</\&lt;/g' \
        -e 's/>/\&gt;/g'
}

if [[ ! -f "$ENV_FILE" ]]; then
    echo "WARN: .env no encontrado en $ENV_FILE; no se puede notificar el fallo" >&2
    exit 0
fi

TELEGRAM_TOKEN="$(read_env_var "$ENV_FILE" TELEGRAM_TOKEN)"
if [[ -z "$TELEGRAM_TOKEN" ]]; then
    TELEGRAM_TOKEN="$(read_env_var "$ENV_FILE" TELEGRAM_BOT_TOKEN)"
fi
TELEGRAM_CHAT_ID="$(read_env_var "$ENV_FILE" TELEGRAM_CHAT_ID)"

if [[ -z "$TELEGRAM_TOKEN" || -z "$TELEGRAM_CHAT_ID" ]]; then
    echo "WARN: faltan credenciales de Telegram; no se puede notificar el fallo" >&2
    exit 0
fi

STATUS="$((systemctl status "$SERVICE_NAME" --no-pager -l 2>&1 || true) | head -n 14 | html_escape)"
DETAILS_BLOCK=""
if [[ -n "$DETAILS" ]]; then
    DETAILS_BLOCK="$(printf '%s' "$DETAILS" | html_escape)"
fi
NOW_UTC="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

MESSAGE="$(cat <<EOF
<b>[RESIDENCIAFISCAL]</b> ❌ <b>${TITLE}</b>
referencia=<code>${REFERENCE}</code>
timestamp=<code>${NOW_UTC}</code>
${DETAILS_BLOCK}

<pre>${STATUS}</pre>
EOF
)"

curl -sS --max-time 8 -X POST \
    "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
    --data-urlencode "parse_mode=HTML" \
    --data-urlencode "text=${MESSAGE}" \
    -o /dev/null \
    || echo "WARN: fallo enviando la notificación de Telegram" >&2
