#!/usr/bin/env bash
# Transfer only the verified C1 bundle and its JSON Schema to Alfredo.
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

BUNDLE="${DEEP_RESEARCH_BUNDLE:-$REPO_ROOT/output/deep-research/rollout-106.bundle.zip}"
SCHEMA_SOURCE="${DEEP_RESEARCH_SCHEMA_SOURCE:-$REPO_ROOT/../pymechat-alfredo/app/assets/residenciafiscal-deep-research-output.schema.json}"
REMOTE_ROOT="${DEEP_RESEARCH_REMOTE_ROOT:-/opt/residenciafiscal/deep-research}"
CONTAINER="${ALFREDO_CODEX_CONTAINER:-alfredo-codex-agent}"
REMOTE_SCRIPT="/tmp/residenciafiscal-install-deep-research-bundle.py"
REMOTE_BUNDLE="/tmp/residenciafiscal-deep-research.bundle.zip"
REMOTE_SCHEMA="/tmp/residenciafiscal-deep-research-output.schema.json"

[ -f .env ] || { printf 'falta .env en %s\n' "$REPO_ROOT" >&2; exit 1; }
ENV_FILE="${ALFREDO_DEPLOY_ENV_FILE:-$REPO_ROOT/../pymechat-alfredo/.env}"
[ -f "$ENV_FILE" ] || { printf 'falta fichero de conexión Alfredo: %s\n' "$ENV_FILE" >&2; exit 1; }
[ -f "$BUNDLE" ] || { printf 'falta bundle: %s\n' "$BUNDLE" >&2; exit 1; }
[ -f "$SCHEMA_SOURCE" ] || { printf 'falta schema: %s\n' "$SCHEMA_SOURCE" >&2; exit 1; }

set -a
. ./.env
[ -f "$ENV_FILE" ] && . "$ENV_FILE"
set +a
: "${ALFREDO_VPS_HOST:=${VPS_HOST:-}}"
: "${ALFREDO_VPS_SSH_PORT:=22}"
: "${ALFREDO_VPS_SSH_USER:=ubuntu}"
: "${ALFREDO_VPS_HOST:?falta ALFREDO_VPS_HOST o VPS_HOST}"

SSH_TARGET="$ALFREDO_VPS_SSH_USER@$ALFREDO_VPS_HOST"
SSH_OPTS=(-o ConnectTimeout=10 -p "$ALFREDO_VPS_SSH_PORT")
SCP_OPTS=(-o ConnectTimeout=10 -P "$ALFREDO_VPS_SSH_PORT")

bundle_id="$(PYTHONPATH=src uv run python -c 'import json, sys, zipfile; print(json.loads(zipfile.ZipFile(sys.argv[1]).read("MANIFEST.json"))["bundle_id"])' "$BUNDLE")"
if [[ ! "$bundle_id" =~ ^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$ ]] \
    || [[ "$bundle_id" == *..* || "$bundle_id" == */ || "$bundle_id" == *//* ]]; then
    printf 'bundle_id inseguro: %s\n' "$bundle_id" >&2
    exit 1
fi

printf '== Verificando bundle local ==\n'
make deep-research-bundle-verify DEEP_RESEARCH_BUNDLE="$BUNDLE"
printf '== Copiando solo bundle, schema e instalador a Alfredo ==\n'
scp "${SCP_OPTS[@]}" "$BUNDLE" "$SSH_TARGET:$REMOTE_BUNDLE"
scp "${SCP_OPTS[@]}" "$SCHEMA_SOURCE" "$SSH_TARGET:$REMOTE_SCHEMA"
scp "${SCP_OPTS[@]}" "$REPO_ROOT/scripts/deep_research_bundle_install.py" "$SSH_TARGET:$REMOTE_SCRIPT"
printf -v REMOTE_INSTALL_COMMAND '%q ' \
    sudo python3 "$REMOTE_SCRIPT" \
    --bundle "$REMOTE_BUNDLE" \
    --root "$REMOTE_ROOT" \
    --bundle-id "$bundle_id" \
    --container "$CONTAINER" \
    --schema "$REMOTE_SCHEMA"
ssh "${SSH_OPTS[@]}" "$SSH_TARGET" "$REMOTE_INSTALL_COMMAND"
printf -v REMOTE_CLEAN_COMMAND '%q ' rm -f "$REMOTE_SCRIPT" "$REMOTE_BUNDLE" "$REMOTE_SCHEMA"
ssh "${SSH_OPTS[@]}" "$SSH_TARGET" "$REMOTE_CLEAN_COMMAND"
printf '== Bundle instalado; la activación del worker sigue siendo explícita ==\n'
