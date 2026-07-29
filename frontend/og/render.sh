#!/usr/bin/env bash
# Render determinista de la imagen Open Graph: `npm run og`.
# Lee los tokens de src/index.css, los inyecta en og-image.html y captura
# 1200×630 con Chrome headless. El PNG resultante es un artefacto: no se
# edita a mano.
set -euo pipefail
cd "$(dirname "$0")"

CHROME="${CHROME:-google-chrome}"
CSS=../src/index.css
OUT=../public/og-image.png

token() {
  grep -oP -- "--color-$1:\s*\K#[0-9a-fA-F]{6}" "$CSS" | head -1
}

BACKGROUND=$(token background)
FOREGROUND=$(token foreground)
PRIMARY=$(token primary)
MUTED_FOREGROUND=$(token muted-foreground)

TMP=$(mktemp -t og-image-XXXX.html --tmpdir="$PWD")
trap 'rm -f "$TMP"' EXIT
sed -e "s/__BACKGROUND__/$BACKGROUND/g" \
    -e "s/__FOREGROUND__/$FOREGROUND/g" \
    -e "s/__PRIMARY__/$PRIMARY/g" \
    -e "s/__MUTED_FOREGROUND__/$MUTED_FOREGROUND/g" \
    og-image.html > "$TMP"

# El viewport de Chrome headless no coincide exactamente con --window-size,
# así que se captura con margen y se recorta al lienzo real de 1200×630.
"$CHROME" --headless --disable-gpu --hide-scrollbars \
  --window-size=1280,760 --virtual-time-budget=10000 \
  --screenshot="$OUT" "file://$TMP" 2>/dev/null

python3 - "$OUT" <<'PY'
import sys

from PIL import Image

out = sys.argv[1]
Image.open(out).convert("RGB").crop((0, 0, 1200, 630)).save(out)
PY

echo "OG generada: $OUT"
