#!/usr/bin/env bash
# Render determinista de los iconos: `npm run favicon`.
# Desde public/favicon.svg (fuente única del isotipo) genera:
#   - public/favicon.ico (48/32/16; el 16 desde una variante con el trazo de
#     las letras engrosado, que a ese tamaño el monograma pierde el contraforma)
#   - public/apple-touch-icon.png (180, full-bleed: iOS aplica su propia máscara)
# Chrome no pinta con ventanas muy pequeñas, así que cada variante se captura
# a 512 px y Pillow reescala (Lanczos, mejor antialiasing que el render directo).
# Los .ico/.png resultantes son artefactos: no se editan a mano.
set -euo pipefail
cd "$(dirname "$0")"

CHROME="${CHROME:-google-chrome}"
SVG=../public/favicon.svg

WORK=$(mktemp -d -t favicon-XXXX)
trap 'rm -rf "$WORK"' EXIT

# Variante engrosada para 16 px: las letras ganan un stroke del color del fill.
sed -e 's|fill="#f8fafc"/>|fill="#f8fafc" stroke="#f8fafc" stroke-width="28"/>|' \
    -e 's|fill="#f59e0b"/>|fill="#f59e0b" stroke="#f59e0b" stroke-width="28"/>|' \
    "$SVG" > "$WORK/bold.svg"

# Variante full-bleed sin esquinas redondeadas para apple-touch-icon.
sed -e 's|rx="14" ||' "$SVG" > "$WORK/fullbleed.svg"

shot() { # shot <svg> <salida>: captura a 512 px con fondo transparente
  local wrapper="$WORK/wrapper.html"
  {
    printf '<!doctype html><html><head><style>html,body{margin:0}svg{display:block;width:100vw;height:100vh}</style></head><body>'
    cat "$1"
    printf '</body></html>'
  } > "$wrapper"
  "$CHROME" --headless --disable-gpu --hide-scrollbars \
    --window-size=512,512 --default-background-color=00000000 \
    --screenshot="$2" "file://$wrapper" 2>/dev/null
}

shot "$SVG" "$WORK/base-512.png"
shot "$WORK/bold.svg" "$WORK/bold-512.png"
shot "$WORK/fullbleed.svg" "$WORK/fullbleed-512.png"

python3 - "$WORK" <<'PY'
import sys
from pathlib import Path

from PIL import Image

work = Path(sys.argv[1])
public = Path("../public")

def load(name: str) -> Image.Image:
    # El viewport de Chrome no coincide exactamente con --window-size, así que
    # el SVG queda centrado con márgenes transparentes: recortar al contenido.
    im = Image.open(work / name)
    return im.crop(im.getchannel("A").getbbox())


base = load("base-512.png")
bold = load("bold-512.png")
frames = [
    base.resize((48, 48), Image.LANCZOS),
    base.resize((32, 32), Image.LANCZOS),
    bold.resize((16, 16), Image.LANCZOS),
]
frames[0].save(
    public / "favicon.ico",
    format="ICO",
    append_images=frames[1:],
    sizes=[(48, 48), (32, 32), (16, 16)],
)

apple = load("fullbleed-512.png").convert("RGB").resize((180, 180), Image.LANCZOS)
apple.save(public / "apple-touch-icon.png", format="PNG")
print("Iconos generados: public/favicon.ico y public/apple-touch-icon.png")
PY
