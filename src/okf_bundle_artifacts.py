"""Índices y manifiesto deterministas del bundle jurisprudencial."""

from __future__ import annotations

from pathlib import Path


def render_root_index() -> str:
    """Genera el índice raíz con la versión OKF declarada."""

    return """---
okf_version: "0.2"
---

# Corpus jurisprudencial de residencia fiscal

* [Sentencias](sentencias/) - Resoluciones normalizadas y conectadas con su PDF original.
"""


def render_judgments_index(title: str, slug: str, description: str) -> str:
    """Genera el índice de sentencias para divulgación progresiva."""

    return f"# Sentencias sobre residencia fiscal\n\n* [{title}]({slug}.md) - {description}\n"


def build_manifest(
    *,
    jsonl_path: Path,
    analysis_sha256: str,
    analysis_provenance: dict[str, object],
    source_record_path: Path,
    source_record_sha256: str,
    pdf_path: Path,
    pdf_sha256: str,
    extractor: str,
    page_count: int,
    document_path: Path,
    document_sha256: str,
    status: str,
    literal_count: int,
    pending_count: int,
    warnings: tuple[str, ...],
    annotation_path: Path | None,
    annotation_sha256: str | None,
    approved_issues: int,
    proposed_issues: int,
    verification_report_path: Path,
    verification_report_sha256: str,
) -> dict[str, object]:
    """Construye el manifiesto de fuentes y derivados sin leer el reloj."""

    return {
        "schema_version": "residenciafiscal-okf-manifest/2",
        "okf_version": "0.2",
        "scope": {"documents": 1, "source_files": [pdf_path.name]},
        "analysis_source": {
            "path": jsonl_path.as_posix(),
            "sha256": analysis_sha256,
        },
        "analysis_record": {
            "path": source_record_path.as_posix(),
            "sha256": source_record_sha256,
        },
        "analysis_provenance": analysis_provenance,
        "annotations_source": (
            {
                "path": annotation_path.as_posix(),
                "sha256": annotation_sha256,
            }
            if annotation_path is not None
            else None
        ),
        "pdf_sources": [
            {
                "archivo": pdf_path.name,
                "sha256": pdf_sha256,
                "size_bytes": pdf_path.stat().st_size,
                "pages": page_count,
                "extractor": extractor,
            }
        ],
        "documents": [
            {
                "concept_id": f"sentencias/{document_path.stem}",
                "path": document_path.as_posix(),
                "sha256": document_sha256,
                "status": status,
                "literal_citations": literal_count,
                "pending_citations": pending_count,
                "legal_issues": {
                    "approved": approved_issues,
                    "proposed": proposed_issues,
                },
                "verification_report": {
                    "path": verification_report_path.as_posix(),
                    "sha256": verification_report_sha256,
                },
                "normalization_warnings": list(warnings),
            }
        ],
    }
