#!/bin/bash
# Instala el timer diario de purgado del chat en el VPS.
# Ejecutar en el VPS con sudo después de configurar CHAT_RETENTION_DAYS.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"
SYSTEMD_DIR="/etc/systemd/system"
SERVICE="residenciafiscal-chat-retention.service"
TIMER="residenciafiscal-chat-retention.timer"

if [[ "$EUID" -ne 0 ]]; then
    echo "ERROR: este script requiere sudo" >&2
    exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: no se encontró $ENV_FILE" >&2
    exit 1
fi

# shellcheck source=../backup/lib-read-env.sh
source "$SCRIPT_DIR/../backup/lib-read-env.sh"

missing=()
for key in SUPABASE_DB_PASSWORD SUPABASE_REF CHAT_RETENTION_DAYS; do
    [[ -z "$(read_env_var "$ENV_FILE" "$key")" ]] && missing+=("$key")
done
if [[ ${#missing[@]} -gt 0 ]]; then
    echo "ERROR: faltan claves en ${ENV_FILE}: ${missing[*]}" >&2
    exit 1
fi

if ! command -v psql >/dev/null 2>&1; then
    echo "ERROR: psql no encontrado; instala postgresql-client antes" >&2
    exit 1
fi

cp "$SCRIPT_DIR/$SERVICE" "$SYSTEMD_DIR/$SERVICE"
cp "$SCRIPT_DIR/$TIMER" "$SYSTEMD_DIR/$TIMER"
systemctl daemon-reload
systemctl enable "$TIMER"
systemctl start "$TIMER"

echo "=== Timer de retención instalado ==="
systemctl list-timers "$TIMER" --no-pager
echo "Ejecución manual: sudo systemctl start $SERVICE"
