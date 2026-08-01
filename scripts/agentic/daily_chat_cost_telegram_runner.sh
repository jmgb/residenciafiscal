#!/usr/bin/env bash
# Resumen diario del ledger del chat enviado por Telegram.
#
# Lo dispara `residenciafiscal-daily-chat-cost-telegram.timer` cada día a las
# 09:15 (Europe/Madrid), quince minutos después del informe semanal de tráfico
# para no solapar los dos envíos del lunes.
#
# Solo usa la librería estándar: la RPC de Supabase se llama por HTTP, así que
# no depende de PyPI. El `.env` se parsea, nunca se hace `source`.
set -euo pipefail

export HOME="${HOME:-/home/ubuntu}"
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
export TZ="Europe/Madrid"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_DIR"

read_env_value() {
  grep -h -E "^$1=" .env 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '"' | tr -d "'" | tr -d ' '
}

ENABLED="$(read_env_value DAILY_CHAT_COST_TELEGRAM_ENABLED || true)"
if [[ "${ENABLED:-true}" =~ ^([Ff]alse|0|no|NO)$ ]]; then
  echo "DAILY_CHAT_COST_TELEGRAM_ENABLED=false; se omite el envío."
  exit 0
fi

python3 scripts/daily_chat_cost_telegram.py "$@" || {
  exit_code=$?
  echo "el resumen diario del chat falló con exit ${exit_code}" >&2
  exit "$exit_code"
}
