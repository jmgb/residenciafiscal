"""Invariantes locales de hechos, pruebas y caso agregado."""

from copy import deepcopy

import pytest
from jurisprudence_case_v3_factory import valid_case
from pydantic import ValidationError


def test_acepta_un_caso_v3_completo_y_tipado() -> None:
    from jurisprudence_case_models import JurisprudenceCase

    case = JurisprudenceCase.model_validate(valid_case())

    assert case.schema_version == "residenciafiscal-case/3"
    assert case.judgment.judgment_id == "san-1210-2023"
    assert case.legal_issues[0].holding_id == "holding-residencia-fiscal"
    assert case.source_anchors[0].fragments[0].page_index == 8


def test_un_hecho_no_puede_terminar_antes_de_empezar() -> None:
    from jurisprudence_case_entities import CaseFact

    raw = deepcopy(valid_case()["facts"][0])
    raw["start_date"] = "2023-02-22"
    raw["end_date"] = "2023-02-21"

    with pytest.raises(ValidationError, match="end_date"):
        CaseFact.model_validate(raw)


def test_un_hecho_probado_por_el_tribunal_exige_anclaje() -> None:
    from jurisprudence_case_entities import CaseFact

    raw = deepcopy(valid_case()["facts"][0])
    raw["anchor_ids"] = []

    with pytest.raises(ValidationError, match="anchor_ids"):
        CaseFact.model_validate(raw)


@pytest.mark.parametrize("missing_field", ["assessment_reason", "anchor_ids"])
def test_una_prueba_valorada_exige_motivo_y_anclaje(missing_field: str) -> None:
    from jurisprudence_case_evidence import EvidenceFinding

    raw = deepcopy(valid_case()["evidence_findings"][0])
    raw[missing_field] = None if missing_field == "assessment_reason" else []

    with pytest.raises(ValidationError, match=missing_field):
        EvidenceFinding.model_validate(raw)
