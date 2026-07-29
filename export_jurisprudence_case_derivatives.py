"""CLI para publicar los derivados B4 de un caso jurisprudencial v3."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Sequence
from pathlib import Path

from jurisprudence_case_artifact import load_jurisprudence_case
from jurisprudence_case_derivative_artifacts import write_case_derivative
from jurisprudence_case_derivative_validation import (
    DerivativeValidationResult,
    validate_case_derivatives,
)
from jurisprudence_case_okf_rendering import render_case_okf_markdown
from jurisprudence_case_retrieval import (
    build_retrieval_index,
    render_retrieval_index,
)
from jurisprudence_case_verbatim_validation import validate_case_artifact
from okf_provenance import sha256_file
from verbatim_validation import validate_verbatim_artifact


def _relative_resource(source: Path, destination_dir: Path) -> str:
    return Path(os.path.relpath(source.resolve(), destination_dir.resolve())).as_posix()


def _render_report(
    result: DerivativeValidationResult,
    *,
    case_sha256: str,
    verbatim_sha256: str,
) -> str:
    return (
        json.dumps(
            {
                "case_sha256": case_sha256,
                "judgment_id": result.judgment_id,
                "legal_issue_count": result.legal_issue_count,
                "literal_anchor_count": result.literal_anchor_count,
                "literal_fragment_count": result.literal_fragment_count,
                "markdown_sha256": result.markdown_sha256,
                "retrieval_sha256": result.retrieval_sha256,
                "retrieval_unit_count": result.retrieval_unit_count,
                "validation": "passed",
                "verbatim_sha256": verbatim_sha256,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def export_case_derivatives(
    *,
    case_path: Path,
    verbatim_path: Path,
    markdown_path: Path,
    retrieval_path: Path,
    report_path: Path,
    project_root: Path,
) -> DerivativeValidationResult:
    """Revalida fuentes, proyecta el caso y publica tres artefactos."""

    verbatim_result = validate_verbatim_artifact(
        verbatim_path,
        project_root=project_root,
    )
    validate_case_artifact(
        case_path,
        verbatim_path=verbatim_path,
        project_root=project_root,
    )
    case = load_jurisprudence_case(case_path.read_bytes())
    case_sha256 = sha256_file(case_path)
    pdf_path = project_root / case.judgment.source_file
    retrieval = build_retrieval_index(
        case,
        case_resource=_relative_resource(case_path, retrieval_path.parent),
        case_sha256=case_sha256,
    )
    serialized_retrieval = render_retrieval_index(retrieval)
    markdown = render_case_okf_markdown(
        case,
        case_resource=_relative_resource(case_path, markdown_path.parent),
        case_sha256=case_sha256,
        pdf_resource=_relative_resource(pdf_path, markdown_path.parent),
        verbatim_resource=_relative_resource(
            verbatim_path,
            markdown_path.parent,
        ),
    )
    result = validate_case_derivatives(
        case,
        case_sha256=case_sha256,
        markdown=markdown,
        retrieval=retrieval,
        serialized_retrieval=serialized_retrieval,
    )
    report = _render_report(
        result,
        case_sha256=case_sha256,
        verbatim_sha256=verbatim_result.artifact_sha256,
    )
    write_case_derivative(markdown, markdown_path)
    write_case_derivative(serialized_retrieval, retrieval_path)
    write_case_derivative(report, report_path)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deriva el perfil OKF y el índice por cuestión desde case/3.",
    )
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--verbatim", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    parser.add_argument("--retrieval", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = export_case_derivatives(
        case_path=args.case,
        verbatim_path=args.verbatim,
        markdown_path=args.markdown,
        retrieval_path=args.retrieval,
        report_path=args.report,
        project_root=args.project_root,
    )
    print(
        json.dumps(
            {
                "judgment_id": result.judgment_id,
                "markdown": str(args.markdown),
                "report": str(args.report),
                "retrieval": str(args.retrieval),
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
