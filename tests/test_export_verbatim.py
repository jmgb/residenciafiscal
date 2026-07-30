"""CLI reproducible para materializar un corpus verbatim."""

from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfWriter


def test_exporta_y_valida_un_pdf_sin_llm(
    tmp_path: Path,
    capsys,
) -> None:
    from export_verbatim import main
    from verbatim_artifact import load_verbatim_corpus

    pdf_path = tmp_path / "sentencias" / "source.pdf"
    pdf_path.parent.mkdir(parents=True)
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    with pdf_path.open("wb") as destination:
        writer.write(destination)
    output_path = tmp_path / "verbatim" / "documento-prueba.pages.json"

    exit_code = main(
        [
            "--pdf",
            str(pdf_path),
            "--document-id",
            "documento-prueba",
            "--source-file",
            "sentencias/source.pdf",
            "--output",
            str(output_path),
            "--project-root",
            str(tmp_path),
        ]
    )

    report = json.loads(capsys.readouterr().out)
    corpus = load_verbatim_corpus(output_path.read_bytes())
    assert exit_code == 0
    assert corpus.page_count == 1
    assert corpus.status == "NEEDS_REVIEW"
    assert report["validation"] == "passed"
    assert report["artifact"] == str(output_path)
