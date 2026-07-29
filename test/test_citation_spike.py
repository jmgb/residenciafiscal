"""Pruebas de la orquestación del spike de citas. No invocan ningún LLM."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from citation_report import render_markdown_report, summarize_findings
from citation_spike import (
    CitationCandidate,
    extract_citation_candidates,
    load_citation_sources,
    verify_loaded_citations,
)
from citation_verification import CitationStatus


def test_extrae_solo_frases_clave_con_texto() -> None:
    records: list[Mapping[str, object]] = [
        {
            "archivo": "sentencia.pdf",
            "frases_clave": [
                {"tema": "criterio", "pagina": "PÁGINA 2", "texto": "Una cita válida."},
                {"tema": "prueba", "pagina": "3", "texto": "   "},
                "valor inesperado",
            ],
        },
        {"archivo": "sin-frases.pdf", "frases_clave": None},
    ]

    assert extract_citation_candidates(records) == (
        CitationCandidate(
            source_file="sentencia.pdf",
            citation_index=0,
            topic="criterio",
            declared_page="PÁGINA 2",
            quote="Una cita válida.",
        ),
    )


def test_extrae_cada_pdf_una_sola_vez_y_conserva_errores(tmp_path: Path) -> None:
    existing_pdf = tmp_path / "sentencia.pdf"
    existing_pdf.touch()
    candidates = (
        CitationCandidate("sentencia.pdf", 0, "criterio", "1", "Primera cita válida."),
        CitationCandidate("sentencia.pdf", 1, "prueba", "2", "Segunda cita válida."),
        CitationCandidate("falta.pdf", 0, "prueba", "1", "Cita sin documento fuente."),
    )
    calls: list[Path] = []

    def page_loader(path: Path) -> tuple[str, ...]:
        calls.append(path)
        return ("Primera cita válida.", "Segunda cita válida.")

    loaded = load_citation_sources(candidates, tmp_path, page_loader=page_loader)

    assert calls == [existing_pdf]
    assert loaded[0].pages == ("Primera cita válida.", "Segunda cita válida.")
    assert loaded[1].pages == loaded[0].pages
    assert loaded[2].pages is None
    assert loaded[2].error == "source_missing"


def test_resume_estados_y_causas_observables() -> None:
    candidates = (
        CitationCandidate(
            "sentencia.pdf",
            0,
            "criterio",
            "1",
            "La residencia habitual estaba en España.",
        ),
        CitationCandidate(
            "sentencia.pdf",
            1,
            "prueba",
            "1",
            "tarjetas de crédito... vivienda permanente en Francia",
        ),
    )

    loaded = load_citation_sources(
        candidates,
        Path("."),
        page_loader=lambda _path: (
            "La residencia habitual estaba en España. Las tarjetas de crédito se usaron aquí.",
        ),
        require_source_file=False,
    )
    findings = verify_loaded_citations(loaded, threshold=90)
    summary = summarize_findings(findings)

    assert findings[0].verification is not None
    assert findings[0].verification.status is CitationStatus.VERIFIED_DECLARED_PAGE
    assert findings[1].verification is not None
    assert findings[1].verification.status is CitationStatus.PARTIAL_FRAGMENTS
    assert summary["total_citations"] == 2
    assert summary["verified_citations"] == 1
    assert summary["verification_rate"] == 0.5
    assert summary["status_counts"] == {
        "partial_fragments": 1,
        "verified_declared_page": 1,
    }
    cause_counts = summary["cause_counts"]
    assert isinstance(cause_counts, dict)
    assert cause_counts["partial_fragments"] == 1


def test_informe_markdown_incluye_umbral_y_distribucion() -> None:
    summary = {
        "total_citations": 4,
        "verified_citations": 3,
        "verification_rate": 0.75,
        "status_counts": {
            "verified_declared_page": 2,
            "verified_adjacent_page": 1,
            "not_found": 1,
        },
        "cause_counts": {
            "ellipsis": 1,
            "fuzzy": 2,
            "wrong_page": 1,
            "partial_fragments": 0,
            "extraction_defect": 0,
            "unresolved": 1,
            "invalid_declared_page": 0,
            "processing_error": 0,
        },
    }

    markdown = render_markdown_report(
        summary=summary,
        threshold=85,
        source_jsonl="output/analisis.jsonl",
        threshold_summaries={80.0: summary, 85.0: summary},
    )

    assert "# Spike de verificación de citas" in markdown
    assert "Umbral seleccionado | 85" in markdown
    assert "75,0 %" in markdown
    assert "| 80 | 3 | 75,0 % |" in markdown
    assert "not_found" in markdown
