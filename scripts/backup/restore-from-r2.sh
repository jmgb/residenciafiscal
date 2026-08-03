#!/bin/bash
# ============================================================================
# Residencia Fiscal — Restaurar un backup de Supabase desde Cloudflare R2
# ============================================================================
# Uso:
#   ./scripts/backup/restore-from-r2.sh                          # listar backups
#   ./scripts/backup/restore-from-r2.sh --verify-only 2026-07-31_020314
#   ./scripts/backup/restore-from-r2.sh 2026-07-31_020314        # restaurar (destructivo)
#
# Requisitos: aws CLI, psql, credenciales R2 + SUPABASE_DB_PASSWORD en el .env
# de la raíz del repositorio.
# Docs: docs/operations/BACKUPS.md
# ============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
R2_BUCKET="${BACKUP_R2_BUCKET:-residenciafiscal-backup}"
POOLER_HOST="${BACKUP_POOLER_HOST:-aws-0-eu-west-1.pooler.supabase.com}"
TEMP_DIR="/tmp/residenciafiscal-restore-$$"
VERIFY_SCRIPT="$SCRIPT_DIR/verify-backup-contract.sh"
REQUIRED_PUBLIC_FUNCTIONS=(
    public.create_chat_request
    public.complete_chat_request
    public.fail_chat_request
    public.create_deep_research_job
    public.get_deep_research_job
    public.update_deep_research_job
    public.cancel_deep_research_job
)

# NO usar `source` sobre el .env (ver lib-read-env.sh).
ENV_FILE="${BACKUP_ENV_FILE:-$PROJECT_ROOT/.env}"
# shellcheck source=lib-read-env.sh
source "$SCRIPT_DIR/lib-read-env.sh"
R2_ACCESS_KEY_ID="$(read_env_var_or_current "$ENV_FILE" R2_ACCESS_KEY_ID)"
R2_SECRET_ACCESS_KEY="$(read_env_var_or_current "$ENV_FILE" R2_SECRET_ACCESS_KEY)"
R2_ACCOUNT_ID="$(read_env_var_or_current "$ENV_FILE" R2_ACCOUNT_ID)"
SUPABASE_DB_PASSWORD="$(read_env_var_or_current "$ENV_FILE" SUPABASE_DB_PASSWORD)"
SUPABASE_REF="$(read_env_var_or_current "$ENV_FILE" SUPABASE_REF)"
export SUPABASE_DB_PASSWORD

