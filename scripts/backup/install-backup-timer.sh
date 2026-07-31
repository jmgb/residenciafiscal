#!/bin/bash
# ============================================================================
# Instalar los systemd timers de backup de Residencia Fiscal en el VPS
# ============================================================================
# Ejecutar en el VPS con sudo:
#   sudo bash /home/ubuntu/residenciafiscal/scripts/backup/install-backup-timer.sh
#
# Es idempotente: se puede volver a ejecutar tras cada `git pull` que toque
# las units para recopiarlas y recargar systemd.
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"
SYSTEMD_DIR="/etc/systemd/system"

UNITS=(
    residenciafiscal-backup.service
    residenciafiscal-backup.timer
    residenciafiscal-backup-failure@.service
    residenciafiscal-backup-freshness.service
    residenciafiscal-backup-freshness.timer
    residenciafiscal-backup-restore-drill.service
    residenciafiscal-backup-restore-drill.timer
)

TIMERS=(
    residenciafiscal-backup.timer
    residenciafiscal-backup-freshness.timer
    residenciafiscal-backup-restore-drill.timer
)

REQUIRED_KEYS=(
    R2_ACCESS_KEY_ID
    R2_SECRET_ACCESS_KEY
    R2_ACCOUNT_ID
    SUPABASE_DB_PASSWORD
    SUPABASE_REF
)

# ── Verificaciones previas ─────────────────────────────────────────────────
if [[ "$EUID" -ne 0 ]]; then
    echo "ERROR: este script requiere sudo" >&2
    exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: no se encontró $ENV_FILE" >&2
    exit 1
fi

# shellcheck source=lib-read-env.sh
source "${SCRIPT_DIR}/lib-read-env.sh"

missing=()
for key in "${REQUIRED_KEYS[@]}"; do
    [[ -z "$(read_env_var "$ENV_FILE" "$key")" ]] && missing+=("$key")
done

if [[ ${#missing[@]} -gt 0 ]]; then
    echo "ERROR: faltan claves en ${ENV_FILE}:" >&2
    printf '  - %s\n' "${missing[@]}" >&2
    exit 1
fi

# pg_dump se niega a dumpear un servidor más nuevo que él, y Supabase corre
# PostgreSQL 17. El postgresql-client de Ubuntu 24.04 es el 16, así que hace falta
# el repo PGDG. Sube MIN_PG_MAJOR cuando Supabase actualice de versión mayor.
MIN_PG_MAJOR=17

ensure_pg_dump() {
    local major=0
    if command -v pg_dump &> /dev/null; then
        major="$(pg_dump --version | grep -oE '[0-9]+' | head -1)"
    fi
    if [[ "$major" -ge "$MIN_PG_MAJOR" ]]; then
        echo "pg_dump ${major}.x OK"
        return 0
    fi

    echo "pg_dump ${major:-ausente} < ${MIN_PG_MAJOR}: instalando postgresql-client-${MIN_PG_MAJOR} desde PGDG..."
    apt-get update -q
    apt-get install -y curl ca-certificates
    install -d /usr/share/postgresql-common/pgdg
    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
        -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc
    local codename
    codename="$(. /etc/os-release && echo "$VERSION_CODENAME")"
    echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt ${codename}-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list
    apt-get update -q
    apt-get install -y "postgresql-client-${MIN_PG_MAJOR}"
}

ensure_aws_cli() {
    if command -v aws &> /dev/null; then
        echo "aws CLI OK: $(aws --version 2>&1 | head -1)"
        return 0
    fi

    # Ubuntu 24.04 ya no trae el paquete `awscli` en apt: instalador oficial v2.
    echo "aws CLI no encontrado. Instalando AWS CLI v2..."
    apt-get update -q
    apt-get install -y curl unzip ca-certificates
    local tmp
    tmp="$(mktemp -d)"
    curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-$(uname -m).zip" -o "${tmp}/awscliv2.zip"
    unzip -q "${tmp}/awscliv2.zip" -d "$tmp"
    "${tmp}/aws/install" --update
    rm -rf "$tmp"
}

ensure_pg_dump
ensure_aws_cli

# ── Instalar ───────────────────────────────────────────────────────────────
echo "Copiando units a ${SYSTEMD_DIR}..."
for unit in "${UNITS[@]}"; do
    cp "${SCRIPT_DIR}/${unit}" "${SYSTEMD_DIR}/${unit}"
done

echo "Recargando systemd..."
systemctl daemon-reload
systemctl reset-failed \
    residenciafiscal-backup.service \
    residenciafiscal-backup-freshness.service \
    residenciafiscal-backup-restore-drill.service 2>/dev/null || true

echo "Activando timers..."
for timer in "${TIMERS[@]}"; do
    systemctl enable "$timer"
    systemctl start "$timer"
done

echo ""
echo "=== Instalación completada ==="
systemctl list-timers "${TIMERS[@]}" --no-pager
echo ""
echo "Ejecutar un backup ahora:  sudo systemctl start residenciafiscal-backup.service"
echo "Ver logs:                  journalctl -u residenciafiscal-backup -f"
