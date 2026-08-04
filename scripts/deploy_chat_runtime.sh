#!/usr/bin/env bash
# Instala el artefacto del runtime del chat en el host y recrea su contenedor.
#
# El host recibe un tar verificado por hash, lo extrae en una release propia y
# solo entonces mueve `current` con un rename atómico: ningún arranque puede
# combinar código y corpus de versiones distintas. El contenedor queda cerrado
# —sin proveedores ni persistencia— hasta que el operador cambie su env file.
#
# El inventario real del host (hostname, puerto, usuario) sale del entorno
# privado, nunca de este fichero.
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

ARTIFACT="${CHAT_RUNTIME_ARTIFACT:-$REPO_ROOT/output/chat-runtime/chat-runtime.tar.gz}"
DOCKERFILE="${CHAT_RUNTIME_DOCKERFILE:-$REPO_ROOT/docker/chat-runtime.Dockerfile}"
REMOTE_ROOT="${CHAT_RUNTIME_REMOTE_ROOT:-/opt/residenciafiscal/chat-runtime}"
CONTAINER="${CHAT_RUNTIME_CONTAINER:-residenciafiscal-chat}"
IMAGE="${CHAT_RUNTIME_IMAGE:-residenciafiscal-chat-runtime}"
BIND_ADDRESS="${CHAT_RUNTIME_BIND:-127.0.0.1}"
PORT="${CHAT_RUNTIME_PORT:-8021}"
MEMORY="${CHAT_RUNTIME_MEMORY:-1g}"
CPUS="${CHAT_RUNTIME_CPUS:-1.0}"
PIDS="${CHAT_RUNTIME_PIDS:-256}"
REMOTE_ARTIFACT="/tmp/residenciafiscal-chat-runtime.tar.gz"
REMOTE_DOCKERFILE="/tmp/residenciafiscal-chat-runtime.Dockerfile"
REMOTE_INSTALLER="/tmp/residenciafiscal-install-chat-runtime.py"

[ -f "$ARTIFACT" ] || { printf 'falta el artefacto: %s\n' "$ARTIFACT" >&2; exit 1; }
[ -f "$DOCKERFILE" ] || { printf 'falta el dockerfile: %s\n' "$DOCKERFILE" >&2; exit 1; }
[ -f .env ] || { printf 'falta .env en %s\n' "$REPO_ROOT" >&2; exit 1; }
ENV_FILE="${ALFREDO_DEPLOY_ENV_FILE:-$REPO_ROOT/../pymechat-alfredo/.env}"

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

printf '== Verificando el artefacto en local ==\n'
make verify-chat-runtime-artifact CHAT_RUNTIME_ARTIFACT="$ARTIFACT"

printf '== Copiando artefacto e instalador ==\n'
scp "${SCP_OPTS[@]}" "$ARTIFACT" "$SSH_TARGET:$REMOTE_ARTIFACT"
scp "${SCP_OPTS[@]}" "$DOCKERFILE" "$SSH_TARGET:$REMOTE_DOCKERFILE"
scp "${SCP_OPTS[@]}" "$REPO_ROOT/scripts/install_chat_runtime.py" "$SSH_TARGET:$REMOTE_INSTALLER"

printf '== Instalando la release y recreando el contenedor ==\n'
ssh "${SSH_OPTS[@]}" "$SSH_TARGET" \
    "CHAT_RUNTIME_REMOTE_ROOT='$REMOTE_ROOT' \
     CHAT_RUNTIME_CONTAINER='$CONTAINER' \
     CHAT_RUNTIME_IMAGE='$IMAGE' \
     CHAT_RUNTIME_BIND='$BIND_ADDRESS' \
     CHAT_RUNTIME_PORT='$PORT' \
     CHAT_RUNTIME_MEMORY='$MEMORY' \
     CHAT_RUNTIME_CPUS='$CPUS' \
     CHAT_RUNTIME_PIDS='$PIDS' \
     python3 '$REMOTE_INSTALLER' '$REMOTE_ARTIFACT' '$REMOTE_DOCKERFILE'"

printf '== Listo. El servicio escucha solo en %s:%s ==\n' "$BIND_ADDRESS" "$PORT"
