"""Secciones Markdown del perfil OKF derivado del caso v3."""

from __future__ import annotations

from jurisprudence_case_retrieval_models import RetrievalUnit


def _cell(value: object) -> str:
    return str(value).replace("\n", " ").replace("|", r"\|").strip()


def _render_facts(unit: RetrievalUnit) -> list[str]:
    lines = ["### Hechos relevantes", ""]
    if not unit.facts:
        return [*lines, "No constan hechos estructurados para esta cuestión."]
    lines.extend(
        f"- `{item.fact_id}` — {_cell(item.description)} "
        f"(`{item.procedural_status}`, atribuido a `{item.asserted_by}`)."
        for item in unit.facts
    )
    return lines


def _render_evidence(unit: RetrievalUnit) -> list[str]:
    lines = [
        "### Pruebas valoradas",
        "",
        "| ID | Parte | Categoría | Valoración | Función | Prueba y motivo |",
        "|---|---|---|---|---|---|",
    ]
    if not unit.evidence_findings:
        return [*lines, "| — | — | — | — | — | No constan pruebas estructuradas. |"]
    lines.extend(
        f"| `{item.evidence_id}` | `{item.offered_by}` | `{item.category}` | "
        f"`{item.assessment}` | `{item.role}` | {_cell(item.description)} "
        f"**Motivo:** {_cell(item.assessment_reason or 'No consta valoración.')} |"
        for item in unit.evidence_findings
    )
    return lines


def _render_rules(unit: RetrievalUnit) -> list[str]:
    lines = ["### Normas y doctrina", ""]
    if not unit.legal_rules:
        return [*lines, "No constan reglas estructuradas para esta cuestión."]
    lines.extend(
        f"- `{item.legal_rule_id}` — **{_cell(item.citation)}**: {_cell(item.proposition)}"
        for item in unit.legal_rules
    )
    return lines


def _render_burden(unit: RetrievalUnit) -> list[str]:
    lines = ["### Carga de la prueba", ""]
    if not unit.burden_of_proof_steps:
        return [*lines, "No consta una secuencia de carga específica para esta cuestión."]
    lines.extend(
        f"{item.sequence}. `{item.initial_bearer}` — {_cell(item.fact_to_prove)} "
        f"**Conclusión:** {_cell(item.conclusion)}"
        for item in unit.burden_of_proof_steps
    )
    return lines


def _render_specialized_data(unit: RetrievalUnit) -> list[str]:
    lines = ["### Cronología y CDI", ""]
    if not unit.presence_events and not unit.presence_periods:
        lines.append("No consta un cómputo diario o periodo de presencia estructurado.")
    for event in unit.presence_events:
        lines.append(
            f"- Evento `{event.event_id}`: {event.event_date.isoformat()}, "
            f"{event.country}, `{event.event_type}`."
        )
    for period in unit.presence_periods:
        lines.append(
            f"- Periodo `{period.period_id}`: {period.country}, "
            f"`{period.classification}`, días: {period.day_count}."
        )
    if not unit.treaty_analyses:
        lines.append("No consta análisis de convenio para esta cuestión.")
    for treaty in unit.treaty_analyses:
        lines.append(f"- CDI `{treaty.treaty_analysis_id}`: {_cell(treaty.treaty_citation)}")
    return lines


def _render_holding(unit: RetrievalUnit) -> list[str]:
    holding = unit.holding
    lines = [
        "### Conclusión judicial estructurada",
        "",
        f"- Resultado: `{holding.outcome}`.",
        f"- Conclusión: {_cell(holding.conclusion)}",
        f"- Razonamiento decisivo: {_cell(holding.decisive_reasoning)}",
    ]
    lines.extend(f"- Consecuencia: {_cell(item)}" for item in holding.consequences)
    return lines


def _render_anchors(unit: RetrievalUnit) -> list[str]:
    lines = ["### Anclajes literales", ""]
    for anchor in unit.source_anchors:
        lines.extend(
            [
                f"#### `{anchor.anchor_id}`",
                "",
                f"Finalidad: `{anchor.purpose}`; fidelidad: `{anchor.fidelity}`.",
                "",
            ]
        )
        for index, fragment in enumerate(anchor.fragments):
            if index:
                lines.extend(["[…]", ""])
            lines.extend(
                [
                    "```text",
                    fragment.verbatim_text,
                    "```",
                    "",
                    f"Página física {fragment.page_index}; etiqueta impresa "
                    f"{fragment.printed_page or 'no consta'}; offsets "
                    f"{fragment.start_offset}:{fragment.end_offset}.",
                    "",
                ]
            )
    return lines


def render_issue_section(unit: RetrievalUnit) -> list[str]:
    """Renderiza una cuestión y todos sus datos relacionados."""

    issue = unit.issue
    return [
        f"## {issue.question}",
        "",
        f"- ID: `{issue.issue_id}`.",
        f"- Tipo: `{issue.issue_type}`.",
        f"- Criterios: {', '.join(f'`{item}`' for item in issue.criterion_ids) or 'ninguno'}.",
        f"- Estado técnico: `{issue.review.technical}`.",
        f"- Estado jurídico: `{issue.review.legal}`.",
        "",
        *_render_facts(unit),
        "",
        *_render_evidence(unit),
        "",
        *_render_rules(unit),
        "",
        *_render_burden(unit),
        "",
        *_render_specialized_data(unit),
        "",
        *_render_holding(unit),
        "",
        *_render_anchors(unit),
    ]
