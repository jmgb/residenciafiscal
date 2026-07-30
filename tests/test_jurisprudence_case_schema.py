"""Sincronización de los artefactos del schema jurisprudencial v3."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "residenciafiscal-case-v3.schema.json"
FIXTURE_PATH = PROJECT_ROOT / "tests" / "fixtures" / "jurisprudence_case_v3" / "valid_minimal.json"
INVALID_FIXTURE_PATH = (
    PROJECT_ROOT / "tests" / "fixtures" / "jurisprudence_case_v3" / "invalid_missing_reference.json"
)


def test_renderiza_json_schema_determinista() -> None:
    from jurisprudence_case_models import JurisprudenceCase
    from jurisprudence_case_schema import render_case_json_schema

    rendered = render_case_json_schema()

    assert rendered.endswith("\n")
    assert json.loads(rendered) == JurisprudenceCase.model_json_schema()


def test_escribe_el_schema_en_un_destino_explicito(tmp_path: Path) -> None:
    from jurisprudence_case_schema import (
        render_case_json_schema,
        write_case_json_schema,
    )

    destination = tmp_path / "case.schema.json"

    written_path = write_case_json_schema(destination)

    assert written_path == destination
    assert destination.read_text(encoding="utf-8") == render_case_json_schema()


def test_el_json_schema_versionado_esta_sincronizado() -> None:
    from jurisprudence_case_schema import render_case_json_schema

    assert SCHEMA_PATH.read_text(encoding="utf-8") == render_case_json_schema()


def test_fixture_minimo_cumple_el_contrato_v3() -> None:
    from jurisprudence_case_models import JurisprudenceCase

    case = JurisprudenceCase.model_validate_json(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert case.judgment.judgment_id == "san-1210-2023"


def test_fixture_invalido_documenta_una_referencia_huerfana() -> None:
    from pydantic import ValidationError

    from jurisprudence_case_models import JurisprudenceCase

    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    mutation = json.loads(INVALID_FIXTURE_PATH.read_text(encoding="utf-8"))
    item = raw[mutation["collection"]][mutation["index"]]
    item[mutation["field"]] = mutation["value"]

    with pytest.raises(ValidationError, match=mutation["expected_error"]):
        JurisprudenceCase.model_validate(raw)
