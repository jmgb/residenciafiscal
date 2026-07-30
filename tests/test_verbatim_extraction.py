"""Extracción cruda y reproducible de páginas PDF."""

from __future__ import annotations

import hashlib
from pathlib import Path


class _FakePage:
    def __init__(self, extracted_text: str | None) -> None:
        self.extracted_text = extracted_text

    def extract_text(self) -> str | None:
        return self.extracted_text


class _FakeReader:
    def __init__(self, texts: tuple[str | None, ...]) -> None:
        self.pages = tuple(_FakePage(text) for text in texts)


def test_conserva_exactamente_la_salida_de_pypdf(tmp_path: Path) -> None:
    from verbatim_extraction import extract_verbatim_corpus

    pdf_path = tmp_path / "source.pdf"
    pdf_bytes = b"%PDF-synthetic-for-unit-test"
    pdf_path.write_bytes(pdf_bytes)
    raw_text = "\x00  Cabecera sin limpiar\nCuerpo con espacio final  \n  1  \n"

    corpus = extract_verbatim_corpus(
        pdf_path,
        document_id="san-1210-2023",
        source_file="sentencias/SAN_1210_2023.pdf",
        reader_factory=lambda _: _FakeReader((raw_text,)),
        extractor_version="6.14.2",
    )

    assert corpus.pages[0].raw_page_text == raw_text
    assert corpus.pages[0].printed_page == "1"
    assert corpus.pages[0].text_sha256 == hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    assert corpus.source_sha256 == hashlib.sha256(pdf_bytes).hexdigest()
    assert pdf_path.read_bytes() == pdf_bytes


def test_distingue_none_de_cadena_vacia_sin_inventar_texto(
    tmp_path: Path,
) -> None:
    from verbatim_extraction import extract_verbatim_corpus

    pdf_path = tmp_path / "source.pdf"
    pdf_path.write_bytes(b"pdf")

    corpus = extract_verbatim_corpus(
        pdf_path,
        document_id="documento-prueba",
        source_file="sentencias/documento-prueba.pdf",
        reader_factory=lambda _: _FakeReader((None, "")),
        extractor_version="test-version",
    )

    assert [page.raw_page_text for page in corpus.pages] == ["", ""]
    assert [page.extraction_status for page in corpus.pages] == [
        "NO_TEXT_RETURNED",
        "EMPTY_TEXT",
    ]
    assert corpus.status == "NEEDS_REVIEW"


def test_usa_indices_fisicos_uno_based_y_hash_global_determinista(
    tmp_path: Path,
) -> None:
    from verbatim_extraction import extract_verbatim_corpus

    pdf_path = tmp_path / "source.pdf"
    pdf_path.write_bytes(b"pdf")

    def reader_factory(_: str) -> _FakeReader:
        return _FakeReader(("página uno", "página dos"))

    first = extract_verbatim_corpus(
        pdf_path,
        document_id="documento-prueba",
        source_file="sentencias/documento-prueba.pdf",
        reader_factory=reader_factory,
        extractor_version="test-version",
    )
    second = extract_verbatim_corpus(
        pdf_path,
        document_id="documento-prueba",
        source_file="sentencias/documento-prueba.pdf",
        reader_factory=reader_factory,
        extractor_version="test-version",
    )

    assert [page.page_index for page in first.pages] == [1, 2]
    assert first.status == "COMPLETE"
    assert first.pages_sha256 == second.pages_sha256
    assert first == second


def test_identifica_la_version_instalada_del_extractor(tmp_path: Path) -> None:
    from importlib.metadata import version

    from verbatim_extraction import extract_verbatim_corpus

    pdf_path = tmp_path / "source.pdf"
    pdf_path.write_bytes(b"pdf")

    corpus = extract_verbatim_corpus(
        pdf_path,
        document_id="documento-prueba",
        source_file="sentencias/documento-prueba.pdf",
        reader_factory=lambda _: _FakeReader(("texto",)),
    )

    assert corpus.extractor.name == "pypdf"
    assert corpus.extractor.version == version("pypdf")
