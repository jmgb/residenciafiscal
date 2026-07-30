"""Renderizado OKF v3 desde el caso jurisprudencial canónico."""

from __future__ import annotations

import yaml

from jurisprudence_case_models import JurisprudenceCase
from jurisprudence_case_okf_sections import render_issue_section
from jurisprudence_case_retrieval import build_retrieval_index

GENERATOR_ID = "residenciafiscal-case-renderer/0.1.0"


def _frontmatter(
    case: JurisprudenceCase,
    *,
    case_resource: str,
    case_sha256: str,
    pdf_resource: str,
    verbatim_resource: str,
) -> dict[str, object]:
    judgment = case.judgment
    criteria = tuple(
        dict.fromkeys(criterion for issue in case.legal_issues for criterion in issue.criterion_ids)
    )
    holdings_by_id = {holding.holding_id: holding for holding in case.holdings}
    outcomes = {
        issue.issue_id: holdings_by_id[issue.holding_id].outcome for issue in case.legal_issues
    }
    return {
        "type": "Sentencia fiscal",
        "title": judgment.roj,
        "description": (
            f"{len(case.legal_issues)} cuestiones jurídicas estructuradas; "
            "hechos, pruebas, valoración y resultado por cuestión."
        ),
        "resource": pdf_resource,
        "tags": ["residencia-fiscal", *(str(item).lower() for item in criteria)],
        "status": "stable" if str(case.review.legal) == "HUMAN_APPROVED" else "draft",
        "schema_version": "residenciafiscal-okf/3",
        "case_schema_version": case.schema_version,
        "case_resource": case_resource,
        "case_sha256": case_sha256,
        "verbatim_resource": verbatim_resource,
        "source_sha256": judgment.source_sha256,
        "roj": judgment.roj,
        "ecli": judgment.ecli,
        "organo": judgment.court,
        "sala": judgment.chamber,
        "fecha_resolucion": judgment.decision_date.isoformat(),
        "ejercicios_afectados": list(judgment.tax_years),
        "paises": list(judgment.countries),
        "criterios_detectados": [str(item) for item in criteria],
        "resultados_por_cuestion": {
            issue_id: str(outcome) for issue_id, outcome in outcomes.items()
        },
        "technical_review": str(case.review.technical),
        "legal_review": str(case.review.legal),
        "sources": [
            {
                "id": "sentencia-original",
                "resource": pdf_resource,
                "author": "CENDOJ/official",
            },
            {"id": "caso-v3", "resource": case_resource, "author": GENERATOR_ID},
            {
                "id": "verbatim-v1",
                "resource": verbatim_resource,
                "author": GENERATOR_ID,
            },
        ],
        "generated": {"by": GENERATOR_ID},
    }


def render_case_okf_markdown(
    case: JurisprudenceCase,
    *,
    case_resource: str,
    case_sha256: str,
    pdf_resource: str,
    verbatim_resource: str,
) -> str:
    """Renderiza una ficha legible sin volver a interpretar la sentencia."""

    frontmatter = yaml.safe_dump(
        _frontmatter(
            case,
            case_resource=case_resource,
            case_sha256=case_sha256,
            pdf_resource=pdf_resource,
            verbatim_resource=verbatim_resource,
        ),
        allow_unicode=True,
        sort_keys=False,
    ).strip()
    retrieval = build_retrieval_index(
        case,
        case_resource=case_resource,
        case_sha256=case_sha256,
    )
    lines = [
        "---",
        frontmatter,
        "---",
        "",
        "**Regla de lectura:** hechos, valoraciones y conclusiones son análisis "
        "jurídico estructurado. Solo el contenido dentro de bloques marcados como "
        "anclajes literales reproduce texto extraído de la sentencia.",
        "",
        "# Identidad y alcance",
        "",
        f"- Resolución: `{case.judgment.roj}` / `{case.judgment.ecli}`.",
        f"- Órgano: {case.judgment.court}.",
        f"- Ejercicios: {', '.join(map(str, case.judgment.tax_years))}.",
        f"- Países: {', '.join(case.judgment.countries)}.",
        "",
        "# Cuestiones jurídicas",
        "",
    ]
    for unit in retrieval.units:
        lines.extend([*render_issue_section(unit), ""])
    lines.extend(
        [
            "# Revisión y procedencia",
            "",
            f"- Estado técnico global: `{case.review.technical}`.",
            f"- Estado jurídico global: `{case.review.legal}`.",
            f"- Caso canónico: `{case_sha256}`.",
            f"- PDF: `{case.judgment.source_sha256}`.",
            "- Pendiente de aprobación jurídica humana.",
            "- Este perfil no predice el resultado de otros casos.",
            "",
        ]
    )
    return "\n".join(lines)
