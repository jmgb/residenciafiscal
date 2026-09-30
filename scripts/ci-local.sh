#!/usr/bin/env bash
# CI local: reproduce los checks BLOQUEANTES de .github/workflows/ci.yml,
# frontend.yml y gitleaks.yml para cuando GitHub Actions no tiene minutos.
# FUENTE ÚNICA: ci.yml (`python`) y frontend.yml (`frontend`) también llaman a
# este script, así que local y remoto no pueden divergir. gitleaks.yml sigue
# usando su acción (integración con el PR); aquí solo se ejecuta en `all`,
# `backend`, `changed` y `pre-push`, no en `python`.
#
#   bash scripts/ci-local.sh [all|backend|python|frontend|changed [base]|pre-push]
#   `python` = solo los pasos de ci.yml (ruff, format, mypy, pytest, rollout), sin gitleaks
#   bash scripts/ci-local.sh changed [base]   # según el diff vs base (origin/main)
#   bash scripts/ci-local.sh pre-push         # rutas por stdin (formato `git diff --name-only`)
#
# Ejecuta todos los pasos aunque alguno falle y termina con un resumen; exit 1 si
# falló un paso bloqueante. Los pasos no bloqueantes (p. ej. gitleaks sin binario)
# salen como WARN y no cambian el exit code. Un log por paso en $CI_LOCAL_LOG_DIR;
# con $CI la salida va también a stdout.
#
# no se reproduce: `npm ci` (red; usa el node_modules instalado) y el comentario
# del PR de gitleaks-action (necesita GITHUB_TOKEN). Los pasos de node (lint,
# typecheck, vitest, build) van en serie: nunca dos procesos node a la vez.
# Ojo: `make rollout-reproducibility` regenera ficheros de knowledge/jurisprudencia-v3
# y compara con git: con esos ficheros modificados sin commitear dará falso FAIL.
set -uo pipefail
cd "$(dirname "$0")/.."
mode="${1:-all}"
python=0 frontend=0 gitleaks=0

select_from_paths() {
    while IFS= read -r path; do
        case "$path" in
            '') ;;
            # ci.yml ignora docs/** y los *.md de la raíz (no los de knowledge/, frontend/...).
            docs/*) ;;
            .github/workflows/*|scripts/ci-local.sh) python=1; gitleaks=1; frontend=1 ;;
            frontend/*|knowledge/normativa/*)
                # frontend/** también dispara pytest: hay tests que leen robots.txt, sitemap...
                python=1; gitleaks=1; frontend=1 ;;
            */*) python=1; gitleaks=1 ;;
            *.md|LICENSE) ;;
            *) python=1; gitleaks=1 ;;
        esac
    done
}

case "$mode" in
    all) python=1; gitleaks=1; frontend=1 ;;
    backend) python=1; gitleaks=1 ;;
    python) python=1 ;;
    frontend) frontend=1 ;;
    pre-push) select_from_paths ;;
    changed)
        base="${2:-origin/main}"
        merge_base=$(git merge-base "$base" HEAD) || { echo "ci-local: no encuentro $base (¿git fetch?)" >&2; exit 2; }
        select_from_paths < <({ git diff --name-only "$merge_base"; git ls-files --others --exclude-standard; } | sort -u) ;;
    *) echo "usage: bash scripts/ci-local.sh [all|backend|python|frontend|changed [base]|pre-push]" >&2; exit 2 ;;
esac

LOG_DIR="${CI_LOCAL_LOG_DIR:-${TMPDIR:-/tmp}/ci-local-residenciafiscal}"
mkdir -p "$LOG_DIR"
summary=()
failed=0

# _run <blocking|advisory> <nombre> <comando bash>: ejecuta, guarda log y sigue aunque falle.
_run() {
    local kind="$1" name="$2" cmd="$3" log start rc
    log="$LOG_DIR/$(printf '%s' "$name" | tr -c 'A-Za-z0-9_-' '_').log"
    start=$SECONDS
    printf '▶ %s\n' "$name"
    if [[ -n "${CI:-}" ]]; then
        bash -c "$cmd" 2>&1 | tee "$log"
        rc=${PIPESTATUS[0]}
    else
        bash -c "$cmd" >"$log" 2>&1
        rc=$?
    fi
    if (( rc == 0 )); then
        summary+=("ok    $(( SECONDS - start ))s  $name")
    elif [[ "$kind" == advisory ]]; then
        summary+=("WARN  $(( SECONDS - start ))s  $name (no bloqueante)  → $log")
    else
        summary+=("FAIL  $(( SECONDS - start ))s  $name  → $log")
        failed=1
        [[ -n "${CI:-}" ]] || tail -n 40 "$log"
    fi
    [[ "$kind" == advisory ]] && return 0
    return "$rc"
}
step() { _run blocking "$@"; }
advisory() { _run advisory "$@"; }

if (( python )); then
    step "python: uv sync" 'uv sync --locked' || python=0
fi
if (( python )); then
    step "python: ruff check" 'uv run ruff check .'
    step "python: ruff format --check" 'uv run ruff format --check .'
    step "python: mypy" 'uv run mypy .'
    step "python: pytest" 'uv run pytest -q'
    step "rollout: verify" 'make rollout-verify'
    step "rollout: reproducibility" 'make rollout-reproducibility'
    if (( ! gitleaks )); then :
    elif command -v gitleaks >/dev/null 2>&1; then
        step "gitleaks" 'gitleaks git --no-banner --redact'
    else
        advisory "gitleaks" 'echo "gitleaks no está instalado: no se escanean secretos"; exit 1'
    fi
fi
# Los pasos de node van en serie: nunca dos procesos node pesados a la vez.
if (( frontend )); then
    step "frontend: lint" 'cd frontend && npm run lint'
    step "frontend: typecheck" 'cd frontend && npm run typecheck'
    step "frontend: vitest" 'cd frontend && npm run test'
    step "frontend: build" 'cd frontend && npm run build'
fi

echo
echo "== ci-local ($mode) · logs en $LOG_DIR"
(( ${#summary[@]} )) && printf '%s\n' "${summary[@]}" || echo "nada que ejecutar (sin cambios de código)"
exit "$failed"
