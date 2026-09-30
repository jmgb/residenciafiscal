#!/usr/bin/env bash
# Selección de pasos de scripts/ci-local.sh con stubs offline (git real en repo temporal).
set -euo pipefail
script="$(cd "$(dirname "$0")/../.." && pwd)/scripts/ci-local.sh"
root=$(mktemp -d)
trap 'rm -rf "$root"' EXIT
tmp="$root/repo" stubs="$root/bin" gl="$root/gl"  # stubs y logs fuera del repo
mkdir -p "$tmp"/{scripts,src,docs,frontend,knowledge/normativa} "$stubs" "$gl"
cp "$script" "$tmp/scripts/ci-local.sh"
cat > "$stubs/command-stub" <<'STUB'
#!/usr/bin/env bash
echo "${0##*/} $*" >> "$CHECK_CALLS"
[[ -n "${FAIL_PATTERN:-}" && "${0##*/} $*" == *"$FAIL_PATTERN"* ]] && exit 1
exit 0
STUB
chmod +x "$stubs/command-stub"
for n in uv npm make; do ln -s command-stub "$stubs/$n"; done
ln -s ../bin/command-stub "$gl/gitleaks"
export CHECK_CALLS="$root/calls" CI_LOCAL_LOG_DIR="$root/logs"
BASE_PATH="$stubs:/usr/bin:/bin"   # sin gitleaks real
export PATH="$BASE_PATH"
unset CI FAIL_PATTERN
run() { bash "$tmp/scripts/ci-local.sh" "$@"; }
fail() { echo "FAIL: $*"; exit 1; }
called() { grep -q "$1" "$CHECK_CALLS"; }

(unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_OBJECT_DIRECTORY GIT_COMMON_DIR
 cd "$tmp" && git init -q && git add -A && git -c user.email=ci@local -c user.name=ci commit -qm base --allow-empty \
    && git update-ref refs/remotes/origin/main HEAD)
cd "$tmp"
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_OBJECT_DIRECTORY GIT_COMMON_DIR

# docs-only (docs/** y *.md de la raíz) -> nada
: > "$CHECK_CALLS"
run pre-push <<< $'README.md\ndocs/plan.md\nCLAUDE.md' >/dev/null
[[ ! -s "$CHECK_CALLS" ]] || fail 'docs-only lanza pasos'

# python -> sin npm; frontend -> sin pytest; ambos para workflow/ci-local/normativa
: > "$CHECK_CALLS"
run pre-push <<< src/x.py >/dev/null || fail 'python: exit != 0'
called 'pytest -q' && called 'make rollout-verify' || fail 'python no corre pytest/rollout'
called 'npm' && fail 'python-only lanzó npm'

: > "$CHECK_CALLS"
run pre-push <<< knowledge/otro/x.md >/dev/null   # .md fuera de la raíz sí dispara ci.yml
called 'pytest -q' || fail 'knowledge/**.md no dispara pytest'

for p in .github/workflows/frontend.yml scripts/ci-local.sh frontend/src/a.ts knowledge/normativa/x.md; do
    : > "$CHECK_CALLS"
    run pre-push <<< "$p" >/dev/null
    called 'npm run lint' && called 'npm run typecheck' || fail "frontend no corre para $p"
done
: > "$CHECK_CALLS"
run frontend >/dev/null
called 'pytest' && fail 'modo frontend lanzó pytest'
called 'npm run typecheck' || fail 'modo frontend sin typecheck'

# fallo bloqueante no corta el resto y da exit 1
: > "$CHECK_CALLS"
if FAIL_PATTERN='mypy' run all >/dev/null 2>&1; then fail 'mypy fallido debería dar exit 1'; fi
called 'pytest -q' && called 'npm run typecheck' || fail 'el fallo de mypy cortó pasos posteriores'

# gitleaks ausente -> WARN y exit 0; presente -> se ejecuta
out=$(run all 2>&1) || fail 'gitleaks ausente dio exit != 0'
grep -q 'WARN.*gitleaks' <<< "$out" || fail 'falta WARN de gitleaks'
: > "$CHECK_CALLS"
PATH="$gl:$BASE_PATH" run all >/dev/null || fail 'con gitleaks dio exit != 0'
called 'gitleaks git' || fail 'gitleaks instalado no se ejecutó'
if PATH="$gl:$BASE_PATH" FAIL_PATTERN='gitleaks' run all >/dev/null 2>&1; then fail 'gitleaks con hallazgos debería dar exit 1'; fi

# changed: diff + untracked
echo x > frontend/new.ts
: > "$CHECK_CALLS"
run changed >/dev/null
called 'npm run lint' || fail 'changed ignoró frontend/new.ts'
called 'pytest' || fail 'changed: frontend/** debería lanzar también pytest'
rm frontend/new.ts; echo x > docs/new.md
: > "$CHECK_CALLS"
run changed >/dev/null
[[ ! -s "$CHECK_CALLS" ]] || fail 'changed lanzó pasos por un diff solo de docs'
echo 'PASS: ci-local selecciona por rutas, sigue tras fallos y respeta advisory'
