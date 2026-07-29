"""Descarga de la API de datos abiertos del BOE la normativa de residencia fiscal.

Es el equivalente normativo de bajarse los PDF del CENDOJ: deja en
`normativa/es/` el XML tal cual lo sirve el BOE, sin reescribir nada, más un
`manifest.json` con el hash y la fecha de actualización de cada norma.
`export_normativa.py` trabaja después sobre esos ficheros, ya sin red.

**Este script es el lector de España.** Habla solo con la API del BOE y no
pretende ser genérico: otra jurisdicción tendrá otra fuente, otro formato y otra
noción de consolidación, y su lector vivirá en su propio módulo escribiendo en
`normativa/<código ISO>/`. El contrato común está en `docs/NORMATIVA.md`.

Se descarga el **texto íntegro** de cada norma aunque solo se publiquen algunos
preceptos: la fuente completa es lo que hace auditable la selección.

    uv run python descargar_normativa.py --output-dir normativa/es
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

API_CONSOLIDADA = "https://www.boe.es/datosabiertos/api/legislacion-consolidada"
API_DIARIO = "https://www.boe.es/diario_boe/xml.php"
PAGINA_INDICE = 5000

# Núcleo estatal. La elección es jurídica: son las normas que deciden la
# residencia fiscal de una persona física o la prueba de esa residencia.
NUCLEO: tuple[str, ...] = (
    "BOE-A-2006-20764",  # Ley 35/2006, IRPF
    "BOE-A-2007-6820",  # RD 439/2007, Reglamento del IRPF
    "BOE-A-2003-23186",  # Ley 58/2003, General Tributaria
    "BOE-A-2004-4527",  # RDLeg 5/2004, TR del IRNR
    "BOE-A-2023-3508",  # Orden HFP/115/2023, jurisdicciones no cooperativas
)

# Normas derogadas: ya no están en la base consolidada, así que se descarga su
# publicación original en el diario. El BOE no las borra, solo las saca del
# texto consolidado, y varias sentencias del corpus siguen aplicándolas.
NUCLEO_DEROGADO: dict[str, str] = {
    # Rige los ejercicios 2005-2006, que sí aparecen en el corpus de sentencias.
    "BOE-A-2004-4347": "RDLeg 3/2004, TR del IRPF, derogado por la Ley 35/2006",
}

# Los convenios de doble imposición vigentes no se listan a mano: se localizan
# por título en el índice de legislación consolidada, que es la lista viva del
# BOE.
FILTRO_CDI = "doble imposici"

# Convenios sustituidos, que por eso ya no aparecen en ese índice. Se citan en
# sentencias del corpus porque regían el ejercicio enjuiciado, así que hay que
# bajarlos del diario igual que las normas estatales derogadas.
CDI_DEROGADO: dict[str, str] = {
    # SAN/STS sobre ejercicios anteriores a 2013 lo aplican; sustituido por el
    # convenio de 2013 (BOE-A-2014-373) tras la denuncia de 2012.
    "BOE-A-1994-20084": "CDI España-Argentina de 1992, sustituido por el de 2013",
    # Sustituido por el convenio de 2013 (BOE-A-2014-5171); una sentencia del
    # corpus razona expresamente sobre esta redacción.
    "BOE-A-1976-23347": "CDI España-Reino Unido de 1975, sustituido por el de 2013",
}


def _fetch(url: str, reintentos: int = 3) -> bytes:
    peticion = urllib.request.Request(url, headers={"Accept": "application/xml"})
    for intento in range(reintentos):
        try:
            with urllib.request.urlopen(peticion, timeout=180) as respuesta:
                return bytes(respuesta.read())
        except (urllib.error.URLError, TimeoutError) as error:
            if intento == reintentos - 1:
                raise
            print(f"    reintento {intento + 1} tras {error}", flush=True)
            time.sleep(2 * (intento + 1))
    raise RuntimeError("inalcanzable")


def _campo(xml: str, nombre: str) -> str | None:
    encontrado = re.search(rf"<{nombre}[^>]*>(.*?)</{nombre}>", xml, re.S)
    return encontrado.group(1).strip() if encontrado else None


def descargar_indice() -> list[tuple[str, str]]:
    """Identificador y título de toda la legislación consolidada vigente."""
    entradas: list[tuple[str, str]] = []
    desplazamiento = 0
    while True:
        pagina = _fetch(f"{API_CONSOLIDADA}?limit={PAGINA_INDICE}&offset={desplazamiento}").decode(
            "utf-8"
        )
        elementos = re.findall(r"<item>(.*?)</item>", pagina, re.S)
        if not elementos:
            break
        for elemento in elementos:
            identificador = _campo(elemento, "identificador")
            titulo = _campo(elemento, "titulo")
            if identificador and titulo:
                entradas.append((identificador, re.sub(r"\s+", " ", titulo)))
        print(f"  índice: {len(entradas)} normas", flush=True)
        if len(elementos) < PAGINA_INDICE:
            break
        desplazamiento += PAGINA_INDICE
    return entradas


def descargar_consolidada(destino: Path, boe_id: str, grupo: str) -> dict[str, object]:
    metadatos = _fetch(f"{API_CONSOLIDADA}/id/{boe_id}").decode("utf-8")
    if "<code>200</code>" not in metadatos:
        raise RuntimeError(f"{boe_id}: la API no devuelve metadatos")
    texto = _fetch(f"{API_CONSOLIDADA}/id/{boe_id}/texto")

    (destino / f"{boe_id}.meta.xml").write_text(metadatos, encoding="utf-8")
    (destino / f"{boe_id}.texto.xml").write_bytes(texto)

    return {
        "id": boe_id,
        "grupo": grupo,
        "titulo": _campo(metadatos, "titulo"),
        "rango": _campo(metadatos, "rango"),
        "fecha_disposicion": _campo(metadatos, "fecha_disposicion"),
        "fecha_publicacion": _campo(metadatos, "fecha_publicacion"),
        "fecha_vigencia": _campo(metadatos, "fecha_vigencia"),
        "vigencia_agotada": _campo(metadatos, "vigencia_agotada"),
        "fecha_actualizacion_boe": _campo(metadatos, "fecha_actualizacion"),
        "url_eli": _campo(metadatos, "url_eli"),
        "url_html_consolidada": _campo(metadatos, "url_html_consolidada"),
        "bloques": len(re.findall(r"<bloque id=", texto.decode("utf-8"))),
        "texto_bytes": len(texto),
        "texto_sha256": hashlib.sha256(texto).hexdigest(),
    }


def descargar_diario(destino: Path, boe_id: str, grupo: str, nota: str) -> dict[str, object]:
    documento = _fetch(f"{API_DIARIO}?id={boe_id}")
    (destino / f"{boe_id}.diario.xml").write_bytes(documento)
    texto = documento.decode("utf-8", "replace")
    return {
        "id": boe_id,
        "grupo": grupo,
        "titulo": _campo(texto, "titulo"),
        "rango": _campo(texto, "rango"),
        "fecha_disposicion": _campo(texto, "fecha_disposicion"),
        "fecha_publicacion": _campo(texto, "fecha_publicacion"),
        "nota": nota,
        "fuente_endpoint": API_DIARIO,
        "texto_bytes": len(documento),
        "texto_sha256": hashlib.sha256(documento).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("normativa/es"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print("Descargando el índice de legislación consolidada…")
    indice = descargar_indice()
    cdis = [
        identificador
        for identificador, titulo in indice
        if FILTRO_CDI in titulo.lower() and identificador not in NUCLEO
    ]
    derogadas = {
        **{boe_id: ("nucleo_derogado", nota) for boe_id, nota in NUCLEO_DEROGADO.items()},
        **{boe_id: ("cdi_derogado", nota) for boe_id, nota in CDI_DEROGADO.items()},
    }
    print(f"Núcleo: {len(NUCLEO)} | CDI vigentes: {len(cdis)} | derogadas: {len(derogadas)}")

    registros: list[dict[str, object]] = []
    fallos: list[dict[str, str]] = []

    objetivos = [(boe_id, "nucleo") for boe_id in NUCLEO]
    objetivos += [(boe_id, "cdi") for boe_id in cdis]
    for boe_id, grupo in objetivos:
        print(f"  {boe_id} [{grupo}]", flush=True)
        try:
            registros.append(descargar_consolidada(args.output_dir, boe_id, grupo))
        except Exception as error:  # noqa: BLE001 - queremos el inventario completo
            print(f"    FALLO: {error}", flush=True)
            fallos.append({"id": boe_id, "error": str(error)})

    for boe_id, (grupo, nota) in derogadas.items():
        print(f"  {boe_id} [{grupo}]", flush=True)
        try:
            registros.append(descargar_diario(args.output_dir, boe_id, grupo, nota))
        except Exception as error:  # noqa: BLE001
            print(f"    FALLO: {error}", flush=True)
            fallos.append({"id": boe_id, "error": str(error)})

    (args.output_dir / "manifest.json").write_text(
        json.dumps(
            {
                "fuente": "API de datos abiertos del BOE",
                "endpoint_consolidada": API_CONSOLIDADA,
                "endpoint_diario": API_DIARIO,
                "normas": registros,
                "fallos": fallos,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"\n✅ {len(registros)} normas en {args.output_dir}/ | fallos: {len(fallos)}")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
