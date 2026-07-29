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
        status = verification.status.value if verification else "processing_error"
        score = f"{verification.score:g}" if verification else "—"
        matched_pages = (
            ", ".join(str(page) for page in verification.matched_pages)
            if verification and verification.matched_pages
            else "—"
        )
        lines.extend(
            [
                "",
                f"### Cita {candidate.citation_index + 1} — {candidate.topic or 'sin tema'}",
                "",
                f"- Estado: `{status}`",
                f"- Puntuación: {score}",
                f"- Página declarada: {candidate.declared_page}",
                f"- Páginas encontradas: {matched_pages}",
                f"- Texto: {candidate.quote}",
            ]
        )
        if not verification or not verification.fragment_matches:
            continue
        lines.extend(
            [
                "",
                "| Fragmento normalizado | Puntuación | Página | Exacto |",
                "|---|---:|---:|:---:|",
            ]
        )
        for match in verification.fragment_matches:
            fragment = match.fragment.replace("|", r"\|")
            page = match.page_number if match.page_number is not None else "—"
            exact = "sí" if match.exact else "no"
            lines.append(f"| {fragment} | {match.score:g} | {page} | {exact} |")
