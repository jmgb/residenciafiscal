#!/usr/bin/env bash
# ============================================================================
# Instalar el timer semanal de tráfico de Residencia Fiscal
# ============================================================================
# Se ejecuta EN EL VPS `alfredo` y necesita sudo, porque desde el 2026-08-11 las
# units son de sistema y no de usuario:
#
#   ssh alfredo
#   bash /home/ubuntu/residenciafiscal/scripts/agentic/install-weekly-ga4-telegram-timer.sh
#
# Por qué cambió: mientras vivían en el portátil como units de usuario, un lunes
# con la máquina apagada a las 09:00 dejaba el informe sin enviar hasta el
# arranque (2026-08-10: los cinco informes hermanos se dispararon de golpe a las
# 23:07 por el catch-up de Persistent=true). El VPS está siempre encendido y su
# journal sobrevive a los reinicios.
#
# Es idempotente: se puede relanzar tras cada `git pull` que toque las units
# para recopiarlas y recargar systemd.
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"
SYSTEMD_DIR="/etc/systemd/system"

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

for unit in "${UNITS[@]}"; do
    sudo install -o root -g root -m 644 "${SCRIPT_DIR}/${unit}" "${SYSTEMD_DIR}/${unit}"
    echo "instalado ${SYSTEMD_DIR}/${unit}"
done

sudo systemctl daemon-reload
sudo systemctl enable --now "$TIMER"

echo
systemctl list-timers --all --no-pager | grep -E "UNIT|${TIMER}" || true
