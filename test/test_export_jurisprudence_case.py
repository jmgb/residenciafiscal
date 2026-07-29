"""Export reproducible del caso jurisprudencial v3 piloto."""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_exporta_compila_y_valida_el_caso_piloto(tmp_path: Path) -> None:
    from export_jurisprudence_case import export_jurisprudence_case

    output_path = tmp_path / "san-1210-2023.case.json"
    report_path = tmp_path / "san-1210-2023.validation.json"

    result = export_jurisprudence_case(
        proposal_path=PROJECT_ROOT
        / "knowledge/jurisprudence-case-proposals/san-1210-2023.proposal.json",
        verbatim_path=PROJECT_ROOT / "knowledge/jurisprudencia/verbatim/san-1210-2023.pages.json",
        evaluation_path=PROJECT_ROOT
        / "knowledge/jurisprudencia/evaluations/san-1210-2023.questions.json",
        output_path=output_path,
        report_path=report_path,
        project_root=PROJECT_ROOT,
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert result.judgment_id == "san-1210-2023"
    assert (
        output_path.read_bytes()
        == (PROJECT_ROOT / "knowledge/jurisprudencia/cases/san-1210-2023.case.json").read_bytes()
    )
    assert report["validation"] == "passed"
    assert report["anchor_count"] == 17
    assert report["legal_issue_count"] == 3
    assert report["question_evaluation_count"] == 18
