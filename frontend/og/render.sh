#!/usr/bin/env bash
# Render determinista de la imagen Open Graph: `npm run og`.
# Lee los tokens de src/index.css, los inyecta en og-image.html y captura
# 1200×630 con Chrome headless. El PNG resultante es un artefacto: no se
# edita a mano.
set -euo pipefail
cd "$(dirname "$0")"

CHROME="${CHROME:-google-chrome}"
CSS=../src/index.css

token() {
  grep -oP -- "--color-$1:\s*\K#[0-9a-fA-F]{6}" "$CSS" | head -1
}

BACKGROUND=$(token background)
FOREGROUND=$(token foreground)
PRIMARY=$(token primary)
MUTED_FOREGROUND=$(token muted-foreground)

render() { # render <fuente.html> <salida.png>
  local tmp
  tmp=$(mktemp -t og-image-XXXX.html --tmpdir="$PWD")
  sed -e "s/__BACKGROUND__/$BACKGROUND/g" \
      -e "s/__FOREGROUND__/$FOREGROUND/g" \
      -e "s/__PRIMARY__/$PRIMARY/g" \
      -e "s/__MUTED_FOREGROUND__/$MUTED_FOREGROUND/g" \
      "$1" > "$tmp"

  # El viewport de Chrome headless no coincide exactamente con --window-size,
  # así que se captura con margen y se recorta al lienzo real de 1200×630.
  "$CHROME" --headless --disable-gpu --hide-scrollbars \
    --window-size=1280,760 --virtual-time-budget=10000 \
    --screenshot="$2" "file://$tmp" 2>/dev/null
  rm -f "$tmp"

  python3 - "$2" <<'PY'
import sys

from PIL import Image

out = sys.argv[1]
Image.open(out).convert("RGB").crop((0, 0, 1200, 630)).save(out)
PY

  echo "OG generada: $2"
}

render og-image.html ../public/og-image.png
render og-image-manifiesto.html ../public/og-image-manifiesto.png
