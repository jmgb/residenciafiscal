#!/bin/bash
# ¿El código que systemd ejecuta es el que dice el repositorio?
#
# El subsistema de backup y el de retención corren desde un checkout del VPS que
# nadie actualiza solo. Sus ficheros llegaron ahí copiados a mano, así que la
# coincidencia con el repo es un hecho comprobable, no una garantía: el día que
# se toque `vps-backup.sh` o `purge-chat-data.sh`, el VPS seguiría ejecutando la
# versión vieja y ningún check lo notaría. `Backup contract OK` tampoco, porque
# valida el dump contra Supabase, no el script contra git.
#
# Este guardián contesta esa quinta pregunta. No tiene timer propio: lo invoca
# `check-backup-freshness.sh`, igual que `verify-backup-contract.sh`.
#
# Solo lee. Nunca actualiza el checkout por su cuenta: reconciliar es una
# decisión con consecuencias y se hace según el runbook de `BACKUPS.md`.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
UNIT_DIR="${OPERATIONAL_DRIFT_UNIT_DIR:-/etc/systemd/system}"
# Directorios cuyo contenido se ejecuta en producción.
OPERATIONAL_DIRS=("scripts/backup" "scripts/privacy")

timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

problemas=()

# ---------------------------------------------------------------------------
# 1. Ediciones locales que no están en ningún commit
# ---------------------------------------------------------------------------
if git -C "$PROJECT_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
    existentes=()
    for dir in "${OPERATIONAL_DIRS[@]}"; do
        [[ -d "$PROJECT_ROOT/$dir" ]] && existentes+=("$dir")
    done

    sucio="$(git -C "$PROJECT_ROOT" status --porcelain -- "${existentes[@]}" 2>/dev/null || true)"
    if [[ -n "$sucio" ]]; then
        ficheros="$(printf '%s\n' "$sucio" | awk '{print $NF}' | tr '\n' ' ')"
        problemas+=("cambios sin versionar en el checkout: ${ficheros}")
    fi

    # -----------------------------------------------------------------------
    # 2. Commits en el repositorio que este checkout todavía no ejecuta
    # -----------------------------------------------------------------------
    # Sin red esto no se puede saber, y no saberlo no es un fallo del backup:
    # se avisa y se sigue con lo que sí es comprobable en local.
    if git -C "$PROJECT_ROOT" fetch --quiet origin 2>/dev/null; then
        atrasado="$(
            git -C "$PROJECT_ROOT" diff --name-only HEAD origin/main -- "${existentes[@]}" 2>/dev/null || true
        )"
        if [[ -n "$atrasado" ]]; then
            ficheros="$(printf '%s\n' "$atrasado" | tr '\n' ' ')"
            problemas+=("el repositorio tiene versiones más nuevas sin desplegar: ${ficheros}")
        fi
    else
        echo "[$(timestamp)] WARN: no se pudo consultar origin; solo se comprueba el estado local" >&2
    fi
else
    echo "[$(timestamp)] WARN: ${PROJECT_ROOT} no es un checkout git; se omite la comparación" >&2
fi

# ---------------------------------------------------------------------------
# 3. Units instaladas que ya no son las del checkout
# ---------------------------------------------------------------------------
# systemd ejecuta su propia copia en UNIT_DIR: reinstalar es un paso manual, y
# olvidarlo deja el timer viejo corriendo aunque el fichero del repo cambie.
for dir in "${OPERATIONAL_DIRS[@]}"; do
    [[ -d "$PROJECT_ROOT/$dir" ]] || continue
    for unit in "$PROJECT_ROOT/$dir"/*.service "$PROJECT_ROOT/$dir"/*.timer; do
        [[ -f "$unit" ]] || continue
        nombre="$(basename "$unit")"
        instalada="${UNIT_DIR}/${nombre}"
        [[ -f "$instalada" ]] || continue

        if ! cmp -s "$unit" "$instalada"; then
            problemas+=("la unit instalada difiere del checkout: ${nombre}")
        fi
    done
done

if [[ ${#problemas[@]} -gt 0 ]]; then
    echo "[$(timestamp)] Operational drift DETECTED:" >&2
    for problema in "${problemas[@]}"; do
        echo "  - ${problema}" >&2
    done
    echo "  Reconcilia según docs/operations/BACKUPS.md antes de confiar en estos jobs." >&2
    exit 1
fi

echo "[$(timestamp)] Operational drift OK: el checkout y las units instaladas coinciden con el repositorio"
