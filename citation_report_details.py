"""Detalle Markdown por cita para el informe del spike."""

from __future__ import annotations

from collections.abc import Sequence

from citation_spike import CitationFinding


def append_finding_details(lines: list[str], findings: Sequence[CitationFinding]) -> None:
    """Añade resultados y puntuaciones por fragmento a un informe Markdown."""

    if not findings:
        return

    lines.extend(
        [
            "",
            "## Detalle por cita",
            "",
            "> Resultado de una muestra acotada; no fija por sí solo el gate del corpus.",
        ]
    )
    for finding in findings:
        candidate = finding.candidate
        verification = finding.verification
        evidence_status = verification.evidence_status.value if verification else "processing_error"
        literal_fidelity = verification.literal_fidelity.value if verification else "unverified"
        score = f"{verification.score:g}" if verification else "—"
        matched_pdf_pages = (
            ", ".join(str(page) for page in verification.matched_pdf_page_indexes)
            if verification and verification.matched_pdf_page_indexes
            else "—"
        )
        printed_labels = (
            ", ".join(verification.matched_printed_page_labels)
            if verification and verification.matched_printed_page_labels
            else "—"
        )
        lines.extend(
            [
                "",
                f"### Cita {candidate.citation_index + 1} — {candidate.topic or 'sin tema'}",
                "",
                f"- Evidencia: `{evidence_status}`",
                f"- Fidelidad literal: `{literal_fidelity}`",
                f"- Puntuación: {score}",
                f"- Índice PDF declarado: {candidate.declared_page}",
                f"- Índices PDF encontrados: {matched_pdf_pages}",
                f"- Etiquetas impresas encontradas: {printed_labels}",
                f"- Texto: {candidate.quote}",
            ]
        )
        if not verification or not verification.fragment_matches:
            continue
        lines.extend(
            [
                "",
                "| Fragmento normalizado | Puntuación | Índice PDF | Etiqueta impresa | Exacto |",
                "|---|---:|---:|---:|:---:|",
            ]
        )
        for match in verification.fragment_matches:
            fragment = match.fragment.replace("|", r"\|")
            page = match.pdf_page_index if match.pdf_page_index is not None else "—"
            printed = match.printed_page_label or "—"
            exact = "sí" if match.exact else "no"
            lines.append(f"| {fragment} | {match.score:g} | {page} | {printed} | {exact} |")
