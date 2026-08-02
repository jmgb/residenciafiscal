"""Exporta la proyección pública de las sentencias y su manifiesto.

    uv run python src/export_public_judgments.py

Escribe en `knowledge/jurisprudencia-v3/publico/` un fichero por sentencia
candidata más un `manifest.json` con el hash de cada proyección. El frontend
consume eso —nunca los casos canónicos— y el build público solo materializa lo
que el manifiesto declara `published`.

Tres estados, y ninguno lo decide el frontend:

- `internal_preview`: lo calcula la proyección; hay algún elemento sin aprobación
  humana. Renderizable en preview, jamás indexable.
- `publishable`: todos los elementos proyectados están `HUMAN_APPROVED`.
- `published`: además ha pasado el gate editorial del lote. Se declara en
  `LOTES_PUBLICADOS`, y solo puede contener casos ya `publishable`.

Solo entran los 67 casos con `is_tax_residence_case`. Los 39 restantes tienen
`issue_type: OTHER` y su análisis no habla de residencia fiscal (D4).
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from public_judgment_projection import (
    EstadoPublicacion,
    proyectar,
    render_public_judgment,
)

RAIZ = Path(__file__).resolve().parents[1]
CASOS_POR_DEFECTO = RAIZ / "knowledge" / "jurisprudencia-v3" / "cases"
SALIDA_POR_DEFECTO = RAIZ / "knowledge" / "jurisprudencia-v3" / "publico"

MANIFEST_SCHEMA_VERSION = "residenciafiscal-public-judgments/1"

# Lotes que han superado el gate editorial y jurídico. Vacío a propósito: la
# fase C2 está aplazada por falta de revisor humano, y ningún caso puede pasar a
# `published` mientras su análisis siga siendo `AGENT_REVIEWED`.
LOTES_PUBLICADOS: dict[str, tuple[str, ...]] = {}


def _judgment_ids_publicados() -> set[str]:
    return {judgment_id for lote in LOTES_PUBLICADOS.values() for judgment_id in lote}


def construir_manifiesto(casos: list[dict]) -> dict:
    """Manifiesto con el estado y el hash de cada proyección candidata."""
    publicados = _judgment_ids_publicados()
    entradas: list[dict[str, object]] = []
    for caso in casos:
        if not caso["judgment"]["is_tax_residence_case"]:
            continue
        proyeccion = proyectar(caso)
        contenido = render_public_judgment(caso)
        judgment_id = proyeccion.judgment.judgment_id

        estado = str(proyeccion.publication_state)
        if judgment_id in publicados:
            if proyeccion.publication_state != EstadoPublicacion.PUBLISHABLE:
                raise ValueError(
                    f"{judgment_id} figura en un lote publicado pero su proyección es "
                    f"{estado}: el gate humano no se salta desde el lote."
                )
            estado = "published"

        entradas.append(
            {
                "judgmentId": judgment_id,
                "roj": proyeccion.judgment.roj,
                "court": proyeccion.judgment.court,
                "decisionDate": proyeccion.judgment.decision_date,
                "taxYears": list(proyeccion.judgment.tax_years),
                "criterionIds": sorted(
                    {
                        criterio
                        for cuestion in proyeccion.issues
                        for criterio in cuestion.criterion_ids
                    }
                ),
                "outcomes": sorted(
                    {cuestion.holding.outcome for cuestion in proyeccion.issues if cuestion.holding}
                ),
                "jurisdictions": [j.code for j in proyeccion.jurisdictions],
                "publicationState": estado,
                "legalReview": proyeccion.judgment.review.legal,
                "projectionSha256": hashlib.sha256(contenido.encode("utf-8")).hexdigest(),
                "sourceSha256": proyeccion.judgment.source_sha256,
            }
        )

    entradas.sort(key=lambda entrada: str(entrada["judgmentId"]))
    return {
        "schemaVersion": MANIFEST_SCHEMA_VERSION,
        # §7.1: ningún consumidor debe deducir la jurisdicción de la ruta física.
        "jurisdiction": "es",
        "candidates": len(entradas),
        "published": sum(1 for e in entradas if e["publicationState"] == "published"),
        "judgments": entradas,
    }


def render_manifiesto(casos: list[dict]) -> str:
    return json.dumps(construir_manifiesto(casos), ensure_ascii=False, indent=2) + "\n"


def cargar_casos(directorio: Path) -> list[dict]:
    return [
        json.loads(ruta.read_text(encoding="utf-8"))
        for ruta in sorted(directorio.glob("*.case.json"))
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases-dir", type=Path, default=CASOS_POR_DEFECTO)
    parser.add_argument("--output-dir", type=Path, default=SALIDA_POR_DEFECTO)
    parser.add_argument(
        "--check",
        action="store_true",
        help="No escribe: falla si algún artefacto versionado está desactualizado.",
    )
    args = parser.parse_args()

    casos = cargar_casos(args.cases_dir)
    if not casos:
        print(f"❌ No hay casos en {args.cases_dir}")
        return 1

    manifiesto = construir_manifiesto(casos)
    candidatos = {entrada["judgmentId"] for entrada in manifiesto["judgments"]}

    args.output_dir.mkdir(parents=True, exist_ok=True)
    desactualizados: list[str] = []

    def comparar_o_escribir(destino: Path, contenido: str) -> None:
        if args.check:
            if not destino.exists() or destino.read_text(encoding="utf-8") != contenido:
                desactualizados.append(destino.name)
            return
        destino.write_text(contenido, encoding="utf-8")

    for caso in casos:
        judgment_id = caso["judgment"]["judgment_id"]
        if judgment_id not in candidatos:
            continue
        comparar_o_escribir(
            args.output_dir / f"{judgment_id}.public.json", render_public_judgment(caso)
        )
    comparar_o_escribir(args.output_dir / "manifest.json", render_manifiesto(casos))

    if args.check:
        for nombre in desactualizados:
            print(f"  ✗ {nombre}")
        print(f"{'❌' if desactualizados else '✅'} {len(candidatos) + 1} artefactos comprobados")
        return 1 if desactualizados else 0

    print(
        f"✅ {manifiesto['candidates']} proyecciones públicas "
        f"({manifiesto['published']} publicadas) en {args.output_dir}/"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
