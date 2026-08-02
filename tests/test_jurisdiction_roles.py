"""El papel de cada jurisdicción en una sentencia se deriva, no se adivina.

`TASKS.md` ya midió el caso que obliga a separar esto de la normalización: 31 de
las 106 sentencias son la saga de becarios del ICEX, donde el país que aparece
en el texto es el destino de la beca y no la jurisdicción cuya residencia se
discute. Contar esas menciones como «sentencias sobre X» publicaría una cifra
falsa.

Por eso el rol sale de campos tipados del caso —la determinación residencial, el
análisis de convenio, los periodos de presencia— y nunca de que un alias
aparezca en `judgment.countries`. Lo que solo está ahí se queda en
`mentioned_only`, que no autoriza ningún enlace público.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from jurisdiction_roles import (
    ROLES_TIPADOS,
    Rol,
    derivar_roles,
    render_jurisdiction_roles_json_schema,
)

PROJECT_ROOT = Path(__file__).parents[1]
CASOS = PROJECT_ROOT / "knowledge" / "jurisprudencia-v3" / "cases"
SIDECARS = PROJECT_ROOT / "knowledge" / "jurisprudencia-v3" / "jurisdicciones"
SCHEMA = PROJECT_ROOT / "schemas" / "residenciafiscal-jurisdiction-roles-v1.schema.json"


def cargar_caso(judgment_id: str) -> dict:
    return json.loads((CASOS / f"{judgment_id}.case.json").read_text(encoding="utf-8"))


def roles_de(sidecar, code: str) -> set[Rol]:
    for entrada in sidecar.jurisdictions:
        if entrada.code == code:
            return set(entrada.roles)
    return set()


def test_el_json_schema_versionado_esta_sincronizado() -> None:
    assert SCHEMA.read_text(encoding="utf-8") == render_jurisdiction_roles_json_schema()


def test_treaty_applied_sale_del_analisis_de_convenio() -> None:
    """El caso francés tiene `treaty_analyses`; el rol sale de ahí, no del alias."""
    sidecar = derivar_roles(cargar_caso("san-1071-2025"))

    assert Rol.TREATY_APPLIED in roles_de(sidecar, "fr")
    assert Rol.TREATY_APPLIED in roles_de(sidecar, "es")


def test_residence_claimed_sale_de_la_determinacion_residencial() -> None:
    """En SAN 1386/2017 el tribunal declara la residencia suiza desde abril."""
    sidecar = derivar_roles(cargar_caso("san-1386-2017"))

    assert Rol.RESIDENCE_CLAIMED in roles_de(sidecar, "ch")
    assert Rol.RESIDENCE_CLAIMED in roles_de(sidecar, "es")


def test_evidence_location_sale_de_los_periodos_de_presencia() -> None:
    sidecar = derivar_roles(cargar_caso("san-1386-2017"))

    assert Rol.EVIDENCE_LOCATION in roles_de(sidecar, "ch")


def test_un_codigo_solo_presente_en_countries_se_queda_en_mentioned_only() -> None:
    """El residual no autoriza a decir «sentencias sobre esa jurisdicción»."""
    caso = cargar_caso("san-1071-2025")
    caso["judgment"] = {**caso["judgment"], "countries": [*caso["judgment"]["countries"], "Kenia"]}

    sidecar = derivar_roles(caso)

    assert roles_de(sidecar, "ke") == {Rol.MENTIONED_ONLY}


def test_el_residual_no_se_mezcla_con_un_rol_tipado() -> None:
    """`mentioned_only` describe la ausencia de papel, no se suma a uno."""
    sidecar = derivar_roles(cargar_caso("san-1071-2025"))

    for entrada in sidecar.jurisdictions:
        if Rol.MENTIONED_ONLY in entrada.roles:
            assert set(entrada.roles) == {Rol.MENTIONED_ONLY}, entrada.code


def test_todo_rol_declara_de_que_campo_sale() -> None:
    """Gate A: ningún rol jurídico se infiere solo por alias."""
    for ruta in sorted(CASOS.glob("*.case.json")):
        sidecar = derivar_roles(json.loads(ruta.read_text(encoding="utf-8")))
        for entrada in sidecar.jurisdictions:
            assert entrada.derived_from, f"{sidecar.judgment_id}/{entrada.code}"
            for rol in entrada.roles:
                if rol in ROLES_TIPADOS:
                    assert any(
                        not origen.startswith("judgment.countries")
                        for origen in entrada.derived_from
                    ), f"{sidecar.judgment_id}/{entrada.code}: {rol} solo tiene origen en countries"


def test_una_jurisdiccion_emisora_ambigua_no_produce_rol_tipado() -> None:
    """Varios `foreign_document.jurisdiction` traen copiado el campo de países.

    «Israel;Brasil» o el título de un convenio no son la autoridad que emitió el
    documento; tratarlos como el lugar de una prueba inventaría un papel.
    """
    caso = cargar_caso("san-1071-2025")
    evidencias = list(caso["evidence_findings"])
    evidencias[0] = {
        **evidencias[0],
        "foreign_document": {
            "defects": [],
            "document_type": "OTHER",
            "issuing_authority": "Autoridad",
            "jurisdiction": "Israel;Brasil",
            "nature": "TAX",
            "period_end": None,
            "period_start": None,
            "probative_effect": "Indicio",
            "tax_scope": "WORLDWIDE_INCOME",
        },
    }
    caso["evidence_findings"] = evidencias

    sidecar = derivar_roles(caso)

    assert roles_de(sidecar, "il") == set()
    assert roles_de(sidecar, "br") == set()


def test_los_sidecars_versionados_estan_al_dia() -> None:
    """Regenerar dos veces produce el mismo fichero (Gate A)."""
    from jurisdiction_roles import render_sidecar

    rutas = sorted(CASOS.glob("*.case.json"))
    assert len(rutas) == 106
    for ruta in rutas:
        caso = json.loads(ruta.read_text(encoding="utf-8"))
        judgment_id = caso["judgment"]["judgment_id"]
        destino = SIDECARS / f"{judgment_id}.roles.json"
        assert destino.exists(), f"falta el sidecar de {judgment_id}"
        assert destino.read_text(encoding="utf-8") == render_sidecar(caso)


def test_el_sidecar_se_ata_a_la_fuente_por_su_hash() -> None:
    caso = cargar_caso("san-1071-2025")
    sidecar = derivar_roles(caso)

    assert sidecar.source_sha256 == caso["judgment"]["source_sha256"]


def test_espana_aparece_en_todas_las_sentencias_con_algun_rol() -> None:
    for ruta in sorted(CASOS.glob("*.case.json")):
        sidecar = derivar_roles(json.loads(ruta.read_text(encoding="utf-8")))
        assert roles_de(sidecar, "es"), sidecar.judgment_id


@pytest.mark.parametrize("judgment_id", ["san-1071-2025", "san-1386-2017"])
def test_las_entradas_salen_ordenadas_por_codigo(judgment_id: str) -> None:
    sidecar = derivar_roles(cargar_caso(judgment_id))

    codigos = [entrada.code for entrada in sidecar.jurisdictions]
    assert codigos == sorted(codigos)
