"""Sincronización del JSON Schema y fixtures verbatim."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "residenciafiscal-verbatim-v1.schema.json"
FIXTURE_DIR = PROJECT_ROOT / "test" / "fixtures" / "verbatim_v1"
VALID_FIXTURE_PATH = FIXTURE_DIR / "valid_minimal.json"
INVALID_FIXTURE_PATH = FIXTURE_DIR / "invalid_page_hash.json"


def test_renderiza_json_schema_verbatim_determinista() -> None:
    from verbatim_models import VerbatimCorpus
    from verbatim_schema import render_verbatim_json_schema

    rendered = render_verbatim_json_schema()

    assert rendered.endswith("\n")
    assert json.loads(rendered) == VerbatimCorpus.model_json_schema()


def test_escribe_schema_verbatim_en_destino_explicito(tmp_path: Path) -> None:
    from verbatim_schema import (
        render_verbatim_json_schema,
        write_verbatim_json_schema,
    )

    destination = tmp_path / "verbatim.schema.json"

    written_path = write_verbatim_json_schema(destination)

    assert written_path == destination
    assert destination.read_text(encoding="utf-8") == render_verbatim_json_schema()


def test_json_schema_verbatim_versionado_esta_sincronizado() -> None:
    from verbatim_schema import render_verbatim_json_schema

    assert SCHEMA_PATH.read_text(encoding="utf-8") == render_verbatim_json_schema()


def test_fixture_minimo_cumple_el_contrato_verbatim() -> None:
    from verbatim_models import VerbatimCorpus

    corpus = VerbatimCorpus.model_validate_json(VALID_FIXTURE_PATH.read_text(encoding="utf-8"))

    assert corpus.document_id == "documento-prueba"
    assert corpus.pages[0].raw_page_text == "Texto íntegro de prueba.\n"


def test_fixture_invalido_documenta_hash_de_pagina_incorrecto() -> None:
    from verbatim_models import VerbatimCorpus

    raw = json.loads(VALID_FIXTURE_PATH.read_text(encoding="utf-8"))
    mutation = json.loads(INVALID_FIXTURE_PATH.read_text(encoding="utf-8"))
    raw["pages"][mutation["page_index"]][mutation["field"]] = mutation["value"]

    with pytest.raises(ValidationError, match=mutation["expected_error"]):
        VerbatimCorpus.model_validate(raw)
