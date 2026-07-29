"""Unidades de recuperación por cuestión derivadas del caso v3."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CASE_PATH = PROJECT_ROOT / "knowledge/jurisprudencia/cases/san-1210-2023.case.json"


def _case():
    from jurisprudence_case_artifact import load_jurisprudence_case

    return load_jurisprudence_case(CASE_PATH.read_bytes())


def test_construye_una_unidad_autosuficiente_por_cuestion() -> None:
    from jurisprudence_case_retrieval import build_retrieval_index

    index = build_retrieval_index(
        _case(),
        case_resource="../cases/san-1210-2023.case.json",
        case_sha256="a" * 64,
    )

    assert index.schema_version == "residenciafiscal-retrieval/1"
    assert len(index.units) == 3
    residence, gains, penalty = index.units
    assert residence.issue.issue_id == "residencia-fiscal"
    assert {item.evidence_id for item in residence.evidence_findings} >= {
        "evidence-vigilancia-aduanera",
        "evidence-carte-resident",
    }
    assert [item.evidence_id for item in gains.evidence_findings] == [
        "evidence-liquidacion-importes"
    ]
    assert penalty.holding.issue_id == "sancion-tributaria"
    assert all(unit.source_anchors for unit in index.units)


def test_facetas_y_texto_de_busqueda_no_mezclan_otras_cuestiones() -> None:
    from jurisprudence_case_retrieval import build_retrieval_index

    index = build_retrieval_index(
        _case(),
        case_resource="../cases/san-1210-2023.case.json",
        case_sha256="a" * 64,
    )
    gains = index.units[1]

    assert gains.facets.issue_type == "UNEXPLAINED_CAPITAL_GAIN"
    assert gains.facets.outcome == "GANA_AEAT"
    assert gains.facets.countries == ("España", "Mónaco")
    assert "importes obtenidos cuyo origen no se había probado" in gains.search_text
    assert "cápsulas Nespresso" not in gains.search_text


def test_serializacion_del_indice_es_determinista_y_estricta() -> None:
    from jurisprudence_case_retrieval import (
        build_retrieval_index,
        load_retrieval_index,
        render_retrieval_index,
    )

    index = build_retrieval_index(
        _case(),
        case_resource="../cases/san-1210-2023.case.json",
        case_sha256="a" * 64,
    )
    first = render_retrieval_index(index)
    second = render_retrieval_index(index)

    assert first == second
    assert first.endswith("\n")
    assert load_retrieval_index(first) == index

    raw = json.loads(first)
    raw["units"][0]["unexpected"] = True
    with pytest.raises(ValidationError, match="unexpected"):
        load_retrieval_index(json.dumps(raw))
