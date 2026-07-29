"""Validación del artefacto verbatim contra su PDF."""

from __future__ import annotations

from pathlib import Path

import pytest
from test_verbatim_extraction import _FakeReader


def _build_artifact(
    tmp_path: Path,
    *,
    extracted_text: str = "Texto original\n1\n",
) -> tuple[Path, Path]:
    from verbatim_artifact import write_verbatim_corpus
    from verbatim_extraction import extract_verbatim_corpus

    pdf_path = tmp_path / "sentencias" / "source.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"pdf-source")
    corpus = extract_verbatim_corpus(
        pdf_path,
        document_id="documento-prueba",
        source_file="sentencias/source.pdf",
        reader_factory=lambda _: _FakeReader((extracted_text,)),
        extractor_version="test-version",
    )
    artifact_path = tmp_path / "verbatim" / "documento-prueba.pages.json"
    write_verbatim_corpus(corpus, artifact_path)
    return pdf_path, artifact_path


def test_valida_pdf_hash_y_reextraccion_completa(tmp_path: Path) -> None:
    from verbatim_validation import validate_verbatim_artifact

    _, artifact_path = _build_artifact(tmp_path)

    result = validate_verbatim_artifact(
        artifact_path,
        project_root=tmp_path,
        reader_factory=lambda _: _FakeReader(("Texto original\n1\n",)),
        extractor_version="test-version",
    )

    assert result.document_id == "documento-prueba"
    assert result.page_count == 1
    assert result.status == "COMPLETE"
    assert len(result.artifact_sha256) == 64


def test_rechaza_si_el_pdf_cambia_despues_del_build(tmp_path: Path) -> None:
    from verbatim_validation import validate_verbatim_artifact

    pdf_path, artifact_path = _build_artifact(tmp_path)
    pdf_path.write_bytes(b"pdf-source-modified")

    with pytest.raises(ValueError, match="source_sha256"):
        validate_verbatim_artifact(
            artifact_path,
            project_root=tmp_path,
            reader_factory=lambda _: _FakeReader(("Texto original\n1\n",)),
            extractor_version="test-version",
        )


def test_rechaza_si_la_reextraccion_no_reproduce_las_paginas(
    tmp_path: Path,
) -> None:
    from verbatim_validation import validate_verbatim_artifact

    _, artifact_path = _build_artifact(tmp_path)

    with pytest.raises(ValueError, match="reextracción"):
        validate_verbatim_artifact(
            artifact_path,
            project_root=tmp_path,
            reader_factory=lambda _: _FakeReader(("Texto diferente\n1\n",)),
            extractor_version="test-version",
        )


def test_rechaza_si_la_version_del_extractor_no_coincide(tmp_path: Path) -> None:
    from verbatim_validation import validate_verbatim_artifact

    _, artifact_path = _build_artifact(tmp_path)

    with pytest.raises(ValueError, match="extractor"):
        validate_verbatim_artifact(
            artifact_path,
            project_root=tmp_path,
            reader_factory=lambda _: _FakeReader(("Texto original\n1\n",)),
            extractor_version="other-version",
        )
