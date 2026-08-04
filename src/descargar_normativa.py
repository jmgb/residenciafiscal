"""Descarga de la API de datos abiertos del BOE la normativa de residencia fiscal.

Es el equivalente normativo de bajarse los PDF del CENDOJ: deja en
`normativa/es/` el XML tal cual lo sirve el BOE, sin reescribir nada, más un
`manifest.json` con el hash y la fecha de actualización de cada norma.
`export_normativa.py` trabaja después sobre esos ficheros, ya sin red.

**Este script es el lector de España.** Habla solo con la API del BOE y no
pretende ser genérico: otra jurisdicción tendrá otra fuente, otro formato y otra
noción de consolidación, y su lector vivirá en su propio módulo escribiendo en
`normativa/<código ISO>/`. El contrato común está en `docs/normativa/NORMATIVA.md`.

Se descarga el **texto íntegro** de cada norma aunque solo se publiquen algunos
preceptos: la fuente completa es lo que hace auditable la selección.

    uv run python src/descargar_normativa.py --output-dir normativa/es
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

# Convenios **en vigor** que ese índice no devuelve. No son un fallo del filtro
# que se pueda arreglar ampliándolo: el motivo es distinto en cada uno y está
# comprobado contra el BOE, así que se declaran a mano y se bajan del diario.
# Sin ellos, la página de esos países no podría enlazar su convenio.
CDI_NO_CONSOLIDADO: dict[str, str] = {
    # El título dice «doble tributación», no «doble imposición», así que el
    # filtro por título no lo encuentra. Sigue en vigor desde el 29-4-2003.
    "BOE-A-2004-11070": "CDI España-Venezuela de 2003; su título dice «doble tributación»",
    # Publicado en 2024 y todavía fuera de la base de legislación consolidada:
    # `act.php` redirige y la API consolidada no lo sirve.
    "BOE-A-2024-15573": "CDI España-Paraguay de 2023, aún no incorporado a la base consolidada",
}

# Normas que el filtro por título arrastra al grupo `cdi` sin ser un convenio
# general de doble imposición sobre la renta. No es un fallo del filtro que se
# arregle afinando el texto: el BOE las titula así porque tratan de doble
# imposición, solo que una es derecho interno y las otras dos son convenios
# sectoriales de transporte. Ninguna contiene regla de residencia, y dejarlas en
# `cdi` haría que la relación bilateral de Venezuela apuntase a un convenio de
# navegación marítima y aérea con el nombre correcto encima.
#
# La lista es la misma que `export_normativa.SIN_PRECEPTO_RESIDENCIA`, y hay un
# test que impide que las dos descripciones del mismo hecho diverjan.
RECLASIFICACION: dict[str, tuple[str, str]] = {
    "BOE-A-1996-28330": (
        "interna_no_cdi",
        "Ley 10/1996: doble imposición interna intersocietaria, no es un tratado",
    ),
    "BOE-A-1989-2339": (
        "cdi_sectorial",
        "Convenio con Venezuela de navegación marítima y aérea, sin regla de residencia",
    ),
    "BOE-A-1983-5313": (
        "cdi_sectorial",
        "Convenio con Argentina de navegación marítima y aérea, sin regla de residencia",
    ),
}

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

# Normas que ya no deben formar parte del inventario porque han dejado de ser
# necesarias y no siguen citándose. Una baja exige motivo y evita que la
# protección del manifiesto convierta una decisión deliberada en un silencio.
BAJAS_DECLARADAS: dict[str, str] = {}


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
        "fuente": "consolidada",
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
        "fuente": "diario",
        "titulo": _campo(texto, "titulo"),
        "rango": _campo(texto, "rango"),
        "fecha_disposicion": _campo(texto, "fecha_disposicion"),
        "fecha_publicacion": _campo(texto, "fecha_publicacion"),
        "nota": nota,
        "fuente_endpoint": API_DIARIO,
        "texto_bytes": len(documento),
        "texto_sha256": hashlib.sha256(documento).hexdigest(),
    }


def normas_del_diario() -> dict[str, tuple[str, str]]:
    """Normas cuya fuente es el diario, con su grupo y el motivo de estarlo.

    Dos razones distintas para el mismo formato de origen: unas están derogadas
    y el BOE las ha sacado de la base consolidada, y otras están **en vigor**
    pero esa base no las sirve. El grupo distingue una cosa de la otra; el
    fichero descargado es el mismo `<id>.diario.xml`.
    """
    return {
        **{boe_id: ("nucleo_derogado", nota) for boe_id, nota in NUCLEO_DEROGADO.items()},
        **{boe_id: ("cdi_derogado", nota) for boe_id, nota in CDI_DEROGADO.items()},
        **{boe_id: ("cdi", nota) for boe_id, nota in CDI_NO_CONSOLIDADO.items()},
    }


def cdis_del_indice(indice: list[tuple[str, str]]) -> tuple[list[str], list[str]]:
    """Convenios a pedir consolidados, y los declarados a mano que ya sobran.

    Un convenio de `CDI_NO_CONSOLIDADO` que el BOE acabe consolidando aparecería
    a la vez en el índice y en la tabla, y se descargaría dos veces: dos
    registros con el mismo identificador en el manifiesto y dos fuentes
    compitiendo por el mismo precepto. Mientras siga declarado gana la tabla, y
    el segundo valor devuelto es el aviso para retirarlo.
    """
    del_diario = normas_del_diario()
    candidatos = [
        identificador
        for identificador, titulo in indice
        if FILTRO_CDI in titulo.lower() and identificador not in NUCLEO
    ]
    return (
        [identificador for identificador in candidatos if identificador not in del_diario],
        sorted(set(candidatos) & set(CDI_NO_CONSOLIDADO)),
    )


def grupo_declarado(boe_id: str) -> tuple[str, str] | None:
    """Grupo y motivo de una norma listada a mano, o `None` si sale del índice."""
    if boe_id in NUCLEO:
        return ("nucleo", "")
    return normas_del_diario().get(boe_id)


def grupo_del_indice(boe_id: str) -> tuple[str, str]:
    """Grupo de un convenio que llega por el filtro de título del índice.

    Casi siempre es `cdi`; las excepciones están curadas en `RECLASIFICACION`
    porque distinguir un convenio general de renta de una ley interna o de un
    convenio sectorial es una decisión jurídica, no un ajuste del filtro.
    """
    return RECLASIFICACION.get(boe_id, ("cdi", ""))


def fusionar_manifiesto(
    previo: dict, registros: list[dict[str, object]]
) -> list[dict[str, object]]:
    """Sustituye en el manifiesto previo los registros recién descargados.

    Descargar solo una norma no puede borrar el inventario de las otras 103: sin
    esta fusión, `--solo` dejaría un manifiesto que `export_normativa.py` leería
    como «el corpus tiene una norma».
    """
    nuevos = {str(registro["id"]): registro for registro in registros}
    fusionados = [nuevos.pop(str(r["id"]), r) for r in previo.get("normas", [])]
    return fusionados + list(nuevos.values())


def desapariciones_no_declaradas(
    previo: dict, registros: list[dict[str, object]], bajas: set[str] | None = None
) -> list[str]:
    """Devuelve las normas del manifiesto previo que faltan sin una baja explícita."""
    anteriores = {str(registro["id"]) for registro in previo.get("normas", [])}
    actuales = {str(registro["id"]) for registro in registros}
    return sorted(anteriores - actuales - (bajas or set()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("normativa/es"))
    parser.add_argument(
        "--solo",
        nargs="+",
        metavar="BOE-ID",
        help=(
            "Descarga únicamente estas normas y las fusiona con el manifiesto existente, "
            "sin pedir el índice completo. Para incorporar una norma nueva sin volver a "
            "bajar las 104."
        ),
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifiesto_path = args.output_dir / "manifest.json"

    del_diario = normas_del_diario()
    if args.solo:
        # Un CDI que sale del índice no está declarado en ninguna tabla: si no
        # lo conocemos, es uno de esos y se pide a la base consolidada.
        objetivos = [
            (boe_id, grupo_declarado(boe_id) or grupo_del_indice(boe_id)) for boe_id in args.solo
        ]
        consolidadas = [
            (boe_id, grupo) for boe_id, (grupo, _) in objetivos if boe_id not in del_diario
        ]
        diario = {boe_id: par for boe_id, par in objetivos if boe_id in del_diario}
        print(f"Descarga selectiva: {len(consolidadas)} consolidadas | {len(diario)} del diario")
    else:
        print("Descargando el índice de legislación consolidada…")
        indice = descargar_indice()
        cdis, ya_consolidados = cdis_del_indice(indice)
        for boe_id in ya_consolidados:
            print(
                f"  ⚠️ {boe_id} ya está en el índice consolidado: quítalo de "
                "CDI_NO_CONSOLIDADO para bajarlo consolidado.",
                flush=True,
            )
        consolidadas = [(boe_id, "nucleo") for boe_id in NUCLEO]
        consolidadas += [(boe_id, grupo_del_indice(boe_id)[0]) for boe_id in cdis]
        diario = del_diario
        print(f"Núcleo: {len(NUCLEO)} | CDI vigentes: {len(cdis)} | del diario: {len(diario)}")

    registros: list[dict[str, object]] = []
    fallos: list[dict[str, str]] = []

    for boe_id, grupo in consolidadas:
        print(f"  {boe_id} [{grupo}]", flush=True)
        try:
            registros.append(descargar_consolidada(args.output_dir, boe_id, grupo))
        except Exception as error:  # noqa: BLE001 - queremos el inventario completo
            print(f"    FALLO: {error}", flush=True)
            fallos.append({"id": boe_id, "error": str(error)})

    for boe_id, (grupo, nota) in diario.items():
        print(f"  {boe_id} [{grupo}]", flush=True)
        try:
            registros.append(descargar_diario(args.output_dir, boe_id, grupo, nota))
        except Exception as error:  # noqa: BLE001
            print(f"    FALLO: {error}", flush=True)
            fallos.append({"id": boe_id, "error": str(error)})

    if args.solo and manifiesto_path.exists():
        previo = json.loads(manifiesto_path.read_text(encoding="utf-8"))
        registros = fusionar_manifiesto(previo, registros)
    elif manifiesto_path.exists():
        previo = json.loads(manifiesto_path.read_text(encoding="utf-8"))
        desaparecidas = desapariciones_no_declaradas(
            previo, registros, bajas=set(BAJAS_DECLARADAS)
        )
        if desaparecidas:
            raise RuntimeError(
                "La descarga eliminaría normas del manifiesto sin declaración: "
                f"{', '.join(desaparecidas)}. Si siguen citándose, añádelas a "
                "CDI_DEROGADO; si no, regístralas en BAJAS_DECLARADAS con su motivo."
            )

    manifiesto_path.write_text(
        json.dumps(
            {
                "fuente": "API de datos abiertos del BOE",
                "endpoint_consolidada": API_CONSOLIDADA,
                "endpoint_diario": API_DIARIO,
                "normas": registros,
                "bajas": [
                    {"id": boe_id, "motivo": motivo}
                    for boe_id, motivo in sorted(BAJAS_DECLARADAS.items())
                ],
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
