"""Tests del enlace entre el corpus de sentencias y el corpus normativo.

Lo que se prueba no es que el resolvedor encuentre muchas citas, sino que **no
enlace lo que no debe**: un enlace equivocado manda a un abogado al artículo de
otro Estado o de otra época, y eso es peor que no enlazar nada.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from normativa_citas import (
    CERTEZA_EXPLICITA,
    CERTEZA_INFERIDA,
    CONVENIOS_POR_PAIS,
    MOTIVO_ARTICULO_NO_PUBLICADO,
    MOTIVO_SIN_PAIS_CDI,
    ConvenioPais,
    buscar_precepto,
    cargar_preceptos,
    enlazar_registro,
    extraer_citas,
    extraer_ejercicios,
    numero_de_designacion,
    paises_citados,
    resolver_cita,
)

RAIZ = Path(__file__).parents[1]
PRECEPTOS = RAIZ / "knowledge" / "normativa" / "es" / "preceptos"
ENLACES = RAIZ / "knowledge" / "normativa" / "es" / "enlaces"

CDI_FRANCIA = "BOE-A-1997-12729"
CDI_REINO_UNIDO_1975 = "BOE-A-1976-23347"
CDI_REINO_UNIDO_2013 = "BOE-A-2014-5171"
# Suecia, Rumanía y Canadá designan su artículo de residencia «Artículo IV».
# Canadá es el único de los tres que está en la tabla de países del corpus.
CDI_CANADA = "BOE-A-1981-2731"
TRLIRPF_2004 = "BOE-A-2004-4347"
LIRPF_2006 = "BOE-A-2006-20764"


@pytest.fixture(scope="module")
def catalogo() -> dict:
    return cargar_preceptos(PRECEPTOS)


# --- Extracción --------------------------------------------------------------


def test_extrae_las_formas_de_cita_que_usa_el_corpus() -> None:
    texto = (
        "Aplica el art.9 LIRPF y el artículo 105.1 LGT, con el art. 4.2 CDI "
        "para el desempate y el art. 95 bis LIRPF por el cambio de residencia."
    )
    citas = {(c.numero, c.sufijo, c.apartado, c.sigla) for c in extraer_citas(texto, "campo")}

    assert ("9", None, "", "lirpf") in citas
    assert ("105", None, ".1", "lgt") in citas
    assert ("4", None, ".2", "cdi") in citas
    assert ("95", "bis", "", "lirpf") in citas


def test_los_ejercicios_se_leen_del_texto_libre_del_analisis() -> None:
    assert extraer_ejercicios("2010 y 2011") == [2010, 2011]
    assert extraer_ejercicios("ejercicios 2014-2016") == [2014, 2016]
    assert extraer_ejercicios("NO CONSTA") == []
    assert extraer_ejercicios(None) == []


def test_el_pais_del_convenio_se_reconoce_dentro_del_texto_libre() -> None:
    assert paises_citados("España - Emiratos Árabes Unidos") == ["emiratos arabes unidos"]
    assert paises_citados("Méjico") == ["mejico"]
    assert paises_citados("NO CONSTA") == []
    assert set(paises_citados("Marruecos; Estados Unidos")) == {"marruecos", "estados unidos"}


def test_los_alias_del_mismo_pais_no_duplican_convenio() -> None:
    """«Países Bajos (Holanda)» aparece así en el corpus y es un solo convenio."""
    assert len(paises_citados("Países Bajos (Holanda)")) == 1


# --- Emparejamiento con el precepto ------------------------------------------


def test_el_numero_de_articulo_se_lee_de_la_designacion() -> None:
    assert numero_de_designacion("Artículo 4") == "4"
    assert numero_de_designacion("Artículo 95 bis") == "95bis"
    assert numero_de_designacion("Disposición transitoria única") is None


def test_el_numero_de_articulo_admite_numeracion_romana() -> None:
    """Tres convenios titulan su artículo de residencia «Artículo IV».

    Las sentencias lo citan en árabe («art. 4 CDI»), así que sin convertir la
    designación el enlace se perdía en silencio: el precepto existe publicado,
    pero ningún número lo alcanzaba.
    """
    assert numero_de_designacion("Artículo IV") == "4"
    assert numero_de_designacion("Artículo XXIV") == "24"
    assert numero_de_designacion("Artículo IV bis") == "4bis"


def test_una_designacion_que_no_es_un_articulo_no_inventa_numero() -> None:
    """Convertir de más es peor que no convertir: mandaría a otro artículo."""
    assert numero_de_designacion("Artículo IIII") is None  # romano mal formado
    assert numero_de_designacion("Disposición transitoria única") is None
    assert numero_de_designacion("Artículo Duodécimo") is None  # empieza por «D»


def test_la_cita_arabiga_alcanza_el_convenio_que_usa_romanos(catalogo: dict) -> None:
    (cita,) = extraer_citas("el art. 4 CDI atribuye la residencia", "campo")
    enlaces, motivo = resolver_cita(cita, catalogo, [2015], list(CONVENIOS_POR_PAIS["canada"]))

    assert motivo is None
    assert [e.boe_id for e in enlaces] == [CDI_CANADA]
    precepto = buscar_precepto(catalogo, CDI_CANADA, "4")
    assert precepto is not None and precepto.designacion == "Artículo IV"


def test_los_identificadores_de_bloque_del_boe_no_son_uniformes(catalogo: dict) -> None:
    """Por esto el emparejamiento va por número de artículo y no por `a{N}`.

    El convenio con Francia publica su artículo 4 como `a4` y el del Reino Unido
    de 2013 como `ar-4`. Construir el identificador desde el número perdía
    enlaces en silencio.
    """
    francia = buscar_precepto(catalogo, CDI_FRANCIA, "4")
    reino_unido = buscar_precepto(catalogo, CDI_REINO_UNIDO_2013, "4")

    assert francia is not None and reino_unido is not None
    assert francia.bloque_id != reino_unido.bloque_id
    assert {francia.bloque_id, reino_unido.bloque_id} == {"a4", "ar-4"}


# --- Resolución --------------------------------------------------------------


def test_una_cita_con_sigla_se_resuelve_como_explicita(catalogo: dict) -> None:
    (cita,) = extraer_citas("conforme al art.9 LIRPF", "campo")
    enlaces, motivo = resolver_cita(cita, catalogo, [2015], [])

    assert motivo is None
    assert [e.slug for e in enlaces] == ["lirpf-a9"]
    assert enlaces[0].certeza == CERTEZA_EXPLICITA


def test_una_cita_sin_sigla_se_resuelve_pero_se_marca_inferida(catalogo: dict) -> None:
    (cita,) = extraer_citas("el art. 9.1.b) exige acreditar", "campo")
    enlaces, _ = resolver_cita(cita, catalogo, [2015], [])

    assert [e.slug for e in enlaces] == ["lirpf-a9"]
    assert enlaces[0].certeza == CERTEZA_INFERIDA
    assert enlaces[0].apartado == "1.b)"


def test_una_cita_sin_sigla_de_un_ejercicio_anterior_a_2007_va_al_texto_refundido(
    catalogo: dict,
) -> None:
    """La Ley 35/2006 no regía en 2005: enlazarla sería un anacronismo."""
    (cita,) = extraer_citas("el art. 9 determina la residencia", "campo")
    enlaces, _ = resolver_cita(cita, catalogo, [2005, 2006], [])

    assert [e.slug for e in enlaces] == ["trlirpf-2004-a9"]


def test_una_sentencia_a_caballo_de_2007_enlaza_las_dos_normas(catalogo: dict) -> None:
    """Un caso puede abarcar ejercicios a ambos lados de la Ley 35/2006.

    Elegir una sola norma por el ejercicio más alto dejaba los anteriores sin la
    norma que de verdad los regía: para 2005 y 2007, «art. 9.1» enlazaba solo a
    la LIRPF y 2005 se quedaba sin precepto aplicable.
    """
    (cita,) = extraer_citas("el art. 9 determina la residencia", "campo")
    enlaces, _ = resolver_cita(cita, catalogo, [2005, 2007], [])

    assert {e.boe_id for e in enlaces} == {TRLIRPF_2004, LIRPF_2006}


def test_cada_norma_declara_solo_los_ejercicios_que_rige(catalogo: dict) -> None:
    """La redacción aplicable se acota al periodo de cada norma.

    Sin acotarla, el texto refundido de 2004 aparecía con una redacción para
    2007, cuando ya estaba derogado.
    """
    (cita,) = extraer_citas("el art. 9 determina la residencia", "campo")
    enlaces, _ = resolver_cita(cita, catalogo, [2005, 2007], [])
    por_norma = {e.boe_id: sorted(e.redaccion_aplicable) for e in enlaces}

    assert por_norma[TRLIRPF_2004] == ["2005"]
    assert por_norma[LIRPF_2006] == ["2007"]


def test_una_sentencia_que_cruza_el_cambio_de_convenio_enlaza_ambos(catalogo: dict) -> None:
    """Mismo problema que con la norma interna: el convenio también cambia.

    El de Reino Unido rige hasta 2013 y el nuevo desde 2014, así que un caso de
    2013 y 2014 aplica los dos.
    """
    (cita,) = extraer_citas("el art. 4.2 CDI resuelve la doble residencia", "campo")
    convenios = list(CONVENIOS_POR_PAIS["reino unido"])

    enlaces, _ = resolver_cita(cita, catalogo, [2013, 2014], convenios)

    assert {e.boe_id for e in enlaces} == {CDI_REINO_UNIDO_1975, CDI_REINO_UNIDO_2013}


def test_el_convenio_se_elige_por_el_ejercicio_enjuiciado(catalogo: dict) -> None:
    """Reino Unido tiene convenio de 1975 y de 2013: el ejercicio decide."""
    (cita,) = extraer_citas("el art. 4.2 CDI resuelve la doble residencia", "campo")
    convenios = list(CONVENIOS_POR_PAIS["reino unido"])

    antiguo, _ = resolver_cita(cita, catalogo, [2010], convenios)
    moderno, _ = resolver_cita(cita, catalogo, [2016], convenios)

    assert [e.boe_id for e in antiguo] == [CDI_REINO_UNIDO_1975]
    assert [e.boe_id for e in moderno] == [CDI_REINO_UNIDO_2013]


def test_una_cita_de_convenio_sin_pais_declarado_no_se_resuelve(catalogo: dict) -> None:
    """Sin país no hay convenio: adivinarlo enlazaría al derecho de otro Estado."""
    (cita,) = extraer_citas("aplica el art. 4.2 CDI", "campo")
    enlaces, motivo = resolver_cita(cita, catalogo, [2015], [])

    assert enlaces == []
    assert motivo == MOTIVO_SIN_PAIS_CDI


def test_un_articulo_de_convenio_que_no_se_publica_no_se_resuelve(catalogo: dict) -> None:
    """De cada convenio solo se publica su artículo de residencia."""
    (cita,) = extraer_citas("el art. 19 CDI grava las pensiones", "campo")
    enlaces, motivo = resolver_cita(cita, catalogo, [2015], [ConvenioPais(CDI_FRANCIA)])

    assert enlaces == []
    assert motivo == MOTIVO_ARTICULO_NO_PUBLICADO


def test_nunca_se_enlaza_a_un_precepto_que_no_existe(catalogo: dict) -> None:
    """El art. 13 TRLIRNR se cita en el corpus y no está en la selección."""
    (cita,) = extraer_citas("el art.13 TRLIRNR califica la renta", "campo")
    enlaces, motivo = resolver_cita(cita, catalogo, [2014], [])

    assert enlaces == []
    assert motivo is not None


def test_la_redaccion_aplicable_es_la_del_ejercicio_no_la_de_hoy(catalogo: dict) -> None:
    """El art. 108 LGT tiene redacción de 2004 y de 2015."""
    (cita,) = extraer_citas("el artículo 108 LGT establece la presunción", "campo")
    enlaces, _ = resolver_cita(cita, catalogo, [2010, 2016], [])

    (enlace,) = enlaces
    assert enlace.redaccion_aplicable["2010"] == "2004-07-01"
    assert enlace.redaccion_aplicable["2016"] == "2015-10-12"


def test_el_anacronismo_se_avisa_y_no_se_corrige(catalogo: dict) -> None:
    """Citar la Ley 35/2006 en un caso de 2005 es un dato del análisis, no nuestro."""
    registro = {
        "archivo": "PRUEBA.pdf",
        "ejercicios_afectados": "2005 y 2006",
        "resumen_criterios": "aplica el art. 9 LIRPF",
    }
    resultado = enlazar_registro(registro, catalogo)

    assert resultado["avisos"]
    assert "no se corrige aquí" in resultado["avisos"][0]
    assert [p["slug"] for p in resultado["preceptos"]] == ["lirpf-a9"]


# --- Artefacto publicado -----------------------------------------------------


def test_el_artefacto_de_enlaces_esta_al_dia_y_es_coherente(catalogo: dict) -> None:
    enlaces = json.loads((ENLACES / "jurisprudencia.json").read_text(encoding="utf-8"))
    slugs = {p.slug for lista in catalogo.values() for p in lista}

    assert enlaces["jurisdiccion"] == "es"
    assert enlaces["sentencias"] == len(enlaces["sentencias_detalle"])
    assert enlaces["enlaces"] == sum(len(s["preceptos"]) for s in enlaces["sentencias_detalle"])

    for sentencia in enlaces["sentencias_detalle"]:
        for precepto in sentencia["preceptos"]:
            assert precepto["slug"] in slugs, precepto["slug"]
            assert (PRECEPTOS / f"{precepto['slug']}.md").exists()
            assert precepto["certeza"] in {CERTEZA_EXPLICITA, CERTEZA_INFERIDA}


def test_el_indice_inverso_coincide_con_el_directo() -> None:
    directo = json.loads((ENLACES / "jurisprudencia.json").read_text(encoding="utf-8"))
    inverso = json.loads((ENLACES / "por_precepto.json").read_text(encoding="utf-8"))

    esperado: dict[str, set[str]] = {}
    for sentencia in directo["sentencias_detalle"]:
        for precepto in sentencia["preceptos"]:
            esperado.setdefault(precepto["slug"], set()).add(sentencia["archivo"])

    obtenido = {p["slug"]: {c["archivo"] for c in p["sentencias"]} for p in inverso["preceptos"]}
    assert obtenido == esperado
    for precepto in inverso["preceptos"]:
        assert precepto["total_sentencias"] == len({c["archivo"] for c in precepto["sentencias"]})


def test_el_articulo_9_lirpf_es_el_precepto_mas_citado() -> None:
    """Si deja de serlo, o el corpus cambió de objeto o el resolvedor se rompió."""
    inverso = json.loads((ENLACES / "por_precepto.json").read_text(encoding="utf-8"))
    mas_citado = max(inverso["preceptos"], key=lambda p: p["total_sentencias"])

    assert mas_citado["slug"] == "lirpf-a9"
    assert mas_citado["total_sentencias"] > 40
