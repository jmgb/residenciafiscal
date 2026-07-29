"""Enlaza el corpus de sentencias con el corpus normativo.

Lee el JSONL del análisis y los preceptos publicados y escribe en
`knowledge/normativa/<jurisdiccion>/enlaces/` dos vistas del mismo hecho:

- `jurisprudencia.json` — por sentencia: qué preceptos cita, con qué certeza y
  qué redacción regía sus ejercicios.
- `por_precepto.json` — el índice inverso, que es el que sirve para responder
  «qué han dicho los tribunales sobre el art. 9.1.b».

No modifica ni las sentencias ni los preceptos. La relación entre dos corpus es
un tercer artefacto: meterla dentro del texto legal lo contaminaría, y meterla en
los perfiles de sentencia obligaría a regenerarlos por un motivo ajeno.

    uv run python enlazar_normativa.py --jsonl output/analisis_*.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from normativa_citas import cargar_preceptos, enlazar_registro

SCHEMA_VERSION = "residenciafiscal-normativa-enlaces/1"
GENERADOR = "residenciafiscal-normativa/0.1.0"


def cargar_jsonl(ruta: Path) -> list[dict]:
    with ruta.open(encoding="utf-8") as fichero:
        return [json.loads(linea) for linea in fichero if linea.strip()]


def indice_inverso(enlaces: list[dict], titulos: dict[str, str]) -> list[dict]:
    """Agrupa por precepto las sentencias que lo citan."""
    por_slug: dict[str, list[dict]] = defaultdict(list)
    for enlace in enlaces:
        for precepto in enlace["preceptos"]:
            por_slug[precepto["slug"]].append(
                {
                    "archivo": enlace["archivo"],
                    "roj": enlace["roj"],
                    "ejercicios": enlace["ejercicios"],
                    "apartado": precepto["apartado"],
                    "certeza": precepto["certeza"],
                    "texto_citado": precepto["texto_citado"],
                }
            )

    return [
        {
            "slug": slug,
            "titulo": titulos.get(slug),
            "sentencias": sorted(citas, key=lambda c: str(c["archivo"])),
            "total_sentencias": len({c["archivo"] for c in citas}),
        }
        for slug, citas in sorted(por_slug.items())
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jsonl", type=Path, required=True)
    parser.add_argument("--jurisdiccion", default="es")
    parser.add_argument("--corpus-root", type=Path, default=Path("knowledge/normativa"))
    args = parser.parse_args()

    base = args.corpus_root / args.jurisdiccion
    catalogo = cargar_preceptos(base / "preceptos")
    if not catalogo:
        print(f"❌ No hay preceptos publicados en {base / 'preceptos'}")
        return 1

    registros = cargar_jsonl(args.jsonl)
    enlaces = [enlazar_registro(registro, catalogo) for registro in registros]
    titulos = {p.slug: p.titulo for lista in catalogo.values() for p in lista}

    destino = base / "enlaces"
    destino.mkdir(parents=True, exist_ok=True)

    con_precepto = [e for e in enlaces if e["preceptos"]]
    total_citas = sum(len(e["preceptos"]) for e in enlaces)
    explicitas = sum(1 for e in enlaces for p in e["preceptos"] if p["certeza"] == "explicita")
    no_resueltas = sum(len(e["citas_no_resueltas"]) for e in enlaces)
    avisos = [{"archivo": e["archivo"], "avisos": e["avisos"]} for e in enlaces if e["avisos"]]

    cabecera = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERADOR,
        "jurisdiccion": args.jurisdiccion,
        "jsonl": args.jsonl.name,
        "sentencias": len(enlaces),
        "sentencias_con_precepto": len(con_precepto),
        "enlaces": total_citas,
        "enlaces_explicitos": explicitas,
        "enlaces_inferidos": total_citas - explicitas,
        "citas_no_resueltas": no_resueltas,
        "avisos": avisos,
    }

    (destino / "jurisprudencia.json").write_text(
        json.dumps({**cabecera, "sentencias_detalle": enlaces}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    inverso = indice_inverso(enlaces, titulos)
    (destino / "por_precepto.json").write_text(
        json.dumps(
            {**cabecera, "preceptos_citados": len(inverso), "preceptos": inverso},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        f"✅ {total_citas} enlaces ({explicitas} explícitos, {total_citas - explicitas} "
        f"inferidos) sobre {len(con_precepto)}/{len(enlaces)} sentencias"
    )
    print(f"   {len(inverso)} preceptos citados | {no_resueltas} citas sin precepto publicado")
    for aviso in avisos:
        print(f"⚠️  {aviso['archivo']}: {aviso['avisos'][0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
