#!/usr/bin/env bash
# ============================================================================
# Instalar el timer semanal de tráfico de Residencia Fiscal
# ============================================================================
# Se ejecuta en la máquina que dispara los informes, SIN sudo, porque las
# units son de usuario igual que las de los proyectos hermanos:
#
#   bash scripts/agentic/install-weekly-ga4-telegram-timer.sh
#
# Es idempotente: se puede relanzar tras cada `git pull` que toque las units
# para recopiarlas y recargar systemd.
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"
SYSTEMD_DIR="${HOME}/.config/systemd/user"

UNITS=(
    residenciafiscal-weekly-ga4-telegram.service
    residenciafiscal-weekly-ga4-telegram.timer
)
TIMER=residenciafiscal-weekly-ga4-telegram.timer

REQUIRED_KEYS=(
    POSTHOG_QUERY_HOST
    POSTHOG_PROJECT_ID
    POSTHOG_PERSONAL_API_KEY
    TELEGRAM_TOKEN
    TELEGRAM_CHAT_ID
)

if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: no se encontró $ENV_FILE" >&2
    exit 1
fi

missing=()
for key in "${REQUIRED_KEYS[@]}"; do
    grep -q -E "^${key}=." "$ENV_FILE" || missing+=("$key")
done
if [[ ${#missing[@]} -gt 0 ]]; then
    echo "ERROR: faltan claves en .env: ${missing[*]}" >&2
    exit 1
fi

mkdir -p "$SYSTEMD_DIR"
for unit in "${UNITS[@]}"; do
    install -m 644 "${SCRIPT_DIR}/${unit}" "${SYSTEMD_DIR}/${unit}"
    echo "instalado ${SYSTEMD_DIR}/${unit}"
done

systemctl --user daemon-reload
systemctl --user enable --now "$TIMER"

echo
systemctl --user list-timers --all --no-pager | grep -E "UNIT|${TIMER}" || true
