#!/bin/bash
# Purgado diario del chat según el plazo de retención aprobado.
#
# El plazo es obligatorio: sin CHAT_RETENTION_DAYS el job falla cerrado y no
# inventa una política legal. La función SQL solo devuelve contadores; nunca se
# imprimen preguntas, respuestas ni diagnósticos.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${PRIVACY_ENV_FILE:-$PROJECT_ROOT/.env}"
POOLER_HOST="${PRIVACY_POOLER_HOST:-aws-0-eu-west-1.pooler.supabase.com}"

# shellcheck source=../backup/lib-read-env.sh
source "$SCRIPT_DIR/../backup/lib-read-env.sh"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: .env no encontrado en $ENV_FILE" >&2
    exit 1
fi

SUPABASE_DB_PASSWORD="$(read_env_var_or_current "$ENV_FILE" SUPABASE_DB_PASSWORD)"
SUPABASE_REF="$(read_env_var_or_current "$ENV_FILE" SUPABASE_REF)"
RETENTION_DAYS="$(read_env_var_or_current "$ENV_FILE" CHAT_RETENTION_DAYS)"

if [[ -z "$SUPABASE_DB_PASSWORD" || -z "$SUPABASE_REF" ]]; then
    echo "ERROR: faltan SUPABASE_DB_PASSWORD o SUPABASE_REF" >&2
    exit 1
fi

if [[ -z "$RETENTION_DAYS" ]]; then
    echo "ERROR: Falta CHAT_RETENTION_DAYS; el purgado no se ejecuta" >&2
    exit 1
fi

if [[ ! "$RETENTION_DAYS" =~ ^[1-9][0-9]{0,3}$ ]] || (( RETENTION_DAYS > 3650 )); then
    echo "ERROR: CHAT_RETENTION_DAYS debe ser un entero entre 1 y 3650" >&2
    exit 1
fi

if ! command -v psql >/dev/null 2>&1; then
    echo "ERROR: psql no encontrado" >&2
    exit 1
fi

CUTOFF="$(date -u -d "${RETENTION_DAYS} days ago" +%Y-%m-%dT%H:%M:%SZ)"
DB_URL="postgresql://postgres.${SUPABASE_REF}:${SUPABASE_DB_PASSWORD}@${POOLER_HOST}:5432/postgres"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Purgando chat anterior a ${CUTOFF}..."
PGPASSWORD="$SUPABASE_DB_PASSWORD" psql \
    "$DB_URL" \
    --no-password \
    --no-align \
    --tuples-only \
    -v ON_ERROR_STOP=1 \
    -c "SELECT private.purge_expired_chat_data('$CUTOFF'::timestamptz);"
