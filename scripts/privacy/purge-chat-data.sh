#!/bin/bash
# Purgado diario del chat según el plazo de retención aprobado.
#
# Sigue el patrón de Presupuestor: desactivado por defecto, dry-run por defecto
# y límite de lote. Sin CHAT_RETENTION_DAYS el job falla cerrado y no inventa
# una política legal. La función SQL solo devuelve contadores; nunca se
# imprimen preguntas, respuestas ni diagnósticos.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${PRIVACY_ENV_FILE:-$PROJECT_ROOT/.env}"
POOLER_HOST="${PRIVACY_POOLER_HOST:-aws-0-eu-west-1.pooler.supabase.com}"

# shellcheck source=../backup/lib-read-env.sh
source "$SCRIPT_DIR/../backup/lib-read-env.sh"

if [[ ! -f "$ENV_FILE" && -z "${CHAT_RETENTION_PURGE_ENABLED:-}" ]]; then
    echo "Retención desactivada: no se ejecuta el purgado" >&2
    exit 0
fi

PURGE_ENABLED="$(read_env_var_or_current "$ENV_FILE" CHAT_RETENTION_PURGE_ENABLED)"
PURGE_ENABLED="${PURGE_ENABLED:-false}"
DRY_RUN="$(read_env_var_or_current "$ENV_FILE" CHAT_RETENTION_DRY_RUN)"
DRY_RUN="${DRY_RUN:-true}"
BATCH_LIMIT="$(read_env_var_or_current "$ENV_FILE" CHAT_RETENTION_BATCH_LIMIT)"
BATCH_LIMIT="${BATCH_LIMIT:-500}"

case "${PURGE_ENABLED,,}" in
    true|1|yes) ;;
    false|0|no) echo "Retención desactivada: no se ejecuta el purgado" >&2; exit 0 ;;
    *) echo "ERROR: CHAT_RETENTION_PURGE_ENABLED debe ser true o false" >&2; exit 1 ;;
esac

case "${DRY_RUN,,}" in
    true|1|yes) DRY_RUN_SQL=true ;;
    false|0|no) DRY_RUN_SQL=false ;;
    *) echo "ERROR: CHAT_RETENTION_DRY_RUN debe ser true o false" >&2; exit 1 ;;
esac

if [[ ! "$BATCH_LIMIT" =~ ^[1-9][0-9]{0,5}$ ]] || (( BATCH_LIMIT > 100000 )); then
    echo "ERROR: CHAT_RETENTION_BATCH_LIMIT debe ser un entero entre 1 y 100000" >&2
    exit 1
fi

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
# C va primero, y el orden es parte del contrato. `deep_research_jobs` cae en
# cascada al borrar su conversación, así que purgar el chat antes dejaría esos
# jobs fuera de la auditoría y del límite de lote: el contador saldría a cero
# habiendo borrado. Al revés no hay hueco, porque un job posterior al cutoff
# implica una conversación posterior al cutoff —`authorize_chat_conversation`
# refresca `updated_at` antes de crearlo— y esa conversación no se purga.
DEEP_RESULT="$(PGPASSWORD="$SUPABASE_DB_PASSWORD" psql \
    "$DB_URL" \
    --no-password \
    --no-align \
    --tuples-only \
    -v ON_ERROR_STOP=1 \
    -c "SELECT private.purge_expired_deep_research_jobs('$CUTOFF'::timestamptz, ${DRY_RUN_SQL}, ${BATCH_LIMIT});")"
echo "$DEEP_RESULT"

# `batch_overflow` significa que C encontró más candidatos de los permitidos y
# no borró ninguno, a propósito. Seguir purgando el chat borraría en cascada
# justo esos jobs, que es lo que el límite acababa de rechazar: se para aquí y
# el fallo llega por Telegram para que lo mire una persona.
#
# La condición se lee del resultado de la RPC, no de la variable de bash: en
# dry-run no hay cascada que evitar y la observación del chat debe seguir.
if printf '%s' "$DEEP_RESULT" | grep -Eq '"status"[[:space:]]*:[[:space:]]*"batch_overflow"' \
    && printf '%s' "$DEEP_RESULT" | grep -Eq '"dry_run"[[:space:]]*:[[:space:]]*false'; then
    echo "ERROR: el purgado de investigación profunda superó el límite de lote; no se purga el chat" >&2
    exit 1
fi

RESULT="$(PGPASSWORD="$SUPABASE_DB_PASSWORD" psql \
    "$DB_URL" \
    --no-password \
    --no-align \
    --tuples-only \
    -v ON_ERROR_STOP=1 \
    -c "SELECT private.purge_expired_chat_data('$CUTOFF'::timestamptz, ${DRY_RUN_SQL}, ${BATCH_LIMIT});")"
echo "$RESULT"
