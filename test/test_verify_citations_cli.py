"""Pruebas del CLI reproducible del spike. No invocan ningún LLM."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from citation_models import ExtractedPage
from verify_citations import main, parse_thresholds


def test_parsea_y_ordena_umbrales_sin_duplicados() -> None:
    assert parse_thresholds("90, 80,85,90") == (80.0, 85.0, 90.0)


@pytest.mark.parametrize("raw", ["", "0,85", "101", "texto"])
def test_rechaza_umbrales_invalidos(raw: str) -> None:
    with pytest.raises(ValueError):
        parse_thresholds(raw)


def test_cli_genera_json_detallado_e_informe_markdown(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "analisis.jsonl"
    pdf_dir = tmp_path / "sentencias"
    output_dir = tmp_path / "informe"
    pdf_dir.mkdir()
    (pdf_dir / "sentencia.pdf").touch()
    jsonl_path.write_text(
        json.dumps(
            {
                "archivo": "sentencia.pdf",
                "frases_clave": [
                    {
                        "tema": "criterio",
                        "pagina": "1",
                        "texto": "La residencia habitual estaba en España.",
                    }
                ],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    with jsonl_path.open("a", encoding="utf-8") as destination:
        destination.write(
            json.dumps(
                {
                    "archivo": "otra-sentencia.pdf",
                    "frases_clave": [
                        {
                            "tema": "prueba",
                            "pagina": "1",
                            "texto": "Esta cita no debe entrar en el spike acotado.",
                        }
                    ],
                },
                ensure_ascii=False,
            )
            + "\n"
        )
    (pdf_dir / "otra-sentencia.pdf").touch()

    exit_code = main(
        [
            "--jsonl",
            str(jsonl_path),
            "--pdf-dir",
            str(pdf_dir),
            "--output-dir",
            str(output_dir),
            "--source-file",
            "sentencia.pdf",
            "--threshold",
            "85",
            "--thresholds",
            "80,85,90",
        ],
        page_loader=lambda _path: (
            ExtractedPage(
                pdf_page_index=1,
                printed_page_label="7",
                text="La residencia habitual estaba en España.",
            ),
        ),
    )

    assert exit_code == 0
    json_report = json.loads(
        (output_dir / "citation-verification.json").read_text(encoding="utf-8")
    )
    markdown_report = (output_dir / "citation-verification.md").read_text(encoding="utf-8")
    assert json_report["config"]["threshold"] == 85
    assert json_report["config"]["source_file"] == "sentencia.pdf"
    assert json_report["config"]["candidates"] == 1
    assert len(json_report["config"]["source_jsonl_sha256"]) == 64
    assert json_report["summary"]["located_citations"] == 1
    assert json_report["summary"]["literal_citations"] == 1
    assert json_report["threshold_summaries"]["80"]["located_citations"] == 1
    assert json_report["findings"][0]["evidence_found"] is True
    assert json_report["findings"][0]["evidence_status"] == "found_declared_page"
    assert json_report["findings"][0]["literal_fidelity"] == "exact"
    assert json_report["findings"][0]["matched_pdf_page_indexes"] == [1]
    assert json_report["findings"][0]["matched_printed_page_labels"] == ["7"]
    assert json_report["findings"][0]["fragment_matches"][0]["score"] == 100
    assert "# Spike de verificación de citas" in markdown_report
    assert "| Sentencia | `sentencia.pdf` |" in markdown_report
    assert "## Detalle por cita" in markdown_report
    assert "La residencia habitual estaba en España." in markdown_report
    assert "`found_declared_page`" in markdown_report
    assert "`exact`" in markdown_report
    assert "Etiquetas impresas encontradas: 7" in markdown_report


def test_cli_filtra_y_ordena_por_manifiesto_sin_ejecutar_todo_el_jsonl(
    tmp_path: Path,
) -> None:
    jsonl_path = tmp_path / "analisis.jsonl"
    pdf_dir = tmp_path / "sentencias"
    output_dir = tmp_path / "informe"
    manifest_path = tmp_path / "muestra.json"
    pdf_dir.mkdir()
    for source_file in ("primera.pdf", "segunda.pdf"):
        (pdf_dir / source_file).touch()
    jsonl_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "archivo": "primera.pdf",
                        "frases_clave": [
                            {"tema": "criterio", "pagina": "1", "texto": "Cita primera."}
                        ],
                    }
                ),
                json.dumps(
                    {
                        "archivo": "segunda.pdf",
                        "frases_clave": [
                            {"tema": "prueba", "pagina": "1", "texto": "Cita segunda."}
                        ],
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "name": "solo-segunda",
                "expected_documents": 1,
                "documents": [
                    {
                        "archivo": "segunda.pdf",
                        "cubre": ["exacta"],
                        "motivo": "Valida el filtro por manifiesto.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--jsonl",
            str(jsonl_path),
            "--pdf-dir",
            str(pdf_dir),
            "--output-dir",
            str(output_dir),
            "--manifest",
            str(manifest_path),
            "--thresholds",
            "85",
        ],
        page_loader=lambda path: (f"Cita {path.stem}.",),
    )

    report = json.loads((output_dir / "citation-verification.json").read_text(encoding="utf-8"))
    markdown = (output_dir / "citation-verification.md").read_text(encoding="utf-8")
    assert exit_code == 0
    assert report["config"]["manifest"] == str(manifest_path)
    assert report["config"]["source_files"] == ["segunda.pdf"]
    assert [finding["source_file"] for finding in report["findings"]] == ["segunda.pdf"]
    assert "| Sentencia | `segunda.pdf` |" in markdown
