"""Serialización y escritura del corpus verbatim."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = PROJECT_ROOT / "tests" / "fixtures" / "verbatim_v1" / "valid_minimal.json"


def _fixture_corpus():
    from verbatim_models import VerbatimCorpus

    return VerbatimCorpus.model_validate_json(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_render_es_determinista_y_valida_al_recargar() -> None:
    from verbatim_artifact import load_verbatim_corpus, render_verbatim_corpus

    corpus = _fixture_corpus()

    first = render_verbatim_corpus(corpus)
    second = render_verbatim_corpus(corpus)

    assert first == second
    assert first.endswith("\n")
    assert json.loads(first)["schema_version"] == "residenciafiscal-verbatim/1"
    assert load_verbatim_corpus(first) == corpus


def test_escritura_atomica_no_deja_temporales(tmp_path: Path) -> None:
    from verbatim_artifact import render_verbatim_corpus, write_verbatim_corpus

    corpus = _fixture_corpus()
    destination = tmp_path / "nested" / "document.pages.json"

    written_path = write_verbatim_corpus(corpus, destination)

    assert written_path == destination
    assert destination.read_text(encoding="utf-8") == render_verbatim_corpus(corpus)
    assert list(destination.parent.iterdir()) == [destination]


def test_dos_escrituras_producen_los_mismos_bytes(tmp_path: Path) -> None:
    from verbatim_artifact import write_verbatim_corpus

    corpus = _fixture_corpus()
    first_path = tmp_path / "first.pages.json"
    second_path = tmp_path / "second.pages.json"

    write_verbatim_corpus(corpus, first_path)
    write_verbatim_corpus(corpus, second_path)

    assert first_path.read_bytes() == second_path.read_bytes()


def test_loader_rechaza_un_artefacto_manipulado() -> None:
    from verbatim_artifact import load_verbatim_corpus

    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    raw["pages"][0]["raw_page_text"] = "Texto alterado"

    with pytest.raises(ValidationError, match="text_sha256"):
        load_verbatim_corpus(json.dumps(raw))
