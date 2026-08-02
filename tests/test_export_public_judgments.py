"""El manifiesto público es lo que decide qué puede llegar a la web.

`JURISPRUDENCE_PHASE_E0.md` separa dos gates: el técnico, que ya pasan los 106
casos, y el jurídico, que exige aprobación humana de todo lo que se publique. El
manifiesto es donde ese segundo gate se hace comprobable por máquina, y por eso
el estado no se escribe a mano: se calcula, y declarar un lote publicado con un
caso sin aprobar es un error de build, no un aviso.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from export_public_judgments import (
    LOTES_PUBLICADOS,
    cargar_casos,
    construir_manifiesto,
    render_manifiesto,
)
from public_judgment_projection import render_public_judgment

PROJECT_ROOT = Path(__file__).parents[1]
CASOS = PROJECT_ROOT / "knowledge" / "jurisprudencia-v3" / "cases"
PUBLICO = PROJECT_ROOT / "knowledge" / "jurisprudencia-v3" / "publico"


@pytest.fixture(scope="module")
def casos() -> list[dict]:
    return cargar_casos(CASOS)


@pytest.fixture(scope="module")
def manifiesto(casos: list[dict]) -> dict:
    return construir_manifiesto(casos)


def test_solo_entran_los_sesenta_y_siete_candidatos(manifiesto: dict) -> None:
    """D4: las 39 fuera de ámbito no son producto, su análisis no habla de residencia."""
    assert manifiesto["candidates"] == 67
    assert len(manifiesto["judgments"]) == 67


def test_hoy_ningun_caso_esta_publicado(manifiesto: dict) -> None:
    """La fase C2 está aplazada por falta de revisor: el gate no se rebaja."""
    assert manifiesto["published"] == 0
    assert LOTES_PUBLICADOS == {}
    estados = {entrada["publicationState"] for entrada in manifiesto["judgments"]}
    assert estados == {"internal_preview"}


def test_declarar_publicado_un_caso_sin_aprobar_rompe_el_build(casos: list[dict]) -> None:
    """Un lote no puede ascender lo que la revisión no ha aprobado."""
    import export_public_judgments

    original = dict(export_public_judgments.LOTES_PUBLICADOS)
    export_public_judgments.LOTES_PUBLICADOS["lote-inventado"] = ("san-1210-2023",)
    try:
        with pytest.raises(ValueError, match="no se salta"):
            construir_manifiesto(casos)
    finally:
        export_public_judgments.LOTES_PUBLICADOS.clear()
        export_public_judgments.LOTES_PUBLICADOS.update(original)


def test_un_lote_con_un_id_desconocido_rompe_el_build(casos: list[dict]) -> None:
    """Un typo editorial no puede quedar como una publicación que nunca ocurre."""
    import export_public_judgments

    original = dict(export_public_judgments.LOTES_PUBLICADOS)
    export_public_judgments.LOTES_PUBLICADOS["lote-inventado"] = ("sts-9999-2030",)
    try:
        with pytest.raises(ValueError, match="no es una candidata"):
            construir_manifiesto(casos)
    finally:
        export_public_judgments.LOTES_PUBLICADOS.clear()
        export_public_judgments.LOTES_PUBLICADOS.update(original)


def test_cada_entrada_lleva_el_hash_de_su_proyeccion(manifiesto: dict, casos: list[dict]) -> None:
    """Sin hash, el frontend no puede detectar una proyección cambiada."""
    import hashlib

    por_id = {caso["judgment"]["judgment_id"]: caso for caso in casos}
    for entrada in manifiesto["judgments"]:
        contenido = render_public_judgment(por_id[entrada["judgmentId"]])
        assert entrada["projectionSha256"] == hashlib.sha256(contenido.encode("utf-8")).hexdigest()
        assert len(entrada["sourceSha256"]) == 64


def test_el_manifiesto_declara_su_jurisdiccion(manifiesto: dict) -> None:
    assert manifiesto["jurisdiction"] == "es"


def test_el_manifiesto_trae_lo_que_el_indice_necesita_para_filtrar(manifiesto: dict) -> None:
    """El índice filtra en cliente: sin estos campos tendría que bajar 67 fichas."""
    for entrada in manifiesto["judgments"]:
        assert entrada["roj"]
        assert entrada["court"]
        assert entrada["decisionDate"]
        assert isinstance(entrada["criterionIds"], list)
        assert isinstance(entrada["outcomes"], list)


def test_los_artefactos_versionados_estan_al_dia(casos: list[dict]) -> None:
    """Regenerar dos veces da diff vacío."""
    assert (PUBLICO / "manifest.json").read_text(encoding="utf-8") == render_manifiesto(casos)

    por_id = {caso["judgment"]["judgment_id"]: caso for caso in casos}
    ficheros = sorted(PUBLICO.glob("*.public.json"))
    assert len(ficheros) == 67
    for fichero in ficheros:
        judgment_id = fichero.name.removesuffix(".public.json")
        assert fichero.read_text(encoding="utf-8") == render_public_judgment(por_id[judgment_id])


def test_ninguna_proyeccion_de_caso_fuera_de_ambito_se_escribe(casos: list[dict]) -> None:
    fuera = {
        caso["judgment"]["judgment_id"]
        for caso in casos
        if not caso["judgment"]["is_tax_residence_case"]
    }
    assert len(fuera) == 39
    for judgment_id in fuera:
        assert not (PUBLICO / f"{judgment_id}.public.json").exists()
