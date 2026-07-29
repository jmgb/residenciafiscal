"""Secciones repetitivas del cuerpo Markdown de una sentencia OKF."""

from __future__ import annotations

from collections.abc import Sequence

from citation_models import CitationVerification
from okf_models import OkfEvidence, OkfJudgment


def _cell(value: object) -> str:
    return str(value).replace("\n", " ").replace("|", r"\|").strip()


def render_evidence_table(title: str, items: Sequence[OkfEvidence]) -> list[str]:
    """Renderiza pruebas procesales sin convertir sus resúmenes en citas."""

    lines = [
        f"## {title}",
        "",
        "| ID | Prueba | Categoría | Criterio | Valor de origen | Valoración | Peso |",
        "|---|---|---|---|---|---|---:|",
    ]
    if not items:
        lines.append("| — | No constan pruebas estructuradas. | — | — | — | — | — |")
        return lines
    lines.extend(
        f"| `{item.id}` | {_cell(item.subcategoria)} | `{item.categoria}` | "
        f"`{item.criterio_atacado}` | `{item.source_criterion_atacado}` | "
        f"`{item.aceptada}`: "
        f"{_cell(item.motivo_valoracion)} | {item.peso} |"
        for item in items
    )
    return lines


def render_position(items: Sequence[OkfEvidence]) -> list[str]:
    """Expone los objetivos probatorios atribuidos a una parte, sin resumirlos de nuevo."""

    if not items:
        return ["No constan objetivos probatorios estructurados."]
    return list(dict.fromkeys(f"- {_cell(item.objetivo_probatorio)}" for item in items))


def render_citation_sections(
    judgment: OkfJudgment,
    verifications: Sequence[CitationVerification],
) -> list[str]:
    """Separa citas literales de entradas que requieren revisión."""

    lines = ["# Citas literales verificadas", ""]
    literal_indexes = [
        index
        for index, verification in enumerate(verifications)
        if verification.publishable_literal
    ]
    if not literal_indexes:
        lines.append("No hay citas que superen el criterio de literalidad.")
    for index in literal_indexes:
        verification = verifications[index]
        pages = ", ".join(map(str, verification.matched_pdf_page_indexes))
        labels = ", ".join(verification.matched_printed_page_labels) or "no detectada"
        excerpt = " […] ".join(verification.source_fragments_verbatim)
        lines.extend(f"> {line}" for line in excerpt.splitlines())
        lines.extend(
            [
                ">",
                f"> Índice PDF {pages}; etiqueta impresa {labels}; "
                f"`{verification.literal_fidelity.value}`; puntuación "
                f"{verification.score:g}/100.[^sentencia-original]",
                "",
            ]
        )

    lines.extend(["# Citas pendientes de revisión", ""])
    pending_indexes = [index for index in range(len(verifications)) if index not in literal_indexes]
    if not pending_indexes:
        lines.append("No hay citas pendientes de revisión.")
    for index in pending_indexes:
        citation = judgment.citas[index]
        verification = verifications[index]
        lines.append(
            f"- **Texto del análisis; no es una cita literal** "
            f"(`{verification.evidence_status.value}`, "
            f"`{verification.literal_fidelity.value}`, {verification.score:g}/100): "
            f"{citation.analysis_quote}"
        )
    lines.extend(["", "# Trazabilidad de citas", ""])
    lines.extend(
        [
            "| ID | Propietario | Campo de origen | Evidencia | Fidelidad | "
            "Puntuación | Índices PDF |",
            "|---|---|---|---|---|---:|---|",
        ]
    )
    for citation, verification in zip(judgment.citas, verifications, strict=True):
        pages = ", ".join(map(str, verification.matched_pdf_page_indexes)) or "—"
        lines.append(
            f"| `{citation.id}` | `{citation.owner_id}` | `{citation.source_field}` | "
            f"`{verification.evidence_status.value}` | "
            f"`{verification.literal_fidelity.value}` | {verification.score:g} | "
            f"{pages} |"
        )
    return lines
