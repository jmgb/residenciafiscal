"""Agregación y presentación de resultados del spike de citas."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from typing import SupportsFloat, cast

from citation_models import EvidenceStatus, LiteralFidelity
from citation_report_details import append_finding_details
from citation_spike import FOUND_EVIDENCE_STATUSES, CitationFinding
from citation_verification import split_citation_fragments

LITERAL_FIDELITIES = frozenset({LiteralFidelity.EXACT, LiteralFidelity.EXACT_WITH_ELLIPSIS})


def summarize_findings(findings: Sequence[CitationFinding]) -> dict[str, object]:
    """Resume estados y causas directamente observables, sin inferencias jurídicas."""

    evidence_status_counts: Counter[str] = Counter()
    literal_fidelity_counts: Counter[str] = Counter()
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
    located_citations = 0
    literal_citations = 0

    for finding in findings:
        verification = finding.verification
        if verification is None:
            evidence_status_counts["processing_error"] += 1
            literal_fidelity_counts[LiteralFidelity.UNVERIFIED.value] += 1
            cause_counts["processing_error"] += 1
            continue

        evidence_status_counts[verification.evidence_status.value] += 1
        literal_fidelity_counts[verification.literal_fidelity.value] += 1
        is_located = verification.evidence_status in FOUND_EVIDENCE_STATUSES
        is_literal = verification.literal_fidelity in LITERAL_FIDELITIES
        located_citations += int(is_located)
        literal_citations += int(is_literal)
        cause_counts["ellipsis"] += int(
            is_located and len(split_citation_fragments(finding.candidate.quote)) > 1
        )
        cause_counts["fuzzy"] += int(
            verification.literal_fidelity is LiteralFidelity.FUZZY_CANDIDATE
        )
        cause_counts["wrong_page"] += int(
            verification.evidence_status
            in {EvidenceStatus.FOUND_ADJACENT_PAGE, EvidenceStatus.FOUND_OTHER_PAGE}
        )
        cause_counts["partial_fragments"] += int(
            verification.evidence_status is EvidenceStatus.PARTIAL_FRAGMENTS
        )
        cause_counts["extraction_defect"] += int(
            verification.evidence_status is EvidenceStatus.EXTRACTION_DEFECT
        )
        cause_counts["unresolved"] += int(verification.evidence_status is EvidenceStatus.NOT_FOUND)
        cause_counts["invalid_declared_page"] += int(not verification.declared_page_valid)

    total = len(findings)
    return {
        "total_citations": total,
        "located_citations": located_citations,
        "literal_citations": literal_citations,
        "location_rate": round(located_citations / total, 4) if total else 0.0,
        "literal_rate": round(literal_citations / total, 4) if total else 0.0,
        "evidence_status_counts": dict(sorted(evidence_status_counts.items())),
        "literal_fidelity_counts": dict(sorted(literal_fidelity_counts.items())),
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
            "evidence_found": False,
            "evidence_status": "processing_error",
            "literal_fidelity": LiteralFidelity.UNVERIFIED.value,
            "score": None,
            "declared_pdf_page_index": None,
            "declared_page_valid": False,
            "matched_pdf_page_indexes": [],
            "matched_printed_page_labels": [],
            "matched_fragment_count": 0,
            "total_fragment_count": 0,
            "fragment_matches": [],
        }
    return {
        **base,
        "evidence_found": verification.evidence_found,
        "evidence_status": verification.evidence_status.value,
        "literal_fidelity": verification.literal_fidelity.value,
        "score": verification.score,
        "declared_pdf_page_index": verification.declared_pdf_page_index,
        "declared_page_valid": verification.declared_page_valid,
        "matched_pdf_page_indexes": list(verification.matched_pdf_page_indexes),
        "matched_printed_page_labels": list(verification.matched_printed_page_labels),
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
    source_files: Sequence[str] = (),
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
        _format_source_scope(source_files),
        f"| Umbral seleccionado | {threshold:g} |",
        f"| Citas analizadas | {summary['total_citations']} |",
        f"| Evidencias localizadas | {summary['located_citations']} |",
        f"| Tasa de localización | {_format_percentage(summary['location_rate'])} |",
        f"| Citas literales | {summary['literal_citations']} |",
        f"| Tasa literal | {_format_percentage(summary['literal_rate'])} |",
        "",
        "## Sensibilidad al umbral",
        "",
        "| Umbral | Localizadas | Tasa localización | Literales | Tasa literal |",
        "|---:|---:|---:|---:|---:|",
    ]
    for candidate_threshold, candidate_summary in sorted(threshold_summaries.items()):
        lines.append(
            f"| {candidate_threshold:g} | {candidate_summary['located_citations']} | "
            f"{_format_percentage(candidate_summary['location_rate'])} | "
            f"{candidate_summary['literal_citations']} | "
            f"{_format_percentage(candidate_summary['literal_rate'])} |"
        )

    lines.extend(["", "## Localización de evidencia", "", "| Estado | Citas |", "|---|---:|"])
    status_counts = cast(Mapping[str, object], summary["evidence_status_counts"])
    for status, count in status_counts.items():
        lines.append(f"| `{status}` | {count} |")

    lines.extend(["", "## Fidelidad literal", "", "| Fidelidad | Citas |", "|---|---:|"])
    fidelity_counts = cast(Mapping[str, object], summary["literal_fidelity_counts"])
    for fidelity, count in fidelity_counts.items():
        lines.append(f"| `{fidelity}` | {count} |")

    lines.extend(["", "## Causas observables", "", "| Causa | Citas |", "|---|---:|"])
    cause_counts = cast(Mapping[str, object], summary["cause_counts"])
    for cause, count in cause_counts.items():
        lines.append(f"| `{cause}` | {count} |")

    append_finding_details(lines, findings)
    lines.append("")
    return "\n".join(lines)


def _format_source_scope(source_files: Sequence[str]) -> str:
    if not source_files:
        return "| Sentencias | Todas |"
    joined_sources = ", ".join(f"`{source_file}`" for source_file in source_files)
    label = "Sentencia" if len(source_files) == 1 else "Sentencias"
    return f"| {label} | {joined_sources} |"
