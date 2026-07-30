"""Informe sidecar de trazabilidad de citas: datos para máquinas, fuera del Markdown."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from citation_models import CitationVerification
from okf_models import OkfJudgment

REPORT_SCHEMA_VERSION = "residenciafiscal-okf-verification/1"


def build_verification_report(
    judgment: OkfJudgment,
    verifications: Sequence[CitationVerification],
    *,
    threshold: float,
) -> dict[str, object]:
    """Construye la trazabilidad completa con IDs íntegros, una fila por cita."""

    if len(judgment.citas) != len(verifications):
        raise ValueError("Cada cita debe tener exactamente un resultado de verificación")
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "source_file": judgment.archivo,
        "concept_id": f"sentencias/{judgment.slug}",
        "threshold": threshold,
        "citas": [
            {
                "id": citation.id,
                "owner_id": citation.owner_id,
                "source_field": citation.source_field,
                "evidence_status": verification.evidence_status.value,
                "literal_fidelity": verification.literal_fidelity.value,
                "score": verification.score,
                "publishable_literal": verification.publishable_literal,
                "matched_pdf_page_indexes": list(verification.matched_pdf_page_indexes),
                "matched_printed_page_labels": list(verification.matched_printed_page_labels),
            }
            for citation, verification in zip(judgment.citas, verifications, strict=True)
        ],
    }


def write_verification_report(
    output_dir: Path,
    judgment: OkfJudgment,
    verifications: Sequence[CitationVerification],
    *,
    threshold: float,
) -> Path:
    """Escribe el informe técnico determinista fuera del Markdown jurídico."""

    report_path = output_dir / "reports" / f"{judgment.slug}.verification.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            build_verification_report(judgment, verifications, threshold=threshold),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return report_path
