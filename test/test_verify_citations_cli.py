"""Pruebas del CLI reproducible del spike. No invocan ningún LLM."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

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
        page_loader=lambda _path: ("La residencia habitual estaba en España.",),
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
    assert json_report["summary"]["verified_citations"] == 1
    assert json_report["threshold_summaries"]["80"]["verified_citations"] == 1
    assert json_report["findings"][0]["status"] == "verified_declared_page"
    assert json_report["findings"][0]["fragment_matches"][0]["score"] == 100
    assert "# Spike de verificación de citas" in markdown_report
    assert "| Sentencia | `sentencia.pdf` |" in markdown_report
    assert "## Detalle por cita" in markdown_report
    assert "La residencia habitual estaba en España." in markdown_report
    assert "`verified_declared_page`" in markdown_report
