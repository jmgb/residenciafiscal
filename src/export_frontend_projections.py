"""Proyecta el catálogo y el registro bilateral a los datos del frontend.

    uv run python src/export_frontend_projections.py

El catálogo canónico vive en Python porque lo comparten el corpus normativo, el
jurisprudencial y los validadores; ponerlo dentro de `frontend/` invertiría la
dependencia y haría que el pipeline dependiera de una aplicación de
presentación. Pero el frontend no puede importar Python, así que recibe dos
proyecciones **generadas y versionadas**:

- `jurisdictions.json`: código, nombre y slug de cada jurisdicción.
- `treatyRelations.json`: qué convenio rige entre España y cada contraparte, con
  sus periodos, y el índice inverso norma → contraparte.

Se versionan para que un clon limpio de Netlify tenga el dato sin ejecutar
Python, y hay un test que falla si quedan desincronizadas. Editarlas a mano no
sirve de nada: la siguiente ejecución las sobrescribe.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from jurisdictions import cargar_catalogo
from treaty_relations import cargar_relaciones

RAIZ = Path(__file__).resolve().parents[1]
DATOS_FRONTEND = RAIZ / "frontend" / "src" / "data"

AVISO = "Generado por src/export_frontend_projections.py. No editar a mano."


def render_jurisdictions() -> str:
    """Catálogo en la forma que consume el frontend, indexado por código."""
    catalogo = cargar_catalogo()
    documento = {
        "$comment": AVISO,
        "jurisdictions": {
            code: {"name": jurisdiccion.name, "slug": jurisdiccion.slug}
            for code, jurisdiccion in sorted(catalogo.items())
        },
    }
    return json.dumps(documento, ensure_ascii=False, indent=2) + "\n"


def render_treaty_relations() -> str:
    """Relaciones bilaterales y su índice inverso por identificador del BOE."""
    relaciones = cargar_relaciones()
    por_contraparte = {
        code: [
            {
                "boeId": instrumento.boe_id,
                "status": instrumento.status,
                "fromTaxYear": instrumento.effective_from_tax_year,
                "toTaxYear": instrumento.effective_to_tax_year,
            }
            for instrumento in relacion.instruments
        ]
        for code, relacion in sorted(relaciones.items())
    }
    # El índice inverso evita que cada consumidor recorra las 92 relaciones para
    # saber de quién es un convenio, que es la pregunta que hacen las fichas.
    por_norma = {
        instrumento.boe_id: code
        for code, relacion in sorted(relaciones.items())
        for instrumento in relacion.instruments
    }
    documento = {
        "$comment": AVISO,
        "sourceJurisdiction": "es",
        "byCounterpart": por_contraparte,
        "byBoeId": dict(sorted(por_norma.items())),
    }
    return json.dumps(documento, ensure_ascii=False, indent=2) + "\n"


PROYECCIONES = {
    "jurisdictions.json": render_jurisdictions,
    "treatyRelations.json": render_treaty_relations,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DATOS_FRONTEND)
    parser.add_argument(
        "--check",
        action="store_true",
        help="No escribe: falla si alguna proyección versionada está desactualizada.",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    desactualizadas: list[str] = []
    for nombre, render in PROYECCIONES.items():
        destino = args.output_dir / nombre
        contenido = render()
        if args.check:
            if not destino.exists() or destino.read_text(encoding="utf-8") != contenido:
                desactualizadas.append(nombre)
            continue
        destino.write_text(contenido, encoding="utf-8")
        print(f"  {destino.relative_to(RAIZ)}")

    if args.check:
        for nombre in desactualizadas:
            print(f"  ✗ {nombre}")
        print(f"{'❌' if desactualizadas else '✅'} {len(PROYECCIONES)} proyecciones comprobadas")
        return 1 if desactualizadas else 0

    print(f"✅ {len(PROYECCIONES)} proyecciones del frontend regeneradas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