check_env() {
    local missing=()

    [[ -z "${R2_ACCESS_KEY_ID:-}" ]] && missing+=("R2_ACCESS_KEY_ID")
    [[ -z "${R2_SECRET_ACCESS_KEY:-}" ]] && missing+=("R2_SECRET_ACCESS_KEY")
    [[ -z "${R2_ACCOUNT_ID:-}" ]] && missing+=("R2_ACCOUNT_ID")

    if [[ ${#missing[@]} -gt 0 ]]; then
        echo -e "${RED}❌ Faltan variables de entorno:${NC}"
        printf '   - %s\n' "${missing[@]}"
        echo ""
        echo "Defínelas en $ENV_FILE o expórtalas en tu shell."
        exit 1
    fi
}

# Solo hace falta para restaurar de verdad: listar y verificar no tocan la BD.
check_restore_env() {
    if [[ -z "${SUPABASE_REF:-}" ]]; then
        echo -e "${RED}❌ Falta SUPABASE_REF: no se puede construir la URL de la base de datos.${NC}"
        exit 1
    fi
}

check_live_verify_env() {
    local missing=()

    [[ -z "${SUPABASE_REF:-}" ]] && missing+=("SUPABASE_REF")
    [[ -z "${SUPABASE_DB_PASSWORD:-}" ]] && missing+=("SUPABASE_DB_PASSWORD")
    command -v psql >/dev/null 2>&1 || missing+=("psql")

    if [[ ${#missing[@]} -gt 0 ]]; then
        echo -e "${RED}❌ No se puede comparar el backup con Supabase; falta: ${missing[*]}${NC}"
        exit 1
    fi
}

configure_aws() {
    export AWS_ACCESS_KEY_ID="$R2_ACCESS_KEY_ID"
    export AWS_SECRET_ACCESS_KEY="$R2_SECRET_ACCESS_KEY"
    export AWS_DEFAULT_REGION="auto"
    export R2_ENDPOINT="https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
}

list_backups() {
    echo -e "${BLUE}📁 Backups disponibles en s3://${R2_BUCKET}:${NC}"
    echo "=========================================="

    aws s3 ls "s3://${R2_BUCKET}/" \
        --endpoint-url "$R2_ENDPOINT" \
        --human-readable 2>/dev/null | \
    while read -r line; do
        SIZE=$(echo "$line" | awk '{print $3 " " $4}')
        FILE=$(echo "$line" | awk '{print $5}')
        BACKUP_NAME=$(echo "$FILE" | sed 's/_full.sql.gz$//')
        echo -e "  ${GREEN}${BACKUP_NAME}${NC}  (${SIZE})"
    done

    echo "=========================================="
    echo ""
    echo -e "Uso: ${YELLOW}$0 <backup_name>${NC}"
    echo -e "Ej.: ${YELLOW}$0 2026-07-31_020314${NC}"
}

download_backup() {
    local backup_name="$1"
    local filename="${backup_name}_full.sql.gz"

    echo -e "${BLUE}⬇️  Descargando backup: ${filename}${NC}"

    mkdir -p "$TEMP_DIR"

    aws s3 cp \
        "s3://${R2_BUCKET}/${filename}" \
        "${TEMP_DIR}/${filename}" \
        --endpoint-url "$R2_ENDPOINT"

    if [[ ! -f "${TEMP_DIR}/${filename}" ]]; then
        echo -e "${RED}❌ No se pudo descargar el backup${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ Descargado en ${TEMP_DIR}/${filename}${NC}"
}

decompress_backup() {
    local backup_name="$1"
    local filename="${backup_name}_full.sql.gz"
    local sql_file="${TEMP_DIR}/${backup_name}_full.sql"

    echo -e "${BLUE}🗜️  Descomprimiendo...${NC}"

    gunzip -k -f "${TEMP_DIR}/${filename}"

    if [[ ! -f "$sql_file" ]]; then
        echo -e "${RED}❌ No se pudo descomprimir el backup${NC}"
        exit 1
    fi

    local lines
    lines=$(wc -l < "$sql_file")
    echo -e "${GREEN}✅ Descomprimido: ${sql_file} (${lines} lines)${NC}"
}

verify_backup_contract() {
    local backup_name="$1"
    local sql_file="${TEMP_DIR}/${backup_name}_full.sql"

    if [[ ! -f "$VERIFY_SCRIPT" ]]; then
        echo -e "${RED}❌ Verificador de backup no encontrado: ${VERIFY_SCRIPT}${NC}"
        exit 1
    fi

    if [[ "${BACKUP_VERIFY_LIVE_CONTRACT:-0}" == "1" ]]; then
        check_live_verify_env
        local db_url="postgresql://postgres.${SUPABASE_REF}:${SUPABASE_DB_PASSWORD}@${POOLER_HOST}:5432/postgres"
        local application_tables
        local required_functions

        application_tables="$({
            PGPASSWORD="$SUPABASE_DB_PASSWORD" psql "$db_url" -At --no-password -c "
                SELECT format('%I.%I', table_schema, table_name)
                FROM information_schema.tables
                WHERE table_schema IN ('public', 'private')
                  AND table_type = 'BASE TABLE'
                ORDER BY table_schema, table_name
            "
        } | paste -sd' ' -)"
        required_functions="$(printf '%s\n' "${REQUIRED_PUBLIC_FUNCTIONS[@]}" | LC_ALL=C sort | paste -sd' ' -)"

        BACKUP_EXPECTED_PROJECT="$SUPABASE_REF" \
        BACKUP_EXPECTED_SCHEMAS="public private auth supabase_migrations" \
        BACKUP_EXPECTED_APPLICATION_TABLES="$application_tables" \
        BACKUP_EXPECTED_PUBLIC_FUNCTIONS="$required_functions" \
            /bin/bash "$VERIFY_SCRIPT" "$sql_file"
        return
    fi

    /bin/bash "$VERIFY_SCRIPT" "$sql_file"
}

confirm_restore() {
    echo ""
    echo -e "${YELLOW}⚠️  AVISO: esto SOBRESCRIBE la base de datos actual.${NC}"
    echo -e "${YELLOW}   Proyecto: ${SUPABASE_REF}${NC}"
    echo ""
    read -r -p "¿Seguro que quieres continuar? (escribe 'yes' para confirmar): " confirm

    if [[ "$confirm" != "yes" ]]; then
        echo -e "${RED}❌ Restauración cancelada${NC}"
        exit 1
    fi
}

restore_backup() {
    local backup_name="$1"
    local sql_file="${TEMP_DIR}/${backup_name}_full.sql"

    echo -e "${BLUE}🔄 Restaurando en Supabase...${NC}"

    if [[ -z "${SUPABASE_DB_PASSWORD:-}" ]]; then
        echo -e "${YELLOW}Introduce la password de la base de datos de Supabase:${NC}"
        read -r -s SUPABASE_DB_PASSWORD
        echo ""
    fi

    local DB_URL="postgresql://postgres.${SUPABASE_REF}:${SUPABASE_DB_PASSWORD}@${POOLER_HOST}:5432/postgres"

    if ! command -v psql &> /dev/null; then
        echo -e "${RED}❌ psql no encontrado. Instala postgresql-client.${NC}"
        exit 1
    fi

    PGPASSWORD="$SUPABASE_DB_PASSWORD" psql "$DB_URL" --set ON_ERROR_STOP=1 -f "$sql_file"

    echo -e "${GREEN}✅ Restauración completada${NC}"
}

cleanup() {
    if [[ -d "$TEMP_DIR" ]]; then
        rm -rf "$TEMP_DIR"
    fi
}

main() {
    echo "=========================================="
    echo "  Residencia Fiscal — Restore desde R2"
    echo "=========================================="
    echo ""

    check_env
    configure_aws

    local verify_only=false
    if [[ "${1:-}" == "--verify-only" ]]; then
        verify_only=true
        shift
    fi

    if [[ $# -eq 0 ]]; then
        list_backups
        exit 0
    fi

    local backup_name="$1"

    if [[ ! "$backup_name" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{6}$ ]]; then
        echo -e "${RED}❌ Formato de nombre inválido${NC}"
        echo "Formato esperado: YYYY-MM-DD_HHMMSS (ej. 2026-07-31_020314)"
        exit 1
    fi

    download_backup "$backup_name"
    decompress_backup "$backup_name"
    verify_backup_contract "$backup_name"
    if [[ "$verify_only" == "true" ]]; then
        echo -e "${GREEN}✅ Descarga, descompresión y contrato SQL verificados. No se ejecutó ninguna restauración.${NC}"
        exit 0
    fi
    check_restore_env
    confirm_restore
    restore_backup "$backup_name"

    echo ""
    echo -e "${GREEN}🎉 Restore terminado${NC}"
}

trap cleanup EXIT

main "$@"
