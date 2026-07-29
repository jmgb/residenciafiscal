"""Integridad referencial del agregado jurisprudencial v3."""

from copy import deepcopy

import pytest
from jurisprudence_case_v3_factory import valid_case
from pydantic import ValidationError


def test_rechaza_referencias_a_hechos_inexistentes() -> None:
    from jurisprudence_case_models import JurisprudenceCase

    raw = deepcopy(valid_case())
    raw["legal_issues"][0]["fact_ids"] = ["fact-inexistente"]

    with pytest.raises(ValidationError, match="fact-inexistente"):
        JurisprudenceCase.model_validate(raw)


@pytest.mark.parametrize(
    ("collection", "field", "missing_id", "scalar"),
    [
        ("legal_issues", "evidence_ids", "evidence-inexistente", False),
        ("legal_issues", "legal_rule_ids", "rule-inexistente", False),
        ("legal_issues", "holding_id", "holding-inexistente", True),
        ("legal_issues", "anchor_ids", "anchor-inexistente", False),
        ("facts", "issue_ids", "issue-inexistente", False),
        ("facts", "anchor_ids", "anchor-inexistente", False),
        ("evidence_findings", "fact_ids", "fact-inexistente", False),
        ("evidence_findings", "issue_ids", "issue-inexistente", False),
        ("evidence_findings", "anchor_ids", "anchor-inexistente", False),
        ("legal_rules", "issue_ids", "issue-inexistente", False),
        ("legal_rules", "anchor_ids", "anchor-inexistente", False),
        ("holdings", "issue_id", "issue-inexistente", True),
        ("holdings", "anchor_ids", "anchor-inexistente", False),
        ("burden_of_proof_steps", "issue_ids", "issue-inexistente", False),
        (
            "burden_of_proof_steps",
            "triggering_evidence_ids",
            "evidence-inexistente",
            False,
        ),
        ("burden_of_proof_steps", "anchor_ids", "anchor-inexistente", False),
    ],
)
def test_rechaza_referencias_inexistentes_en_todo_el_agregado(
    collection: str,
    field: str,
    missing_id: str,
    scalar: bool,
) -> None:
    from jurisprudence_case_models import JurisprudenceCase

    raw = deepcopy(valid_case())
    item = raw[collection][0]
    item[field] = missing_id if scalar else [missing_id]

    with pytest.raises(ValidationError, match=missing_id):
        JurisprudenceCase.model_validate(raw)


@pytest.mark.parametrize(
    ("collection", "id_field"),
    [
        ("legal_issues", "issue_id"),
        ("facts", "fact_id"),
        ("evidence_findings", "evidence_id"),
        ("legal_rules", "legal_rule_id"),
        ("holdings", "holding_id"),
        ("burden_of_proof_steps", "step_id"),
        ("source_anchors", "anchor_id"),
    ],
)
def test_rechaza_ids_duplicados_en_cada_coleccion(collection: str, id_field: str) -> None:
    from jurisprudence_case_models import JurisprudenceCase

    raw = deepcopy(valid_case())
    duplicate = deepcopy(raw[collection][0])
    raw[collection].append(duplicate)
    duplicated_id = duplicate[id_field]

    with pytest.raises(ValidationError, match=str(duplicated_id)):
        JurisprudenceCase.model_validate(raw)


def test_cada_holding_debe_pertenecer_a_la_cuestion_que_lo_referencia() -> None:
    from jurisprudence_case_models import JurisprudenceCase

    raw = deepcopy(valid_case())
    second_issue = deepcopy(raw["legal_issues"][0])
    second_issue.update(
        {
            "issue_id": "sancion-tributaria",
            "question": "¿Debía mantenerse la sanción?",
            "issue_type": "PENALTY",
            "holding_id": "holding-sancion-tributaria",
        }
    )
    second_holding = deepcopy(raw["holdings"][0])
    second_holding.update(
        {
            "holding_id": "holding-sancion-tributaria",
            "issue_id": "sancion-tributaria",
            "conclusion": "La sanción debía mantenerse.",
        }
    )
    raw["legal_issues"].append(second_issue)
    raw["holdings"].append(second_holding)
    raw["legal_issues"][0]["holding_id"] = "holding-sancion-tributaria"
    raw["legal_issues"][1]["holding_id"] = "holding-residencia-fiscal"

    with pytest.raises(ValidationError, match="no pertenece"):
        JurisprudenceCase.model_validate(raw)


def test_rechaza_holdings_huerfanos() -> None:
    from jurisprudence_case_models import JurisprudenceCase

    raw = deepcopy(valid_case())
    orphan = deepcopy(raw["holdings"][0])
    orphan["holding_id"] = "holding-huerfano"
    raw["holdings"].append(orphan)

    with pytest.raises(ValidationError, match="huérfanos"):
        JurisprudenceCase.model_validate(raw)


@pytest.mark.parametrize("invalid_source", ["hash", "page"])
def test_los_anclajes_pertenecen_al_pdf_y_a_una_pagina_existente(
    invalid_source: str,
) -> None:
    from jurisprudence_case_models import JurisprudenceCase

    raw = deepcopy(valid_case())
    if invalid_source == "hash":
        raw["source_anchors"][0]["source_sha256"] = "c" * 64
        expected = "source_sha256"
    else:
        raw["source_anchors"][0]["fragments"][0]["page_index"] = 11
        expected = "page_count"

    with pytest.raises(ValidationError, match=expected):
        JurisprudenceCase.model_validate(raw)


def test_la_secuencia_de_carga_de_prueba_debe_ser_contigua() -> None:
    from jurisprudence_case_models import JurisprudenceCase

    raw = deepcopy(valid_case())
    second_step = deepcopy(raw["burden_of_proof_steps"][0])
    second_step["step_id"] = "burden-contribuyente-desvirtua"
    second_step["sequence"] = 3
    raw["burden_of_proof_steps"].append(second_step)

    with pytest.raises(ValidationError, match="contigua"):
        JurisprudenceCase.model_validate(raw)
