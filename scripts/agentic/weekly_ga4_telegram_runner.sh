#!/usr/bin/env bash
# Informe semanal de tráfico de residenciafiscal.org enviado por Telegram.
#
# Lo dispara `residenciafiscal-weekly-ga4-telegram.timer` cada lunes a las 09:00
# (Europe/Madrid). Si el envío falla, intenta avisar por Telegram del fallo con
# el intérprete del sistema, para que un entorno roto no silencie la alerta.
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

ENABLED="$(read_env_value WEEKLY_GA4_TELEGRAM_ENABLED || true)"
if [[ "${ENABLED:-true}" =~ ^([Ff]alse|0|no|NO)$ ]]; then
  echo "WEEKLY_GA4_TELEGRAM_ENABLED=false; se omite el envío."
  exit 0
fi

# El informe corre sobre PostHog con la librería estándar. Las dependencias de
# Google solo se instalan cuando la fuente correspondiente está declarada, para
# no depender de PyPI en rutas que no se usan.
UV_EXTRA_ARGS=()
if [[ -n "$(read_env_value GA4_PROPERTY_ID || true)" ]]; then
  UV_EXTRA_ARGS+=(--with google-analytics-data --with google-auth)
fi
if [[ -n "$(read_env_value GSC_SITE_URL || true)" ]]; then
  UV_EXTRA_ARGS+=(--with google-api-python-client --with google-auth)
fi

uv run "${UV_EXTRA_ARGS[@]}" python scripts/weekly_ga4_telegram.py "$@" || {
  exit_code=$?
  echo "el informe semanal de tráfico falló con exit ${exit_code}" >&2
  python3 scripts/weekly_ga4_telegram.py \
    --failure-alert "El job semanal de tráfico no pudo completarse. Exit: ${exit_code}." \
    --failure-exit-code "$exit_code" || true
  exit "$exit_code"
}
