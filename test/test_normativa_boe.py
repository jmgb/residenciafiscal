"""Tests del parseo del XML del BOE y del corpus de preceptos generado.

Los ficheros de `normativa/` están versionados igual que los PDF de
`sentencias/`, así que estos tests trabajan contra la fuente real: no hay red ni
LLM, y una regresión en el parser se detecta sobre el texto legal de verdad.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from export_normativa import (
    ENCABEZADO_DEROGADO,
    ENCABEZADO_NOTAS,
    ENCABEZADO_VIGENTE,
    GRUPOS_DEROGADOS,
    SELECCION_ESTATAL,
    SIN_PRECEPTO_RESIDENCIA,
    localizar_precepto_residencia,
    recortar,
    renderizar,
    renderizar_indice,
    seleccionar,
    slug_precepto,
)
from normativa_boe import (
    cargar_norma,
    cargar_norma_diario,
    formatear_fecha,
    normalizar_espacios,
    parsear_norma_diario,
)

RAIZ = Path(__file__).parents[1]
JURISDICCION = "es"
FUENTES = RAIZ / "normativa" / JURISDICCION
PRECEPTOS = RAIZ / "knowledge" / "normativa" / JURISDICCION / "preceptos"

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


def _frontmatter_publicado(contenido: str) -> dict:
    return dict(yaml.safe_load(contenido.split("---", 2)[1]))


def _articulado_publicado(contenido: str) -> list[str]:
    """Párrafos que el fichero presenta como texto de la norma.

    Abarca «Texto vigente» y «Redacciones anteriores», que es todo lo que va
    hasta las notas del BOE. Descarta encabezados, avisos y los textos de
    ausencia en cursiva, que no son articulado.
    """
    encabezado = ENCABEZADO_DEROGADO if ENCABEZADO_DEROGADO in contenido else ENCABEZADO_VIGENTE
    cuerpo = contenido.split(encabezado, 1)[1].split(ENCABEZADO_NOTAS, 1)[0]
    return [
        linea.strip()
        for linea in cuerpo.splitlines()
        if linea.strip() and not linea.startswith(("#", ">", "_"))
    ]


def test_el_corpus_generado_esta_al_dia(manifiesto: dict) -> None:
    """`make export-normativa` no debe dejar el repositorio con cambios.

    Se comparan **todos** los ficheros, no una muestra: comprobar solo
    `lirpf-a9.md` dejaba sin gate el renderizado de los 93 convenios.
    """
    seleccionados, incidencias = seleccionar(FUENTES, manifiesto)
    assert [i for i in incidencias if not i["esperado"]] == []

    esperados = {
        f"{slug_precepto(s.norma.boe_id, s.grupo, s.bloque.bloque_id)}.md": renderizar(s)
        for s in seleccionados
    }
    assert len(esperados) == len(seleccionados), "hay slugs de precepto duplicados"

    publicados = {f.name for f in PRECEPTOS.glob("*.md")} - {"index.md"}
    assert publicados == set(esperados)

    for nombre, contenido in sorted(esperados.items()):
        assert (PRECEPTOS / nombre).read_text(encoding="utf-8") == contenido, nombre

    assert (PRECEPTOS / "index.md").read_text(encoding="utf-8") == renderizar_indice(seleccionados)


def test_cada_precepto_publicado_es_subcadena_literal_del_xml_de_origen() -> None:
    """El invariante jurídico: el articulado no se reescribe en ningún punto.

    Se contrasta contra los párrafos **de ese bloque**, no contra todos los del
    fichero XML: comparar contra la norma entera daba por bueno cualquier texto
    del BOE, aunque perteneciera a otro artículo.
    """
    for fichero in sorted(PRECEPTOS.glob("*.md")):
        if fichero.name == "index.md":
            continue
        contenido = fichero.read_text(encoding="utf-8")
        frontmatter = _frontmatter_publicado(contenido)
        boe_id = frontmatter["boe_id"]

        norma = (
            cargar_norma_diario(FUENTES, boe_id)
            if str(frontmatter["grupo"]) in GRUPOS_DEROGADOS
            else cargar_norma(FUENTES, boe_id)
        )
        bloque = norma.bloque(str(frontmatter["bloque_id"]))
        assert bloque is not None, fichero.name

        del_bloque = {parrafo for version in bloque.versiones for parrafo in version.parrafos}

        publicados = _articulado_publicado(contenido)
        assert publicados, fichero.name
        for parrafo in publicados:
            assert parrafo in del_bloque, f"{fichero.name}: {parrafo[:80]}"


def test_las_notas_editoriales_del_boe_no_se_publican_como_articulado() -> None:
    """Una nota del BOE no puede presentarse como texto de la norma.

    El test anterior lo cubre por construcción, pero esta es la afirmación que
    de verdad importa y merece fallar por su propio nombre.
    """
    comprobados = 0
    for fichero in sorted(PRECEPTOS.glob("*.md")):
        if fichero.name == "index.md":
            continue
        contenido = fichero.read_text(encoding="utf-8")
        frontmatter = _frontmatter_publicado(contenido)
        norma = (
            cargar_norma_diario(FUENTES, str(frontmatter["boe_id"]))
            if str(frontmatter["grupo"]) in GRUPOS_DEROGADOS
            else cargar_norma(FUENTES, str(frontmatter["boe_id"]))
        )
        bloque = norma.bloque(str(frontmatter["bloque_id"]))
        assert bloque is not None, fichero.name

        notas = {nota for version in bloque.versiones for nota in version.notas_boe}
        if not notas:
            continue
        comprobados += 1
        for parrafo in _articulado_publicado(contenido):
            assert parrafo not in notas, f"{fichero.name}: nota publicada como articulado"

    assert comprobados, "ningún precepto publicado tiene notas del BOE: el test no prueba nada"


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


# --- Normas derogadas y jurisdicción -----------------------------------------


def test_el_diario_sin_marcas_de_articulo_se_segmenta_por_la_rubrica() -> None:
    """El CDI con Argentina de 1992 está entero en `class="parrafo"`.

    Sin el fallback por forma de la rúbrica devolvía cero bloques, y el convenio
    que aplican las sentencias de ejercicios antiguos quedaba sin publicar.
    """
    norma = cargar_norma_diario(FUENTES, "BOE-A-1994-20084")
    assert len(norma.bloques) > 20

    articulo = localizar_precepto_residencia(norma)
    assert articulo is not None
    assert articulo.bloque_id == "a4"
    assert articulo.epigrafe == "Residencia"
    assert "vivienda permanente" in articulo.texto_completo


def test_un_diario_que_no_delimita_preceptos_falla_en_vez_de_quedar_vacio() -> None:
    """Devolver una norma sin bloques haría que el precepto se omitiera en silencio."""
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <documento fecha_actualizacion="20260101000000">
      <metadatos><identificador>BOE-A-0000-1</identificador><titulo>Prueba</titulo></metadatos>
      <texto><p class="parrafo">Texto sin ninguna rubrica de articulo.</p></texto>
    </documento>"""
    with pytest.raises(ValueError, match="no se ha delimitado ningún precepto"):
        parsear_norma_diario(xml)


