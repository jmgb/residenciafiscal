"""CLI para compilar y validar un caso jurisprudencial v3 sin LLM."""

from __future__ import annotations

import argparse
import json
import tempfile
from collections.abc import Sequence
from pathlib import Path

from jurisprudence_case_artifact import load_jurisprudence_case
from jurisprudence_case_compilation import build_case_artifact
from jurisprudence_case_question_evaluation import (
    CaseQuestionEvaluation,
    validate_question_evaluation,
)
from jurisprudence_case_verbatim_validation import (
    CaseArtifactValidationResult,
    validate_case_artifact,
)
from verbatim_validation import validate_verbatim_artifact


def _render_report(
    result: CaseArtifactValidationResult,
    *,
    case_path: Path,
    question_evaluation_count: int,
) -> str:
    case = load_jurisprudence_case(case_path.read_bytes())
    return (
        json.dumps(
            {
                "anchor_count": result.anchor_count,
                "case_sha256": result.case_sha256,
                "evidence_finding_count": len(case.evidence_findings),
                "fact_count": len(case.facts),
                "fragment_count": result.fragment_count,
                "holding_count": len(case.holdings),
                "input_artifact_count": result.input_artifact_count,
                "judgment_id": result.judgment_id,
                "legal_issue_count": len(case.legal_issues),
                "legal_review": case.review.legal,
                "question_evaluation_count": question_evaluation_count,
                "technical_review": case.review.technical,
                "validation": "passed",
                "verbatim_sha256": result.verbatim_sha256,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def export_jurisprudence_case(
    *,
    proposal_path: Path,
    verbatim_path: Path,
    evaluation_path: Path,
    output_path: Path,
    report_path: Path,
    project_root: Path,
) -> CaseArtifactValidationResult:
    """Compila en staging y publica solo después de validar todas las fuentes."""

    validate_verbatim_artifact(verbatim_path, project_root=project_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        dir=output_path.parent,
        prefix=f".{output_path.name}.",
    ) as staging_directory:
        candidate_path = Path(staging_directory) / output_path.name
        build_case_artifact(
            proposal_path,
            verbatim_path=verbatim_path,
            project_root=project_root,
            destination=candidate_path,
        )
        result = validate_case_artifact(
            candidate_path,
            verbatim_path=verbatim_path,
            project_root=project_root,
        )
        case = load_jurisprudence_case(candidate_path.read_bytes())
        evaluation = CaseQuestionEvaluation.model_validate_json(evaluation_path.read_bytes())
        question_result = validate_question_evaluation(evaluation, case)
        report = _render_report(
            result,
            case_path=candidate_path,
            question_evaluation_count=question_result.question_count,
        )
        candidate_path.replace(output_path)

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=report_path.parent,
        prefix=f".{report_path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary:
        temporary.write(report)
        temporary_path = Path(temporary.name)
    temporary_path.replace(report_path)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compila una propuesta híbrida y valida el caso v3.",
    )
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--verbatim", type=Path, required=True)
    parser.add_argument("--evaluation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = export_jurisprudence_case(
        proposal_path=args.proposal,
        verbatim_path=args.verbatim,
        evaluation_path=args.evaluation,
        output_path=args.output,
        report_path=args.report,
        project_root=args.project_root,
    )
    print(
        json.dumps(
            {
                "artifact": str(args.output),
                "case_sha256": result.case_sha256,
                "judgment_id": result.judgment_id,
                "report": str(args.report),
                "validation": "passed",
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
