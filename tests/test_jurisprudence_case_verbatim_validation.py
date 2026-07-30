"""Validación literal de los anclajes v3 contra el corpus verbatim."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
from jurisprudence_case_v3_factory import valid_case


def _case():
    from jurisprudence_case_models import JurisprudenceCase

    return JurisprudenceCase.model_validate(valid_case())


def _verbatim():
    from verbatim_hashing import sha256_canonical_pages, sha256_utf8
    from verbatim_models import VerbatimCorpus

    phrase = "tiene su residencia efectiva"
    pages = []
    for page_index in range(1, 11):
        text = "x" * 100 + phrase if page_index == 8 else f"Página {page_index}"
        pages.append(
            {
                "page_index": page_index,
                "printed_page": str(page_index),
                "raw_page_text": text,
                "text_sha256": sha256_utf8(text),
                "extraction_status": "TEXT_EXTRACTED",
            }
        )
    return VerbatimCorpus.model_validate(
        {
            "schema_version": "residenciafiscal-verbatim/1",
            "document_id": "san-1210-2023",
            "source_file": "SAN_1210_2023.pdf",
            "source_sha256": "a" * 64,
            "extractor": {"name": "pypdf", "version": "6.14.2"},
            "page_count": 10,
            "pages_sha256": sha256_canonical_pages(pages),
            "status": "COMPLETE",
            "pages": pages,
        }
    )


def test_valida_cada_fragmento_como_slice_exacto() -> None:
    from jurisprudence_case_verbatim_validation import validate_case_against_verbatim

    result = validate_case_against_verbatim(_case(), _verbatim())

    assert result.judgment_id == "san-1210-2023"
    assert result.anchor_count == 1
    assert result.fragment_count == 1


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("start_offset", 99, "no coincide"),
        ("end_offset", 127, "no coincide"),
        ("verbatim_text", "texto inventado", "no coincide"),
        ("printed_page", "7", "printed_page"),
    ],
)
def test_rechaza_fragmentos_no_literales(field: str, value: object, message: str) -> None:
    from jurisprudence_case_models import JurisprudenceCase
    from jurisprudence_case_verbatim_validation import validate_case_against_verbatim

    raw = deepcopy(valid_case())
    raw["source_anchors"][0]["fragments"][0][field] = value
    case = JurisprudenceCase.model_validate(raw)

    with pytest.raises(ValueError, match=message):
        validate_case_against_verbatim(case, _verbatim())


def test_rechaza_metadatos_incompatibles() -> None:
    from jurisprudence_case_models import JurisprudenceCase
    from jurisprudence_case_verbatim_validation import validate_case_against_verbatim

    raw = deepcopy(valid_case())
    raw["judgment"]["extractor"]["version"] = "other"
    case = JurisprudenceCase.model_validate(raw)

    with pytest.raises(ValueError, match="extractor"):
        validate_case_against_verbatim(case, _verbatim())


def test_validador_de_artefactos_comprueba_hashes_de_entradas(tmp_path: Path) -> None:
    from jurisprudence_case_artifact import write_jurisprudence_case
    from jurisprudence_case_models import JurisprudenceCase
    from jurisprudence_case_verbatim_validation import validate_case_artifact
    from okf_provenance import sha256_file
    from verbatim_artifact import write_verbatim_corpus

    verbatim_path = tmp_path / "knowledge" / "verbatim" / "case.pages.json"
    write_verbatim_corpus(_verbatim(), verbatim_path)
    raw = deepcopy(valid_case())
    raw["judgment"]["analysis_provenance"]["input_artifacts"][0] = {
        "kind": "VERBATIM",
        "source_path": "knowledge/verbatim/case.pages.json",
        "sha256": sha256_file(verbatim_path),
    }
    case_path = tmp_path / "knowledge" / "cases" / "case.case.json"
    write_jurisprudence_case(JurisprudenceCase.model_validate(raw), case_path)

    result = validate_case_artifact(
        case_path,
        verbatim_path=verbatim_path,
        project_root=tmp_path,
    )

    assert result.input_artifact_count == 1
    assert len(result.case_sha256) == 64


def test_validador_de_artefactos_rechaza_entrada_modificada(tmp_path: Path) -> None:
    from jurisprudence_case_artifact import write_jurisprudence_case
    from jurisprudence_case_models import JurisprudenceCase
    from jurisprudence_case_verbatim_validation import validate_case_artifact
    from verbatim_artifact import write_verbatim_corpus

    verbatim_path = tmp_path / "knowledge" / "verbatim" / "case.pages.json"
    write_verbatim_corpus(_verbatim(), verbatim_path)
    case_path = tmp_path / "knowledge" / "cases" / "case.case.json"
    write_jurisprudence_case(JurisprudenceCase.model_validate(valid_case()), case_path)

    with pytest.raises(ValueError, match="input_artifacts"):
        validate_case_artifact(
            case_path,
            verbatim_path=verbatim_path,
            project_root=tmp_path,
        )
