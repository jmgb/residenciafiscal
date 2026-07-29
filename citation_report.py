"""Agregación y presentación de resultados del spike de citas."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from typing import SupportsFloat, cast

from citation_report_details import append_finding_details
from citation_spike import VERIFIED_STATUSES, CitationFinding
from citation_verification import CitationStatus, split_citation_fragments


def summarize_findings(findings: Sequence[CitationFinding]) -> dict[str, object]:
    """Resume estados y causas directamente observables, sin inferencias jurídicas."""

    status_counts: Counter[str] = Counter()
    cause_counts: Counter[str] = Counter(
        {
            "ellipsis": 0,
            "fuzzy": 0,
            "wrong_page": 0,
            "partial_fragments": 0,
            "extraction_defect": 0,
            "unresolved": 0,
            "invalid_declared_page": 0,
            "processing_error": 0,
        }
    )
    verified_citations = 0

    for finding in findings:
        verification = finding.verification
        if verification is None:
            status_counts["processing_error"] += 1
            cause_counts["processing_error"] += 1
            continue

        status_counts[verification.status.value] += 1
        is_verified = verification.status in VERIFIED_STATUSES
        verified_citations += int(is_verified)
        cause_counts["ellipsis"] += int(
            is_verified and len(split_citation_fragments(finding.candidate.quote)) > 1
        )
        cause_counts["fuzzy"] += int(
            is_verified
            and any(match.matched and not match.exact for match in verification.fragment_matches)
        )
        cause_counts["wrong_page"] += int(
            verification.status
            in {CitationStatus.VERIFIED_ADJACENT_PAGE, CitationStatus.VERIFIED_OTHER_PAGE}
        )
        cause_counts["partial_fragments"] += int(
            verification.status is CitationStatus.PARTIAL_FRAGMENTS
        )
        cause_counts["extraction_defect"] += int(
            verification.status is CitationStatus.EXTRACTION_DEFECT
        )
        cause_counts["unresolved"] += int(verification.status is CitationStatus.NOT_FOUND)
        cause_counts["invalid_declared_page"] += int(not verification.declared_page_valid)

    total = len(findings)
    return {
        "total_citations": total,
        "verified_citations": verified_citations,
        "verification_rate": round(verified_citations / total, 4) if total else 0.0,
        "status_counts": dict(sorted(status_counts.items())),
        "cause_counts": dict(sorted(cause_counts.items())),
    }


def finding_to_dict(finding: CitationFinding) -> dict[str, object]:
    """Convierte un hallazgo a la forma estable del informe JSON."""

    candidate = finding.candidate
    verification = finding.verification
    base: dict[str, object] = {
        "source_file": candidate.source_file,
        "citation_index": candidate.citation_index,
        "topic": candidate.topic,
        "declared_page_raw": candidate.declared_page,
        "quote": candidate.quote,
        "error": finding.error,
    }
    if verification is None:
        return {
            **base,
            "status": "processing_error",
            "score": None,
            "declared_page": None,
            "declared_page_valid": False,
            "matched_pages": [],
            "matched_fragment_count": 0,
            "total_fragment_count": 0,
            "fragment_matches": [],
        }
    return {
        **base,
        "status": verification.status.value,
        "score": verification.score,
        "declared_page": verification.declared_page,
        "declared_page_valid": verification.declared_page_valid,
        "matched_pages": list(verification.matched_pages),
        "matched_fragment_count": verification.matched_fragment_count,
        "total_fragment_count": verification.total_fragment_count,
        "fragment_matches": [asdict(match) for match in verification.fragment_matches],
    }


def _format_percentage(value: object) -> str:
    numeric_value = float(cast(SupportsFloat, value))
    return f"{numeric_value * 100:.1f}".replace(".", ",") + " %"


def render_markdown_report(
    *,
    summary: Mapping[str, object],
    threshold: float,
    source_jsonl: str,
    threshold_summaries: Mapping[float, Mapping[str, object]],
    source_file: str | None = None,
    findings: Sequence[CitationFinding] = (),
) -> str:
    """Renderiza un informe compacto y apto para revisión humana."""

    lines = [
        "# Spike de verificación de citas",
        "",
        "## Configuración",
        "",
        "| Parámetro | Valor |",
        "|---|---:|",
        f"| JSONL fuente | `{source_jsonl}` |",
        f"| Sentencia | `{source_file}` |" if source_file else "| Sentencia | Todas |",
        f"| Umbral seleccionado | {threshold:g} |",
        f"| Citas analizadas | {summary['total_citations']} |",
        f"| Citas verificadas | {summary['verified_citations']} |",
        f"| Tasa de verificación | {_format_percentage(summary['verification_rate'])} |",
        "",
        "## Sensibilidad al umbral",
        "",
        "| Umbral | Verificadas | Tasa |",
        "|---:|---:|---:|",
    ]
    for candidate_threshold, candidate_summary in sorted(threshold_summaries.items()):
        lines.append(
            f"| {candidate_threshold:g} | {candidate_summary['verified_citations']} | "
            f"{_format_percentage(candidate_summary['verification_rate'])} |"
        )

    lines.extend(["", "## Distribución por estado", "", "| Estado | Citas |", "|---|---:|"])
    status_counts = cast(Mapping[str, object], summary["status_counts"])
    for status, count in status_counts.items():
        lines.append(f"| `{status}` | {count} |")

    lines.extend(["", "## Causas observables", "", "| Causa | Citas |", "|---|---:|"])
    cause_counts = cast(Mapping[str, object], summary["cause_counts"])
    for cause, count in cause_counts.items():
        lines.append(f"| `{cause}` | {count} |")

    append_finding_details(lines, findings)
    lines.append("")
    return "\n".join(lines)
