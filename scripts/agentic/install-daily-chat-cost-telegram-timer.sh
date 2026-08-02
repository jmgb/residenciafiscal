#!/usr/bin/env bash
# ============================================================================
# Instalar el timer diario del ledger del chat de Residencia Fiscal
# ============================================================================
# Se ejecuta en la máquina que dispara los informes, SIN sudo, porque las
# units son de usuario igual que las del informe semanal de tráfico:
#
#   bash scripts/agentic/install-daily-chat-cost-telegram-timer.sh
#
# Es idempotente: se puede relanzar tras cada `git pull` que toque las units
# para recopiarlas y recargar systemd.
#
# No va en el VPS `alfredo`, donde corren los timers de sistema del backup y de
# la retención: su `.env` solo tiene las credenciales de `pg_dump`, mientras que
# este resumen llama a la RPC `chat_daily_stats` por HTTP y necesita la clave de
# servicio. Llevarla allí ampliaría su superficie a cambio de nada.
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"
SYSTEMD_DIR="${HOME}/.config/systemd/user"

UNITS=(
    residenciafiscal-daily-chat-cost-telegram.service
    residenciafiscal-daily-chat-cost-telegram.timer
    residenciafiscal-daily-chat-cost-freshness.service
    residenciafiscal-daily-chat-cost-freshness.timer
)
# El guardián se instala con el digest a propósito: vigila que el digest corra,
# y un guardián que se instala aparte es un guardián que se olvida.
TIMERS=(
    residenciafiscal-daily-chat-cost-telegram.timer
    residenciafiscal-daily-chat-cost-freshness.timer
)

REQUIRED_KEYS=(
    SUPABASE_URL
    SUPABASE_SECRET_KEY
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
for timer in "${TIMERS[@]}"; do
    systemctl --user enable --now "$timer"
done

echo
systemctl --user list-timers --all --no-pager |
    grep -E "UNIT|$(IFS='|'; echo "${TIMERS[*]}")" || true
