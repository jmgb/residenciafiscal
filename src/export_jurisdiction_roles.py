"""Escribe el sidecar de roles jurisdiccionales de cada caso canónico v3.

    uv run python src/export_jurisdiction_roles.py

No toca los casos: escribe un fichero por sentencia en
`knowledge/jurisprudencia-v3/jurisdicciones/`. Es determinista, así que
ejecutarlo dos veces seguidas no produce ningún cambio; esa es la comprobación
del Gate A.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from jurisdiction_roles import render_sidecar

RAIZ = Path(__file__).resolve().parents[1]
CASOS_POR_DEFECTO = RAIZ / "knowledge" / "jurisprudencia-v3" / "cases"
SALIDA_POR_DEFECTO = RAIZ / "knowledge" / "jurisprudencia-v3" / "jurisdicciones"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases-dir", type=Path, default=CASOS_POR_DEFECTO)
    parser.add_argument("--output-dir", type=Path, default=SALIDA_POR_DEFECTO)
    parser.add_argument(
        "--check",
        action="store_true",
        help="No escribe: falla si algún sidecar versionado está desactualizado.",
    )
    args = parser.parse_args()

    rutas = sorted(args.cases_dir.glob("*.case.json"))
    if not rutas:
        print(f"❌ No hay casos en {args.cases_dir}")
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    desactualizados: list[str] = []
    for ruta in rutas:
        caso = json.loads(ruta.read_text(encoding="utf-8"))
        contenido = render_sidecar(caso)
        destino = args.output_dir / f"{caso['judgment']['judgment_id']}.roles.json"
        if args.check:
            if not destino.exists() or destino.read_text(encoding="utf-8") != contenido:
                desactualizados.append(destino.name)
            continue
        destino.write_text(contenido, encoding="utf-8")

    if args.check:
        for nombre in desactualizados:
            print(f"  ✗ {nombre}")
        print(f"{'❌' if desactualizados else '✅'} {len(rutas)} sidecars comprobados")
        return 1 if desactualizados else 0

    print(f"✅ {len(rutas)} sidecars de roles en {args.output_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
