"""Tests del parseo del XML del BOE y del corpus de preceptos generado.

Los ficheros de `normativa/` están versionados igual que los PDF de
`sentencias/`, así que estos tests trabajan contra la fuente real: no hay red ni
LLM, y una regresión en el parser se detecta sobre el texto legal de verdad.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from export_normativa import (
    SELECCION_ESTATAL,
    SIN_PRECEPTO_RESIDENCIA,
    localizar_precepto_residencia,
    recortar,
    renderizar,
    seleccionar,
)
from normativa_boe import cargar_norma, cargar_norma_diario, formatear_fecha, normalizar_espacios

RAIZ = Path(__file__).parents[1]
FUENTES = RAIZ / "normativa"
PRECEPTOS = RAIZ / "knowledge" / "normativa" / "preceptos"

LIRPF = "BOE-A-2006-20764"
CDI_SUIZA = "BOE-A-1967-3470"
TRLIRPF_2004 = "BOE-A-2004-4347"


@pytest.fixture(scope="module")
def manifiesto() -> dict:
    return json.loads((FUENTES / "manifest.json").read_text(encoding="utf-8"))


# --- Parser ------------------------------------------------------------------


def test_normalizar_espacios_colapsa_el_espacio_duro_del_boe() -> None:
    assert normalizar_espacios("Artículo\xa09") == "Artículo 9"
    assert normalizar_espacios("  uno\n\n  dos tres ") == "uno dos tres"


def test_normalizar_espacios_no_toca_ningun_caracter_del_texto_legal() -> None:
    """NFKC convertiría `1.º` en `1.o`: eso es reescribir la norma, no formatearla."""
    assert normalizar_espacios("apartado 1.º y 2.ª") == "apartado 1.º y 2.ª"
    assert normalizar_espacios("n.º 35/2006 «residente»") == "n.º 35/2006 «residente»"


def test_los_ordinales_del_boe_sobreviven_al_corpus_publicado() -> None:
    """Regresión: el art. 72 LIRPF cita otros preceptos con ordinales voladitos."""
    articulo = cargar_norma(FUENTES, LIRPF).bloque("a72")
    assert articulo is not None
    assert "º" in articulo.texto_completo

    publicado = (PRECEPTOS / "lirpf-a72.md").read_text(encoding="utf-8")
    assert publicado.count("º") == articulo.texto_completo.count("º")


def test_formatear_fecha_convierte_el_formato_compacto_del_boe() -> None:
    assert formatear_fecha("20070101") == "2007-01-01"
    assert formatear_fecha(None) is None
    assert formatear_fecha("2007-01-01") == "2007-01-01"


def test_recortar_no_parte_palabras() -> None:
    assert recortar("uno dos tres", 100) == "uno dos tres"
    assert recortar("uno dos tres", 8) == "uno dos…"


def test_articulo_9_lirpf_conserva_el_texto_de_la_norma() -> None:
    articulo = cargar_norma(FUENTES, LIRPF).bloque("a9")
    assert articulo is not None
    texto = articulo.texto_completo

    assert (
        articulo.epigrafe
        == "Contribuyentes que tienen su residencia habitual en territorio español"
    )
    assert "permanezca más de 183 días, durante el año natural, en territorio español" in texto
    assert "se computarán las ausencias esporádicas" in texto
    assert "el núcleo principal o la base de sus actividades o intereses económicos" in texto
    assert "Se presumirá, salvo prueba en contrario" in texto


def test_el_articulo_9_lirpf_nunca_se_ha_modificado() -> None:
    """Si algún día se toca, este test avisa: cambia la lectura de todo el corpus."""
    articulo = cargar_norma(FUENTES, LIRPF).bloque("a9")
    assert articulo is not None
    assert [v.fecha_vigencia for v in articulo.versiones] == ["20070101"]


def test_las_redacciones_sucesivas_llegan_en_orden_cronologico() -> None:
    articulo = cargar_norma(FUENTES, "BOE-A-2003-23186").bloque("a106")
    assert articulo is not None
    fechas = [v.fecha_vigencia for v in articulo.versiones]
    assert all(fecha is not None for fecha in fechas)
    assert fechas == sorted(fecha for fecha in fechas if fecha is not None)
    assert articulo.version_vigente is articulo.versiones[-1]


def test_las_notas_del_boe_no_contaminan_el_articulado() -> None:
    """Las notas editoriales («Se modifica por…») no son texto legal."""
    articulo = cargar_norma(FUENTES, "BOE-A-2003-23186").bloque("a108")
    assert articulo is not None
    assert any(v.notas_boe for v in articulo.versiones)
    for version in articulo.versiones:
        for parrafo in version.parrafos:
            assert not parrafo.startswith("Se modifica")
            assert not parrafo.startswith("Redactado conforme")


def test_el_xml_del_diario_segmenta_los_articulos_de_una_norma_derogada() -> None:
    norma = cargar_norma_diario(FUENTES, TRLIRPF_2004)
    assert norma.vigencia_agotada is True

    articulo = norma.bloque("a9")
    assert articulo is not None
    assert articulo.epigrafe == "Residencia habitual en territorio español"
    assert "Miembros de misiones diplomáticas españolas" in articulo.texto_completo

    siguiente = norma.bloque("a10")
    assert siguiente is not None
    assert "Miembros de misiones diplomáticas españolas" not in siguiente.texto_completo


# --- Detección del artículo de residencia de los CDI -------------------------


def test_el_cdi_con_rubrica_atipica_se_detecta_por_su_contenido() -> None:
    """El CDI con Suiza titula el precepto «Domicilio fiscal», no «Residente»."""
    norma = cargar_norma(FUENTES, CDI_SUIZA)
    articulo = localizar_precepto_residencia(norma)
    assert articulo is not None
    assert articulo.bloque_id == "a4"
    assert articulo.epigrafe == "Domicilio fiscal"
    assert "centro de intereses vitales" in articulo.texto_completo


def test_todos_los_convenios_generales_tienen_su_articulo_de_residencia(manifiesto: dict) -> None:
    sin_resolver = []
    for registro in manifiesto["normas"]:
        if registro["grupo"] != "cdi" or registro["id"] in SIN_PRECEPTO_RESIDENCIA:
            continue
        norma = cargar_norma(FUENTES, str(registro["id"]))
        if localizar_precepto_residencia(norma) is None:
            sin_resolver.append(registro["id"])
    assert sin_resolver == []


# --- Corpus generado ---------------------------------------------------------


def test_el_corpus_generado_esta_al_dia(manifiesto: dict) -> None:
    """`make export-normativa` no debe dejar el repositorio con cambios."""
    seleccionados, incidencias = seleccionar(FUENTES, manifiesto)
    assert [i for i in incidencias if not i["esperado"]] == []

    generados = {fichero.name for fichero in PRECEPTOS.glob("*.md")} - {"index.md"}
    assert len(generados) == len(seleccionados)

    for seleccion in seleccionados:
        if seleccion.norma.boe_id != LIRPF or seleccion.bloque.bloque_id != "a9":
            continue
        assert (PRECEPTOS / "lirpf-a9.md").read_text(encoding="utf-8") == renderizar(seleccion)


def test_cada_precepto_publicado_es_subcadena_literal_del_xml_de_origen() -> None:
    """El invariante jurídico: el articulado no se reescribe en ningún punto."""
    for fichero in sorted(PRECEPTOS.glob("*.md")):
        if fichero.name == "index.md":
            continue
        contenido = fichero.read_text(encoding="utf-8")
        origen = re.search(r"^resource: \.\./\.\./\.\./normativa/(.+)$", contenido, re.M)
        assert origen is not None, fichero.name

        xml = ET.parse(FUENTES / origen.group(1)).getroot()
        parrafos_fuente = {normalizar_espacios("".join(p.itertext())) for p in xml.iter("p")}

        cuerpo = contenido.split("# Texto vigente", 1)[1].split("# Notas del BOE", 1)[0]
        publicados = [
            linea.strip()
            for linea in cuerpo.splitlines()
            if linea.strip() and not linea.startswith(("#", ">", "_"))
        ]
        assert publicados, fichero.name
        for parrafo in publicados:
            assert parrafo in parrafos_fuente, f"{fichero.name}: {parrafo[:80]}"


def test_el_nucleo_estatal_cubre_los_preceptos_que_deciden_la_residencia() -> None:
    esperados = {
        "lirpf-a9.md",  # residencia habitual en España
        "lirpf-a10.md",  # residencia habitual en el extranjero
        "lgt-a105.md",  # carga de la prueba
        "lgt-a108.md",  # presunciones
        "trlirnr-a6.md",  # residencia a efectos del IRNR
        "rirpf-a120.md",  # certificado de residencia fiscal
        "trlirpf-2004-a9.md",  # ejercicios 2005-2006 del corpus
    }
    publicados = {fichero.name for fichero in PRECEPTOS.glob("*.md")}
    assert esperados <= publicados


def test_la_seleccion_estatal_solo_apunta_a_bloques_existentes() -> None:
    for boe_id, bloques in SELECCION_ESTATAL.items():
        norma = (
            cargar_norma_diario(FUENTES, boe_id)
            if boe_id == TRLIRPF_2004
            else cargar_norma(FUENTES, boe_id)
        )
        for bloque_id in bloques:
            assert norma.bloque(bloque_id) is not None, f"{boe_id}#{bloque_id}"
