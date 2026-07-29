"""Renderizado de sidecars sin mezclarlos con el texto fuente."""

from __future__ import annotations

from okf_annotations import AnnotationCorrection, JudgmentAnnotations, LegalIssue


def _is_human_reviewed(item: AnnotationCorrection | LegalIssue) -> bool:
    return (
        item.status == "approved"
        and item.reviewed_by is not None
        and item.reviewed_by.startswith("human:")
    )


def annotation_quality(annotations: JudgmentAnnotations) -> dict[str, object]:
    """Resume revisión humana sin atribuírsela a procesos automáticos."""

    item_count = len(annotations.corrections) + len(annotations.issues)
    human_reviewed = (
        item_count > 0
        and all(_is_human_reviewed(item) for item in annotations.corrections)
        and all(_is_human_reviewed(item) for item in annotations.issues)
    )
    return {
        "human_reviewed": human_reviewed,
        "legal_issues": {
            "total": len(annotations.issues),
            "approved": sum(issue.status == "approved" for issue in annotations.issues),
            "proposed": sum(issue.status == "proposed" for issue in annotations.issues),
        },
    }


def render_annotation_sections(annotations: JudgmentAnnotations) -> list[str]:
    """Expone cuestiones y correcciones con su estado editorial explícito."""

    lines = ["# Resultado por cuestiones jurídicas", ""]
    if not annotations.issues:
        lines.append("No hay resultados desglosados por cuestión jurídica.")
    for issue in annotations.issues:
        citations = ", ".join(f"`{item}`" for item in issue.support_citation_ids) or "—"
        lines.extend(
            [
                f"## {issue.question}",
                "",
                f"- ID: `{issue.id}`.",
                f"- Resultado: `{issue.decision}`.",
                f"- Estado editorial: `{issue.status}`.",
                f"- Citas de apoyo: {citations}.",
                f"- Justificación derivada: {issue.rationale}",
                "",
            ]
        )
        for anchor in issue.source_anchors:
            lines.extend(
                [
                    *(f"> {line}" for line in anchor.source_excerpt_verbatim.splitlines()),
                    ">",
                    f"> Índice PDF {anchor.pdf_page_index}; extracto literal del PDF.",
                    "",
                ]
            )

    lines.extend(["# Anotaciones y correcciones", ""])
    if not annotations.corrections:
        lines.append("No hay correcciones propuestas ni aprobadas.")
    for correction in annotations.corrections:
        lines.extend(
            [
                f"- `{correction.status}` — `{correction.target_id}.{correction.field}`: "
                f"`{correction.source_value}` → `{correction.replacement}`. "
                f"{correction.rationale}",
            ]
        )
    return lines
