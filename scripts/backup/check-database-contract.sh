#!/bin/bash
# ¿La base de datos es la que el repositorio declara?
#
# El subsistema ya contestaba tres preguntas: si hay un backup fresco y legible,
# si el dump cuadra con Supabase y si el checkout del VPS es el del repositorio.
# Faltaba la cuarta, y es la que falló: una migración editada en sitio después
# de aplicarse deja la base de datos con la redacción anterior sin que nada lo
# diga. `supabase migration list` tampoco lo ve, porque compara versiones y no
# contenido.
#
# Compara las firmas vivas de las RPC del contrato con las que declara
# `database-contract.txt`. No compara cuerpos de función: la firma es lo que
# rompe a quien llama, es barato de comprobar y es exactamente lo que se torció
# el 3 de agosto de 2026 —tres argumentos en el repositorio, uno en producción—.
#
# No tiene timer propio: lo invoca `check-backup-freshness.sh`, igual que el
# verificador de contrato y el guardián de deriva. Solo lee, y nunca reconcilia.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && cd .. && pwd)"
MANIFEST="${DATABASE_CONTRACT_MANIFEST:-$SCRIPT_DIR/database-contract.txt}"
# Hereda los overrides del job que lo invoca: si el check de frescura apunta a
# otro `.env`, este miraría otro proyecto y fallaría por credenciales ausentes.
ENV_FILE="${DATABASE_CONTRACT_ENV_FILE:-${BACKUP_FRESHNESS_ENV_FILE:-$PROJECT_ROOT/.env}}"
POOLER_HOST="${DATABASE_CONTRACT_POOLER_HOST:-${BACKUP_POOLER_HOST:-aws-0-eu-west-1.pooler.supabase.com}}"

timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

fail() {
    echo "[$(timestamp)] Database contract FAILED: $1" >&2
    exit 1
}

[[ -f "$MANIFEST" ]] || fail "no existe el manifiesto: $MANIFEST"
command -v psql >/dev/null 2>&1 || fail "psql no encontrado"

# NO usar `source` sobre el .env (ver lib-read-env.sh).
# shellcheck source=lib-read-env.sh
source "$SCRIPT_DIR/lib-read-env.sh"
SUPABASE_DB_PASSWORD="$(read_env_var_or_current "$ENV_FILE" SUPABASE_DB_PASSWORD)"
SUPABASE_REF="$(read_env_var_or_current "$ENV_FILE" SUPABASE_REF)"

if [[ -z "$SUPABASE_DB_PASSWORD" || -z "$SUPABASE_REF" ]]; then
    fail "faltan SUPABASE_DB_PASSWORD o SUPABASE_REF en ${ENV_FILE}"
fi

DECLARADAS="$(grep -v -E '^[[:space:]]*(#|$)' "$MANIFEST" | LC_ALL=C sort)"
[[ -n "$DECLARADAS" ]] || fail "el manifiesto no declara ninguna firma"

# Las funciones cubiertas salen del propio manifiesto: lo que no declara, no se
# comprueba. Se validan antes de construir la consulta porque acaban dentro de
# ella como literales.
CUBIERTAS="$(printf '%s\n' "$DECLARADAS" | cut -d'(' -f1 | LC_ALL=C sort -u)"
LISTA=""
while IFS= read -r funcion; do
    if [[ ! "$funcion" =~ ^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$ ]]; then
        fail "el manifiesto declara un identificador inválido: ${funcion}"
    fi
    LISTA+="${LISTA:+,}'${funcion}'"
done <<< "$CUBIERTAS"

DB_URL="postgresql://postgres.${SUPABASE_REF}:${SUPABASE_DB_PASSWORD}@${POOLER_HOST}:5432/postgres"

if ! VIVAS="$(PGPASSWORD="$SUPABASE_DB_PASSWORD" psql \
    "$DB_URL" \
    --no-password \
    --no-align \
    --tuples-only \
    -v ON_ERROR_STOP=1 \
    -c "SELECT n.nspname || '.' || p.proname || '(' || pg_get_function_identity_arguments(p.oid) || ')'
          FROM pg_proc AS p
          JOIN pg_namespace AS n ON n.oid = p.pronamespace
         WHERE n.nspname || '.' || p.proname IN (${LISTA})
         ORDER BY 1;" 2>&1)"; then
    fail "no se pudo consultar el catálogo: ${VIVAS}"
fi

VIVAS="$(printf '%s\n' "$VIVAS" | grep -v '^$' | LC_ALL=C sort || true)"

AUSENTES="$(comm -23 <(printf '%s\n' "$DECLARADAS") <(printf '%s\n' "$VIVAS"))"
SOBRANTES="$(comm -13 <(printf '%s\n' "$DECLARADAS") <(printf '%s\n' "$VIVAS"))"

if [[ -n "$AUSENTES" || -n "$SOBRANTES" ]]; then
    echo "[$(timestamp)] Database contract DRIFT DETECTED:" >&2
    while IFS= read -r firma; do
        [[ -n "$firma" ]] && echo "  - declarada y ausente en la base de datos: ${firma}" >&2
    done <<< "$AUSENTES"
    while IFS= read -r firma; do
        [[ -n "$firma" ]] && echo "  - viva y no declarada por el repositorio: ${firma}" >&2
    done <<< "$SOBRANTES"
    echo "  Una migración aplicada no se edita: se corrige hacia delante." >&2
    echo "  Ver docs/operations/SUPABASE_CHAT.md antes de tocar nada." >&2
    exit 1
fi

TOTAL="$(printf '%s\n' "$DECLARADAS" | wc -l | tr -d ' ')"
echo "[$(timestamp)] Database contract OK: ${TOTAL} firmas vivas coinciden con el repositorio"
