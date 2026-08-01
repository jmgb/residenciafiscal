#!/bin/bash
# Supresión operativa de una conversación tras verificar la identidad fuera de
# la base de datos. El UUID visible de la URL no prueba por sí solo la identidad.
#
# Uso:
#   delete-chat-conversation.sh --conversation-id ID --ticket TICKET --confirm-delete

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${PRIVACY_ENV_FILE:-$PROJECT_ROOT/.env}"
POOLER_HOST="${PRIVACY_POOLER_HOST:-aws-0-eu-west-1.pooler.supabase.com}"

# shellcheck source=../backup/lib-read-env.sh
source "$SCRIPT_DIR/../backup/lib-read-env.sh"

CONVERSATION_ID=""
TICKET=""
CONFIRM_DELETE=false

usage() {
    echo "Uso: $0 --conversation-id ID --ticket TICKET --confirm-delete" >&2
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --conversation-id)
            [[ $# -ge 2 ]] || { usage; exit 2; }
            CONVERSATION_ID="$2"
            shift 2
            ;;
        --ticket)
            [[ $# -ge 2 ]] || { usage; exit 2; }
            TICKET="$2"
            shift 2
            ;;
        --confirm-delete)
            CONFIRM_DELETE=true
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            usage
            exit 2
            ;;
    esac
done

if [[ -z "$CONVERSATION_ID" || -z "$TICKET" || "$CONFIRM_DELETE" != true ]]; then
    echo "ERROR: exige conversación, ticket y --confirm-delete" >&2
    usage
    exit 2
fi

if [[ ! "$CONVERSATION_ID" =~ ^[A-Za-z0-9_-]{1,128}$ ]]; then
    echo "ERROR: identificador de conversación inválido" >&2
    exit 2
fi

if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: .env no encontrado en $ENV_FILE" >&2
    exit 1
fi

SUPABASE_DB_PASSWORD="$(read_env_var_or_current "$ENV_FILE" SUPABASE_DB_PASSWORD)"
SUPABASE_REF="$(read_env_var_or_current "$ENV_FILE" SUPABASE_REF)"
if [[ -z "$SUPABASE_DB_PASSWORD" || -z "$SUPABASE_REF" ]]; then
    echo "ERROR: faltan SUPABASE_DB_PASSWORD o SUPABASE_REF" >&2
    exit 1
fi

if ! command -v psql >/dev/null 2>&1; then
    echo "ERROR: psql no encontrado" >&2
    exit 1
fi

DB_URL="postgresql://postgres.${SUPABASE_REF}:${SUPABASE_DB_PASSWORD}@${POOLER_HOST}:5432/postgres"
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Ejecutando supresión del ticket ${TICKET}..."
PGPASSWORD="$SUPABASE_DB_PASSWORD" psql \
    "$DB_URL" \
    --no-password \
    --no-align \
    --tuples-only \
    -v ON_ERROR_STOP=1 \
    -c "SELECT private.delete_chat_conversation('$CONVERSATION_ID');"

echo "La copia primaria se ha procesado. Las copias R2 desaparecen conforme a BACKUP_RETENTION_DAYS."
