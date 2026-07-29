"""Genera el corpus de preceptos legales en Markdown a partir del XML del BOE.

Es el equivalente normativo de `export_okf.py`: donde aquel produce un perfil
por sentencia, este produce un fichero por **precepto** —el artículo, no la ley
entera— porque el corpus solo necesita las normas que deciden la residencia
fiscal, no los miles de artículos restantes de la LIRPF o la LGT.

No hay LLM en ningún paso. El texto legal sale literal del XML consolidado y
todo lo derivado (selección, rúbrica, hashes) es determinista.

    uv run python export_normativa.py --sources-dir normativa --output-dir knowledge/normativa
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import yaml

from normativa_boe import (
    BloqueNorma,
    NormaBOE,
    cargar_norma,
    cargar_norma_diario,
    formatear_fecha,
)

SCHEMA_VERSION = "residenciafiscal-normativa/1"
GENERADOR = "residenciafiscal-normativa/0.1.0"

# --- Selección de preceptos --------------------------------------------------
#
# Núcleo estatal: se listan uno a uno porque la elección es jurídica, no
# automatizable. El criterio es «precepto que decide o condiciona la residencia
# fiscal de una persona física, o la prueba de esa residencia».

SELECCION_ESTATAL: dict[str, tuple[str, ...]] = {
    # Ley 35/2006, IRPF
    "BOE-A-2006-20764": (
        "a8",  # Contribuyentes (incluye la cuarentena por traslado a paraíso fiscal)
        "a9",  # Residencia habitual en territorio español: el precepto central
        "a10",  # Residencia habitual en territorio extranjero (diplomáticos)
        "a72",  # Residencia habitual en el territorio de una Comunidad Autónoma
    ),
    # Ley 58/2003, General Tributaria
    "BOE-A-2003-23186": (
        "a105",  # Carga de la prueba
        "a106",  # Normas sobre medios y valoración de la prueba
        "a108",  # Presunciones en materia tributaria
    ),
    # RDLeg 5/2004, TR del Impuesto sobre la Renta de no Residentes
    "BOE-A-2004-4527": ("a6",),  # Residencia en territorio español
    # RD 439/2007, Reglamento del IRPF
    "BOE-A-2007-6820": ("a120",),  # Certificado de residencia fiscal
    # Orden HFP/115/2023, jurisdicciones no cooperativas
    "BOE-A-2023-3508": ("au", "dt"),
    # RDLeg 3/2004, TR del IRPF: derogado, pero rige los ejercicios 2005-2006
    # que sí aparecen en el corpus de sentencias. Su artículo 9 concentra lo que
    # la Ley 35/2006 repartió entre los artículos 9 y 10, así que basta con él;
    # el artículo 10 de este texto refundido es «Atribución de rentas».
    "BOE-A-2004-4347": ("a8", "a9"),
}

# Nombre corto para el slug del fichero. Solo el núcleo: son seis normas
# escogidas a mano y el nombre es verificable de un vistazo.
SLUG_NORMA: dict[str, str] = {
    "BOE-A-2006-20764": "lirpf",
    "BOE-A-2003-23186": "lgt",
    "BOE-A-2004-4527": "trlirnr",
    "BOE-A-2007-6820": "rirpf",
    "BOE-A-2023-3508": "jurisdicciones-no-cooperativas",
    "BOE-A-2004-4347": "trlirpf-2004",
}

# --- Detección del artículo de residencia de cada CDI ------------------------
#
# La rúbrica no sirve: los convenios la titulan «Residente», «Residencia»,
# «Residencia fiscal» o «Domicilio fiscal» según la época. Lo que sí es estable
# en todos los que siguen el Modelo OCDE es la firma sustantiva del precepto:
# define la doble residencia y la resuelve con la vivienda permanente.

FIRMA_DOBLE_RESIDENCIA = re.compile(r"residente de (?:ambos|los dos) Estados", re.IGNORECASE)
FIRMA_VIVIENDA = re.compile(r"vivienda permanente", re.IGNORECASE)

# Convenios cuya redacción se aparta de esa firma y hay que fijar a mano.
OVERRIDES_CDI: dict[str, str] = {
    "BOE-A-2012-5039": "a4",  # Hong Kong: habla de «Parte contratante», no de Estado
    "BOE-A-1982-14239": "a4",  # Polonia: redacta «residente de los dos Estados»
    "BOE-A-1991-18006": "a1",  # Bulgaria: la residencia está en el ámbito subjetivo
}

# Normas que el índice del BOE devuelve al filtrar por «doble imposición» pero
# que no contienen regla de residencia. No son un fallo del detector.
SIN_PRECEPTO_RESIDENCIA: dict[str, str] = {
    "BOE-A-1996-28330": "Ley interna sobre doble imposición intersocietaria, no es un CDI",
    "BOE-A-1989-2339": "Convenio sectorial de navegación marítima y aérea (Venezuela)",
    "BOE-A-1983-5313": "Convenio sectorial de navegación marítima y aérea (Argentina)",
}


@dataclass(frozen=True)
class PreceptoSeleccionado:
    """Un bloque elegido para publicarse, con su norma y su grupo de origen."""

    norma: NormaBOE
    bloque: BloqueNorma
    grupo: str
    source_sha256: str
    fichero_fuente: str

    @property
    def ruta_fuente(self) -> str:
        """Ruta relativa al XML de origen desde `knowledge/normativa/preceptos/`."""
        return f"../../../normativa/{self.fichero_fuente}"


def recortar(texto: str, limite: int) -> str:
    """Recorta por el último espacio para no partir una palabra por la mitad."""
    if len(texto) <= limite:
        return texto
    return texto[:limite].rsplit(" ", 1)[0].rstrip(" ,;:") + "…"


def slug_norma(boe_id: str, grupo: str) -> str:
    """Prefijo del fichero. Los CDI usan su identificador del BOE.

    Deducir el país del título es inseguro: los 96 convenios lo escriben de
    trece formas distintas y un país equivocado en un nombre de fichero es peor
    que un identificador neutro. El título oficial va en el frontmatter.
    """
    if boe_id in SLUG_NORMA:
        return SLUG_NORMA[boe_id]
    prefijo = "cdi" if grupo == "cdi" else "norma"
    return f"{prefijo}-{boe_id.lower()}"


def slug_precepto(boe_id: str, grupo: str, bloque_id: str) -> str:
    return f"{slug_norma(boe_id, grupo)}-{bloque_id}"


def localizar_precepto_residencia(norma: NormaBOE) -> BloqueNorma | None:
    """Devuelve el artículo que fija la residencia en un CDI, o `None`."""
    if norma.boe_id in OVERRIDES_CDI:
        return norma.bloque(OVERRIDES_CDI[norma.boe_id])
    candidatos = [
        bloque
        for bloque in norma.preceptos
        if FIRMA_DOBLE_RESIDENCIA.search(bloque.texto_completo)
        and FIRMA_VIVIENDA.search(bloque.texto_completo)
    ]
    return candidatos[0] if len(candidatos) == 1 else None


def seleccionar(
    sources_dir: Path, manifiesto: dict
) -> tuple[list[PreceptoSeleccionado], list[dict]]:
    """Recorre el manifiesto y decide qué bloques se publican."""
    seleccionados: list[PreceptoSeleccionado] = []
    incidencias: list[dict] = []

    for registro in manifiesto["normas"]:
        boe_id = str(registro["id"])
        grupo = str(registro["grupo"])
        if boe_id in SIN_PRECEPTO_RESIDENCIA:
            incidencias.append(
                {"id": boe_id, "motivo": SIN_PRECEPTO_RESIDENCIA[boe_id], "esperado": True}
            )
            continue

        # Una norma derogada ya no está en la base consolidada: su fuente es el
        # XML del diario, con otra estructura.
        derogada = grupo == "nucleo_derogado"
        sufijo = "diario" if derogada else "texto"
        norma = (
            cargar_norma_diario(sources_dir, boe_id)
            if derogada
            else cargar_norma(sources_dir, boe_id)
        )
        source_sha256 = hashlib.sha256(
            (sources_dir / f"{boe_id}.{sufijo}.xml").read_bytes()
        ).hexdigest()

        if grupo == "cdi":
            bloque = localizar_precepto_residencia(norma)
            if bloque is None:
                incidencias.append(
                    {
                        "id": boe_id,
                        "motivo": "No se ha podido identificar un único artículo de residencia",
                        "esperado": False,
                        "titulo": norma.titulo,
                    }
                )
                continue
            seleccionados.append(
                PreceptoSeleccionado(norma, bloque, grupo, source_sha256, f"{boe_id}.{sufijo}.xml")
            )
            continue

        for bloque_id in SELECCION_ESTATAL.get(boe_id, ()):
            bloque = norma.bloque(bloque_id)
            if bloque is None:
                incidencias.append(
                    {
                        "id": boe_id,
                        "bloque": bloque_id,
                        "motivo": "El bloque declarado en la selección no existe en el XML",
                        "esperado": False,
                    }
                )
                continue
            seleccionados.append(
                PreceptoSeleccionado(norma, bloque, grupo, source_sha256, f"{boe_id}.{sufijo}.xml")
            )

    return seleccionados, incidencias


# --- Renderizado -------------------------------------------------------------


def _titulo_precepto(seleccion: PreceptoSeleccionado) -> str:
    designacion = seleccion.bloque.titulo or seleccion.bloque.bloque_id
    corto = SLUG_NORMA.get(seleccion.norma.boe_id, "").upper()
    epigrafe = seleccion.bloque.epigrafe
    cabeza = f"{designacion} {corto}".strip() if corto else designacion
    return f"{cabeza} — {epigrafe}" if epigrafe else cabeza


def _frontmatter(seleccion: PreceptoSeleccionado, precepto_sha256: str) -> dict:
    norma, bloque = seleccion.norma, seleccion.bloque
    versiones = [
        {
            "fecha_vigencia": formatear_fecha(v.fecha_vigencia),
            "id_norma_modificadora": v.id_norma,
            "vigente": v is bloque.version_vigente,
        }
        for v in bloque.versiones
    ]
    vigente = bloque.version_vigente
    return {
        "type": "Precepto legal",
        "title": _titulo_precepto(seleccion),
        "description": recortar(f"{bloque.titulo} de {norma.titulo}".rstrip(), 160),
        "resource": seleccion.ruta_fuente,
        "tags": ["residencia-fiscal", "normativa", seleccion.grupo],
        "status": "stable",
        "boe_id": norma.boe_id,
        "norma": norma.titulo,
        "rango": norma.rango,
        "bloque_id": bloque.bloque_id,
        "designacion": bloque.titulo,
        "epigrafe": bloque.epigrafe,
        "grupo": seleccion.grupo,
        "vigencia_agotada": norma.vigencia_agotada,
        "vigente_desde": formatear_fecha(vigente.fecha_vigencia) if vigente else None,
        "versiones": versiones,
        "url_eli": norma.url_eli,
        "url_boe": (
            f"{norma.url_html_consolidada}#{bloque.bloque_id}"
            if norma.url_html_consolidada
            else None
        ),
        "fecha_actualizacion_boe": norma.fecha_actualizacion_boe,
        "source_sha256": seleccion.source_sha256,
        "precepto_sha256": precepto_sha256,
        "schema_version": SCHEMA_VERSION,
        "sources": [
            {
                "id": "texto-consolidado" if not norma.vigencia_agotada else "texto-publicado",
                "resource": seleccion.ruta_fuente,
                "title": f"{norma.boe_id} — texto del BOE",
                "author": "Agencia Estatal Boletín Oficial del Estado",
            }
        ],
        "generated": {"by": GENERADOR},
    }


def _cuerpo(seleccion: PreceptoSeleccionado) -> Iterator[str]:
    bloque = seleccion.bloque
    vigente = bloque.version_vigente

    yield (
        "**Regla de lectura:** el articulado reproduce literalmente el texto consolidado que "
        "publica el BOE. Las notas del BOE son anotación editorial y van en su propia sección; "
        "no forman parte del precepto."
    )
    yield ""

    yield "# Texto vigente"
    yield ""
    if vigente is None:
        yield "_El bloque no contiene ninguna redacción._"
    else:
        for parrafo in vigente.parrafos:
            yield parrafo
            yield ""
        if vigente.tiene_tabla:
            yield (
                "> ⚠️ La redacción original contiene una tabla que este formato no reproduce. "
                "Consulta el XML de origen."
            )
            yield ""

    anteriores = bloque.versiones[:-1]
    yield "# Redacciones anteriores"
    yield ""
    if not anteriores:
        yield "_Sin redacciones anteriores: el precepto no se ha modificado._"
        yield ""
    else:
        for version in anteriores:
            yield f"## Vigente desde {formatear_fecha(version.fecha_vigencia)}"
            yield ""
            for parrafo in version.parrafos:
                yield parrafo
                yield ""

    yield "# Notas del BOE"
    yield ""
    notas = [nota for version in bloque.versiones for nota in version.notas_boe]
    if not notas:
        yield "_Sin notas._"
    else:
        for nota in notas:
            yield f"- {nota}"
    yield ""

    yield "# Procedencia"
    yield ""
    norma = seleccion.norma
    yield f"- **Norma:** {norma.titulo}"
    yield f"- **Identificador BOE:** `{norma.boe_id}`, bloque `{bloque.bloque_id}`"
    if norma.url_eli:
        yield f"- **ELI:** {norma.url_eli}"
    if norma.url_html_consolidada:
        yield f"- **Texto consolidado:** {norma.url_html_consolidada}#{bloque.bloque_id}"
    yield f"- **Actualización del BOE:** {norma.fecha_actualizacion_boe}"
    yield (
        "- **Autoridad:** el texto consolidado del BOE es la fuente. Este fichero se regenera "
        "con `make export-normativa`; no se edita a mano."
    )


def renderizar(seleccion: PreceptoSeleccionado) -> str:
    cuerpo = "\n".join(_cuerpo(seleccion)).rstrip() + "\n"
    precepto_sha256 = hashlib.sha256(seleccion.bloque.texto_completo.encode("utf-8")).hexdigest()
    frontmatter = yaml.safe_dump(
        _frontmatter(seleccion, precepto_sha256),
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )
    return f"---\n{frontmatter}---\n\n{cuerpo}"


def renderizar_indice(seleccionados: list[PreceptoSeleccionado]) -> str:
    nucleo = [s for s in seleccionados if s.grupo != "cdi"]
    cdis = sorted((s for s in seleccionados if s.grupo == "cdi"), key=lambda s: s.norma.titulo)

    lineas = [
        "# Normativa de residencia fiscal",
        "",
        "Preceptos extraídos del texto consolidado del BOE. Un fichero por artículo.",
        "Se regenera con `make export-normativa`; no editar a mano.",
        "",
        "## Núcleo estatal",
        "",
    ]
    for seleccion in nucleo:
        slug = slug_precepto(seleccion.norma.boe_id, seleccion.grupo, seleccion.bloque.bloque_id)
        lineas.append(f"- [{_titulo_precepto(seleccion)}]({slug}.md)")

    lineas += [
        "",
        f"## Convenios de doble imposición ({len(cdis)})",
        "",
        "Artículo que fija la residencia y resuelve la doble residencia de cada convenio.",
        "",
    ]
    for seleccion in cdis:
        slug = slug_precepto(seleccion.norma.boe_id, seleccion.grupo, seleccion.bloque.bloque_id)
        lineas.append(f"- [{seleccion.norma.titulo}]({slug}.md) — {seleccion.bloque.titulo}")

    return "\n".join(lineas) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources-dir", type=Path, default=Path("normativa"))
    parser.add_argument("--output-dir", type=Path, default=Path("knowledge/normativa"))
    args = parser.parse_args()

    manifiesto = json.loads((args.sources_dir / "manifest.json").read_text(encoding="utf-8"))
    seleccionados, incidencias = seleccionar(args.sources_dir, manifiesto)

    destino = args.output_dir / "preceptos"
    destino.mkdir(parents=True, exist_ok=True)
    for fichero in destino.glob("*.md"):
        fichero.unlink()

    for seleccion in seleccionados:
        slug = slug_precepto(seleccion.norma.boe_id, seleccion.grupo, seleccion.bloque.bloque_id)
        (destino / f"{slug}.md").write_text(renderizar(seleccion), encoding="utf-8")
    (destino / "index.md").write_text(renderizar_indice(seleccionados), encoding="utf-8")

    reportes = args.output_dir / "reports"
    reportes.mkdir(parents=True, exist_ok=True)
    inesperadas = [i for i in incidencias if not i["esperado"]]
    (reportes / "extraccion.json").write_text(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "generated_by": GENERADOR,
                "normas_en_manifiesto": len(manifiesto["normas"]),
                "preceptos_generados": len(seleccionados),
                "por_grupo": {
                    grupo: sum(1 for s in seleccionados if s.grupo == grupo)
                    for grupo in sorted({s.grupo for s in seleccionados})
                },
                "incidencias": incidencias,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"✅ {len(seleccionados)} preceptos en {destino}/")
    for incidencia in incidencias:
        marca = "ℹ️ " if incidencia["esperado"] else "⚠️ "
        print(f"{marca}{incidencia['id']}: {incidencia['motivo']}")
    return 1 if inesperadas else 0


if __name__ == "__main__":
    sys.exit(main())
