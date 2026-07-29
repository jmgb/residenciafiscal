"""Export reproducible de los derivados B4 del caso piloto."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_exporta_markdown_indice_e_informe_sin_llm(tmp_path: Path) -> None:
    from export_jurisprudence_case_derivatives import export_case_derivatives
    from jurisprudence_case_retrieval import load_retrieval_index

    markdown_path = tmp_path / "sentencias" / "san-1210-2023.md"
    retrieval_path = tmp_path / "retrieval" / "san-1210-2023.issues.json"
    report_path = tmp_path / "reports" / "san-1210-2023.derivatives-validation.json"

    result = export_case_derivatives(
        case_path=PROJECT_ROOT / "knowledge/jurisprudencia/cases/san-1210-2023.case.json",
        verbatim_path=PROJECT_ROOT / "knowledge/jurisprudencia/verbatim/san-1210-2023.pages.json",
        markdown_path=markdown_path,
        retrieval_path=retrieval_path,
        report_path=report_path,
        project_root=PROJECT_ROOT,
    )

    retrieval = load_retrieval_index(retrieval_path.read_bytes())
    report = json.loads(report_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")
    frontmatter = yaml.safe_load(markdown.split("---", 2)[1])
    assert result.judgment_id == "san-1210-2023"
    assert len(retrieval.units) == 3
    assert report["validation"] == "passed"
    assert report["literal_anchor_count"] == 17
    assert report["retrieval_unit_count"] == 3
    for source in frontmatter["sources"]:
        assert (markdown_path.parent / source["resource"]).resolve().is_file()


def test_dos_exports_producen_los_mismos_bytes(tmp_path: Path) -> None:
    from export_jurisprudence_case_derivatives import export_case_derivatives

    arguments = {
        "case_path": PROJECT_ROOT / "knowledge/jurisprudencia/cases/san-1210-2023.case.json",
        "verbatim_path": PROJECT_ROOT
        / "knowledge/jurisprudencia/verbatim/san-1210-2023.pages.json",
        "markdown_path": tmp_path / "sentencias/san-1210-2023.md",
        "retrieval_path": tmp_path / "retrieval/san-1210-2023.issues.json",
        "report_path": tmp_path / "reports/san-1210-2023.derivatives-validation.json",
        "project_root": PROJECT_ROOT,
    }

    export_case_derivatives(**arguments)
    first = tuple(path.read_bytes() for path in arguments.values() if path.suffix != "")
    export_case_derivatives(**arguments)
    second = tuple(path.read_bytes() for path in arguments.values() if path.suffix != "")

    assert first == second
