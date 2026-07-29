"""Render OKF v3 derivado exclusivamente del caso canónico."""

from __future__ import annotations

from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CASE_PATH = PROJECT_ROOT / "knowledge/jurisprudencia/cases/san-1210-2023.case.json"


def _case():
    from jurisprudence_case_artifact import load_jurisprudence_case

    return load_jurisprudence_case(CASE_PATH.read_bytes())


def test_render_okf_v3_es_determinista_y_declara_su_fuente() -> None:
    from jurisprudence_case_okf_rendering import render_case_okf_markdown

    case = _case()
    first = render_case_okf_markdown(
        case,
        case_resource="../cases/san-1210-2023.case.json",
        case_sha256="a" * 64,
        pdf_resource="../../../sentencias/SAN_1210_2023.pdf",
        verbatim_resource="../verbatim/san-1210-2023.pages.json",
    )
    second = render_case_okf_markdown(
        case,
        case_resource="../cases/san-1210-2023.case.json",
        case_sha256="a" * 64,
        pdf_resource="../../../sentencias/SAN_1210_2023.pdf",
        verbatim_resource="../verbatim/san-1210-2023.pages.json",
    )
    frontmatter = yaml.safe_load(first.split("---", 2)[1])

    assert first == second
    assert frontmatter["type"] == "Sentencia fiscal"
    assert frontmatter["schema_version"] == "residenciafiscal-okf/3"
    assert frontmatter["case_schema_version"] == "residenciafiscal-case/3"
    assert frontmatter["case_sha256"] == "a" * 64
    assert frontmatter["legal_review"] == "AGENT_REVIEWED"
    assert frontmatter["status"] == "draft"
    assert "analysis.json" not in first


def test_render_incluye_cada_cuestion_y_cada_anclaje_literal() -> None:
    from jurisprudence_case_okf_rendering import render_case_okf_markdown

    case = _case()
    rendered = render_case_okf_markdown(
        case,
        case_resource="../cases/san-1210-2023.case.json",
        case_sha256="a" * 64,
        pdf_resource="../../../sentencias/SAN_1210_2023.pdf",
        verbatim_resource="../verbatim/san-1210-2023.pages.json",
    )

    for issue in case.legal_issues:
        assert f"## {issue.question}" in rendered
    for anchor in case.source_anchors:
        assert f"`{anchor.anchor_id}`" in rendered
        for fragment in anchor.fragments:
            assert fragment.verbatim_text in rendered
    assert "Pendiente de aprobación jurídica humana" in rendered


def test_resultados_frontmatter_se_resuelven_por_id_no_por_posicion() -> None:
    from jurisprudence_case_okf_rendering import render_case_okf_markdown

    case = _case()
    changed_residence = case.holdings[0].model_copy(update={"outcome": "GANA_CONTRIBUYENTE"})
    reordered = case.model_copy(
        update={
            "holdings": (
                case.holdings[2],
                case.holdings[1],
                changed_residence,
            )
        }
    )
    rendered = render_case_okf_markdown(
        reordered,
        case_resource="../cases/san-1210-2023.case.json",
        case_sha256="a" * 64,
        pdf_resource="../../../sentencias/SAN_1210_2023.pdf",
        verbatim_resource="../verbatim/san-1210-2023.pages.json",
    )
    frontmatter = yaml.safe_load(rendered.split("---", 2)[1])

    assert frontmatter["resultados_por_cuestion"]["residencia-fiscal"] == "GANA_CONTRIBUYENTE"
