"""Resultado residencial tipado, distinto del vencedor procesal."""

from __future__ import annotations

from copy import deepcopy

import pytest
from jurisprudence_case_v3_factory import valid_case
from pydantic import ValidationError


def test_acepta_una_determinacion_residencial_tipadada() -> None:
    from jurisprudence_case_models import JurisprudenceCase

    case = JurisprudenceCase.model_validate(valid_case())
    determination = case.holdings[0].residence_determination

    assert determination is not None
    assert determination.spanish_residence == "RESIDENT_IN_SPAIN"
    assert determination.tax_years == (2011, 2013)
    assert determination.other_country is None


@pytest.mark.parametrize(
    ("determination", "error"),
    [
        (
            {
                "spanish_residence": "RESIDENT_IN_SPAIN",
                "tax_years": [2011],
                "other_country": "Suiza",
                "non_resident_from": None,
            },
            "other_country",
        ),
        (
            {
                "spanish_residence": "NON_RESIDENT_IN_SPAIN",
                "tax_years": [2011],
                "other_country": None,
                "non_resident_from": None,
            },
            "other_country",
        ),
        (
            {
                "spanish_residence": "PARTIAL_YEAR_IN_SPAIN",
                "tax_years": [2009],
                "other_country": "Suiza",
                "non_resident_from": None,
            },
            "non_resident_from",
        ),
    ],
)
def test_rechaza_combinaciones_residenciales_incoherentes(
    determination: dict[str, object],
    error: str,
) -> None:
    from jurisprudence_case_models import JurisprudenceCase

    raw = deepcopy(valid_case())
    raw["holdings"][0]["residence_determination"] = determination

    with pytest.raises(ValidationError, match=error):
        JurisprudenceCase.model_validate(raw)


def test_rechaza_determinacion_residencial_en_una_cuestion_no_residencial() -> None:
    from jurisprudence_case_models import JurisprudenceCase

    raw = deepcopy(valid_case())
    raw["legal_issues"][0]["issue_type"] = "PENALTY"

    with pytest.raises(ValidationError, match="solo es válida para TAX_RESIDENCE"):
        JurisprudenceCase.model_validate(raw)


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("tax_years", [2008], "tax_years"),
        ("other_country", "Suiza", "countries"),
    ],
)
def test_liga_la_determinacion_a_ejercicios_y_paises_de_la_sentencia(
    field: str,
    value: object,
    error: str,
) -> None:
    from jurisprudence_case_models import JurisprudenceCase

    raw = deepcopy(valid_case())
    determination = raw["holdings"][0]["residence_determination"]
    determination["spanish_residence"] = "NON_RESIDENT_IN_SPAIN"
    determination["other_country"] = "Mónaco"
    determination[field] = value

    with pytest.raises(ValidationError, match=error):
        JurisprudenceCase.model_validate(raw)


def test_fecha_de_no_residencia_pertenece_al_ejercicio_determinado() -> None:
    from jurisprudence_case_models import JurisprudenceCase

    raw = deepcopy(valid_case())
    determination = raw["holdings"][0]["residence_determination"]
    determination.update(
        {
            "spanish_residence": "PARTIAL_YEAR_IN_SPAIN",
            "other_country": "Mónaco",
            "non_resident_from": "2010-04-01",
        }
    )

    with pytest.raises(ValidationError, match="non_resident_from"):
        JurisprudenceCase.model_validate(raw)
