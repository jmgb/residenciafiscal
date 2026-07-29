"""Invariantes del análisis de convenios de doble imposición."""

from copy import deepcopy

import pytest
from jurisprudence_case_v3_factory import case_with_treaty
from pydantic import ValidationError


@pytest.mark.parametrize("invalid_treaty", ["decisive_step", "sequence"])
def test_el_analisis_cdi_exige_paso_decisivo_propio_y_secuencia_contigua(
    invalid_treaty: str,
) -> None:
    from jurisprudence_case_models import JurisprudenceCase

    raw = case_with_treaty()
    treaty = raw["treaty_analyses"][0]
    if invalid_treaty == "decisive_step":
        treaty["decisive_step_id"] = "treaty-step-inexistente"
        expected = "treaty-step-inexistente"
    else:
        treaty["steps"][0]["sequence"] = 2
        expected = "contigua"

    with pytest.raises(ValidationError, match=expected):
        JurisprudenceCase.model_validate(raw)


@pytest.mark.parametrize(
    ("target", "field", "missing_id"),
    [
        ("analysis", "domestic_law_issue_ids", "issue-inexistente"),
        ("analysis", "anchor_ids", "anchor-inexistente"),
        ("step", "fact_ids", "fact-inexistente"),
        ("step", "evidence_ids", "evidence-inexistente"),
        ("step", "anchor_ids", "anchor-inexistente"),
    ],
)
def test_el_analisis_cdi_solo_referencia_elementos_del_mismo_caso(
    target: str,
    field: str,
    missing_id: str,
) -> None:
    from jurisprudence_case_models import JurisprudenceCase

    raw = case_with_treaty()
    treaty = raw["treaty_analyses"][0]
    item = treaty if target == "analysis" else treaty["steps"][0]
    item[field] = [missing_id]

    with pytest.raises(ValidationError, match=missing_id):
        JurisprudenceCase.model_validate(raw)


@pytest.mark.parametrize("duplicate_target", ["analysis", "step"])
def test_rechaza_ids_duplicados_en_el_analisis_cdi(duplicate_target: str) -> None:
    from jurisprudence_case_models import JurisprudenceCase

    raw = case_with_treaty()
    treaty = raw["treaty_analyses"][0]
    if duplicate_target == "analysis":
        duplicate = deepcopy(treaty)
        raw["treaty_analyses"].append(duplicate)
        expected = "treaty-spain-switzerland"
    else:
        duplicate = deepcopy(treaty["steps"][0])
        duplicate["sequence"] = 2
        treaty["steps"].append(duplicate)
        expected = "treaty-step-permanent-home"

    with pytest.raises(ValidationError, match=expected):
        JurisprudenceCase.model_validate(raw)
