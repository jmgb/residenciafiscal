#!/bin/bash
# Verifica que un dump SQL contiene exactamente el inventario de tablas de
# aplicación declarado en su cabecera y las RPC públicas imprescindibles.
# No ejecuta SQL ni muestra datos del backup.

set -euo pipefail

SQL_FILE="${1:-}"

fail() {
    echo "ERROR: Backup contract: $1" >&2
    exit 1
}

if [[ -z "$SQL_FILE" ]]; then
    fail "uso: $0 <backup.sql>"
fi

if [[ ! -f "$SQL_FILE" ]]; then
    fail "no existe el fichero SQL: $SQL_FILE"
fi

if [[ ! -s "$SQL_FILE" ]]; then
    fail "el fichero SQL está vacío: $SQL_FILE"
fi

header_value() {
    local label="$1"
    local line
    line="$(grep -m1 -F -- "-- ${label}: " "$SQL_FILE" || true)"
    [[ -n "$line" ]] || fail "falta la cabecera '${label}'"
    printf '%s\n' "${line#-- ${label}: }"
}

canonical_list() {
    tr ' ' '\n' \
        | sed '/^$/d' \
        | LC_ALL=C sort -u \
        | paste -sd' ' -
}

validate_identifiers() {
    local label="$1"
    local list="$2"
    local identifier

    for identifier in $list; do
        if [[ ! "$identifier" =~ ^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$ ]]; then
            fail "${label} contiene un identificador inválido: ${identifier}"
        fi
    done
}

PROJECT="$(header_value "Project")"
SCHEMAS="$(printf '%s' "$(header_value "Schemas")" | canonical_list)"
APPLICATION_TABLES_RAW="$(header_value "Application tables")"
PUBLIC_FUNCTIONS_RAW="$(header_value "Required public functions")"
[[ "$APPLICATION_TABLES_RAW" == "(none)" ]] && APPLICATION_TABLES_RAW=""
[[ "$PUBLIC_FUNCTIONS_RAW" == "(none)" ]] && PUBLIC_FUNCTIONS_RAW=""
APPLICATION_TABLES="$(printf '%s' "$APPLICATION_TABLES_RAW" | canonical_list)"
PUBLIC_FUNCTIONS="$(printf '%s' "$PUBLIC_FUNCTIONS_RAW" | canonical_list)"

validate_identifiers "Application tables" "$APPLICATION_TABLES"
validate_identifiers "Required public functions" "$PUBLIC_FUNCTIONS"

if [[ -n "${BACKUP_EXPECTED_PROJECT:-}" && "$PROJECT" != "$BACKUP_EXPECTED_PROJECT" ]]; then
    fail "Project esperado '${BACKUP_EXPECTED_PROJECT}', encontrado '${PROJECT}'"
fi

if [[ -n "${BACKUP_EXPECTED_SCHEMAS:-}" ]]; then
    EXPECTED_SCHEMAS="$(printf '%s' "$BACKUP_EXPECTED_SCHEMAS" | canonical_list)"
    if [[ "$SCHEMAS" != "$EXPECTED_SCHEMAS" ]]; then
        fail "Schemas esperados '${EXPECTED_SCHEMAS}', encontrados '${SCHEMAS}'"
    fi
fi

if [[ -n "${BACKUP_EXPECTED_APPLICATION_TABLES:-}" ]]; then
    EXPECTED_TABLES="$(printf '%s' "$BACKUP_EXPECTED_APPLICATION_TABLES" | canonical_list)"
    if [[ "$APPLICATION_TABLES" != "$EXPECTED_TABLES" ]]; then
        fail "Application tables esperadas '${EXPECTED_TABLES}', encontradas '${APPLICATION_TABLES}'"
    fi
fi

if [[ -n "${BACKUP_EXPECTED_PUBLIC_FUNCTIONS:-}" ]]; then
    EXPECTED_FUNCTIONS="$(printf '%s' "$BACKUP_EXPECTED_PUBLIC_FUNCTIONS" | canonical_list)"
    if [[ "$PUBLIC_FUNCTIONS" != "$EXPECTED_FUNCTIONS" ]]; then
        fail "Required public functions esperadas '${EXPECTED_FUNCTIONS}', encontradas '${PUBLIC_FUNCTIONS}'"
    fi
fi

# La cabecera no puede mentir: el inventario real de CREATE TABLE para los
# schemas de aplicación debe ser exactamente el declarado.
DUMP_APPLICATION_TABLES="$({
    sed -nE 's/^CREATE TABLE (public|private)\.([a-z][a-z0-9_]*) \(.*/\1.\2/p' "$SQL_FILE"
} | canonical_list)"

if [[ "$DUMP_APPLICATION_TABLES" != "$APPLICATION_TABLES" ]]; then
    fail "Application tables declaradas '${APPLICATION_TABLES}', CREATE TABLE encontrados '${DUMP_APPLICATION_TABLES}'"
fi

for table in $APPLICATION_TABLES; do
    grep -Fq -- "CREATE TABLE ${table} (" "$SQL_FILE" \
        || fail "falta CREATE TABLE ${table}"
    grep -Fq -- "COPY ${table} (" "$SQL_FILE" \
        || fail "falta COPY ${table}: el dump no contiene su bloque restaurable"
done

for function in $PUBLIC_FUNCTIONS; do
    escaped_function="${function//./\.}"
    grep -Eq -- "^CREATE (OR REPLACE )?FUNCTION ${escaped_function}\(" "$SQL_FILE" \
        || fail "falta CREATE FUNCTION ${function}"
done

# Defensa de producto: un dump puede contener los nombres antiguos como texto
# dentro de `supabase_migrations`, pero nunca como DDL ejecutable ni como campos
# de una definición de tabla vigente.
FORBIDDEN_DDL_LINE="$({
    grep -En -- \
        '^(CREATE|ALTER|GRANT|REVOKE|COMMENT ON) .*public\.reserve_chat_request|^(CREATE|ALTER|COPY|GRANT|REVOKE|COMMENT ON) .*private\.(chat_daily_budgets|chat_budget_circuit_breaker)|^[[:space:]]+(reservation_microusd|daily_limit_microusd|budget_date)[[:space:]]' \
        "$SQL_FILE" || true
} | head -1 | cut -d: -f1)"

if [[ -n "$FORBIDDEN_DDL_LINE" ]]; then
    fail "objeto económico prohibido en SQL ejecutable (línea ${FORBIDDEN_DDL_LINE})"
fi

echo "Backup contract OK: project=${PROJECT}; schemas=${SCHEMAS}; application_tables=${APPLICATION_TABLES}; required_public_functions=${PUBLIC_FUNCTIONS}"