def test_los_convenios_sustituidos_se_publican_marcados_como_derogados() -> None:
    """Un convenio sustituido no puede presentarse como derecho vigente."""
    for nombre, esperado in (
        ("cdi-boe-a-1994-20084-a4.md", "Argentina"),
        ("cdi-boe-a-1976-23347-a4.md", "Reino Unido"),
    ):
        contenido = (PRECEPTOS / nombre).read_text(encoding="utf-8")
        frontmatter = _frontmatter_publicado(contenido)

        assert frontmatter["derogada"] is True
        assert frontmatter["grupo"] == "cdi_derogado"
        assert "derogada" in frontmatter["tags"]
        assert esperado in str(frontmatter["nota_derogacion"])
        assert ENCABEZADO_DEROGADO in contenido
        assert ENCABEZADO_VIGENTE not in contenido
        assert "**Norma derogada.**" in contenido


def test_ningun_precepto_vigente_se_rotula_como_derogado() -> None:
    vigentes = derogados = 0
    for fichero in PRECEPTOS.glob("*.md"):
        if fichero.name == "index.md":
            continue
        contenido = fichero.read_text(encoding="utf-8")
        if _frontmatter_publicado(contenido)["derogada"]:
            derogados += 1
            assert ENCABEZADO_DEROGADO in contenido, fichero.name
        else:
            vigentes += 1
            assert ENCABEZADO_VIGENTE in contenido, fichero.name
    assert derogados == 4  # TR IRPF 2004 (arts. 8 y 9) y los dos CDI sustituidos
    assert vigentes > 100


def test_cada_precepto_declara_su_jurisdiccion_y_apunta_a_su_fuente() -> None:
    """El código de jurisdicción es la clave que permite un segundo país."""
    for fichero in sorted(PRECEPTOS.glob("*.md")):
        if fichero.name == "index.md":
            continue
        contenido = fichero.read_text(encoding="utf-8")
        frontmatter = _frontmatter_publicado(contenido)
        assert frontmatter["jurisdiccion"] == JURISDICCION, fichero.name

        origen = (fichero.parent / str(frontmatter["resource"])).resolve()
        assert origen.exists(), f"{fichero.name} -> {frontmatter['resource']}"
        assert origen.parent.name == JURISDICCION
