"""Serialización y escritura del caso jurisprudencial v3."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jurisprudence_case_v3_factory import valid_case
from pydantic import ValidationError


def _case():
    from jurisprudence_case_models import JurisprudenceCase

    return JurisprudenceCase.model_validate(valid_case())


def test_render_es_determinista_y_valido_al_recargar() -> None:
    from jurisprudence_case_artifact import (
        load_jurisprudence_case,
        render_jurisprudence_case,
    )

    case = _case()

    first = render_jurisprudence_case(case)
    second = render_jurisprudence_case(case)

    assert first == second
    assert first.endswith("\n")
    assert json.loads(first)["schema_version"] == "residenciafiscal-case/3"
    assert load_jurisprudence_case(first) == case


def test_escritura_atomica_no_deja_temporales(tmp_path: Path) -> None:
    from jurisprudence_case_artifact import (
        render_jurisprudence_case,
        write_jurisprudence_case,
    )

    case = _case()
    destination = tmp_path / "nested" / "document.case.json"

    written_path = write_jurisprudence_case(case, destination)

    assert written_path == destination
    assert destination.read_text(encoding="utf-8") == render_jurisprudence_case(case)
    assert list(destination.parent.iterdir()) == [destination]


def test_loader_rechaza_un_caso_manipulado() -> None:
    from jurisprudence_case_artifact import load_jurisprudence_case

    raw = valid_case()
    raw["judgment"]["unexpected"] = True

    with pytest.raises(ValidationError, match="unexpected"):
        load_jurisprudence_case(json.dumps(raw))
