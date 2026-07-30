"""Contrato ejecutable de `residenciafiscal-verbatim/1`."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy

import pytest
from pydantic import ValidationError


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _pages_sha256(pages: list[dict[str, object]]) -> str:
    canonical = json.dumps(
        pages,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _valid_payload() -> dict[str, object]:
    pages: list[dict[str, object]] = [
        {
            "page_index": 1,
            "printed_page": None,
            "raw_page_text": "\x00 Primera página \n",
            "text_sha256": _sha256_text("\x00 Primera página \n"),
            "extraction_status": "TEXT_EXTRACTED",
        },
        {
            "page_index": 2,
            "printed_page": "1",
            "raw_page_text": "",
            "text_sha256": _sha256_text(""),
            "extraction_status": "EMPTY_TEXT",
        },
    ]
    return {
        "schema_version": "residenciafiscal-verbatim/1",
        "document_id": "san-1210-2023",
        "source_file": "sentencias/SAN_1210_2023.pdf",
        "source_sha256": "a" * 64,
        "extractor": {"name": "pypdf", "version": "6.14.2"},
        "page_count": 2,
        "pages_sha256": _pages_sha256(pages),
        "status": "NEEDS_REVIEW",
        "pages": pages,
    }


def test_acepta_corpus_verbatim_con_texto_crudo_y_hashes() -> None:
    from verbatim_models import VerbatimCorpus

    corpus = VerbatimCorpus.model_validate(_valid_payload())

    assert corpus.schema_version == "residenciafiscal-verbatim/1"
    assert corpus.pages[0].raw_page_text == "\x00 Primera página \n"
    assert corpus.pages[1].extraction_status == "EMPTY_TEXT"


@pytest.mark.parametrize("field", ["text_sha256", "pages_sha256"])
def test_rechaza_hashes_que_no_corresponden_al_texto(field: str) -> None:
    from verbatim_models import VerbatimCorpus

    raw = deepcopy(_valid_payload())
    if field == "text_sha256":
        raw["pages"][0][field] = "b" * 64  # type: ignore[index]
    else:
        raw[field] = "b" * 64

    with pytest.raises(ValidationError, match=field):
        VerbatimCorpus.model_validate(raw)


@pytest.mark.parametrize("invalid_index", [1, 3])
def test_las_paginas_deben_ser_contiguas_y_empezar_en_uno(
    invalid_index: int,
) -> None:
    from verbatim_models import VerbatimCorpus

    raw = deepcopy(_valid_payload())
    raw["pages"][1]["page_index"] = invalid_index  # type: ignore[index]
    raw["pages_sha256"] = _pages_sha256(raw["pages"])  # type: ignore[arg-type]

    with pytest.raises(ValidationError, match="contigu"):
        VerbatimCorpus.model_validate(raw)


def test_page_count_debe_coincidir_con_los_registros() -> None:
    from verbatim_models import VerbatimCorpus

    raw = deepcopy(_valid_payload())
    raw["page_count"] = 3

    with pytest.raises(ValidationError, match="page_count"):
        VerbatimCorpus.model_validate(raw)


@pytest.mark.parametrize(
    ("raw_text", "extraction_status"),
    [("", "TEXT_EXTRACTED"), ("texto", "EMPTY_TEXT")],
)
def test_estado_de_extraccion_debe_describir_el_valor_crudo(
    raw_text: str,
    extraction_status: str,
) -> None:
    from verbatim_models import VerbatimPage

    raw = {
        "page_index": 1,
        "printed_page": None,
        "raw_page_text": raw_text,
        "text_sha256": _sha256_text(raw_text),
        "extraction_status": extraction_status,
    }

    with pytest.raises(ValidationError, match="extraction_status"):
        VerbatimPage.model_validate(raw)


def test_estado_global_debe_reflejar_paginas_sin_texto() -> None:
    from verbatim_models import VerbatimCorpus

    raw = deepcopy(_valid_payload())
    raw["status"] = "COMPLETE"

    with pytest.raises(ValidationError, match="status"):
        VerbatimCorpus.model_validate(raw)


@pytest.mark.parametrize(
    "source_file",
    ["/tmp/SAN_1210_2023.pdf", "../SAN_1210_2023.pdf", "sentencias/source.txt"],
)
def test_source_file_es_una_ruta_pdf_relativa_y_portable(source_file: str) -> None:
    from verbatim_models import VerbatimCorpus

    raw = deepcopy(_valid_payload())
    raw["source_file"] = source_file

    with pytest.raises(ValidationError, match="source_file"):
        VerbatimCorpus.model_validate(raw)
