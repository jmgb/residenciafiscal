"""Banco y métricas técnicas para el corpus ampliado."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from jurisprudence_case_derivative_artifacts import write_case_derivative
from jurisprudence_case_question_evaluation import CaseQuestionEvaluation
from jurisprudence_case_retrieval import load_retrieval_index
from jurisprudence_retrieval_corpus import load_retrieval_corpus
from jurisprudence_rollout import load_rollout_manifest
from jurisprudence_rollout_completion import rollout_corpus_path
from jurisprudence_sample_evaluation import (
    evaluate_question_bank,
    render_evaluation_bank,
    render_evaluation_report,
)
from jurisprudence_sample_evaluation_models import (
    RetrievalEvaluationBank,
    RetrievalEvaluationQuestion,
)


@dataclass(frozen=True)
class RolloutEvaluationResult:
    question_count: int
    expected_recall_at_5: float
    expected_recall_at_12: float
    bank_path: Path
    report_path: Path


def build_rollout_evaluation_bank(
    *,
    manifest_path: Path,
    output_root: Path,
    project_root: Path,
) -> RetrievalEvaluationBank:
    """Une evaluaciones por sentencia y omite documentos fuera de alcance."""

    manifest = load_rollout_manifest(manifest_path)
    questions: list[RetrievalEvaluationQuestion] = []
    for document in manifest.documents:
        index_path = output_root / f"retrieval/{document.judgment_id}.issues.json"
        index = load_retrieval_index(index_path.read_bytes())
        if not index.judgment.is_tax_residence_case:
            continue
        evaluation_path = (project_root / document.evaluation_path).resolve()
        evaluation = CaseQuestionEvaluation.model_validate_json(evaluation_path.read_bytes())
        questions.extend(
            RetrievalEvaluationQuestion(
                question_id=f"{document.judgment_id}-{item.question_id.lower()}",
                question=item.question,
                behavior="responder",
                expected_judgment_ids=(document.judgment_id,),
                contrast_judgment_ids=(),
            )
            for item in evaluation.questions
        )
    return RetrievalEvaluationBank(
        schema_version="residenciafiscal-retrieval-evaluation-bank/1",
        source_resource=manifest_path.as_posix(),
        questions=tuple(questions),
    )


def export_rollout_evaluation(
    *,
    manifest_path: Path,
    output_root: Path,
    bank_path: Path,
    report_path: Path,
    project_root: Path,
) -> RolloutEvaluationResult:
    """Mide cobertura del rollout sin reutilizar el gate congelado de cinco."""

    manifest = load_rollout_manifest(manifest_path)
    bank = build_rollout_evaluation_bank(
        manifest_path=manifest_path,
        output_root=output_root,
        project_root=project_root,
    )
    corpus = load_retrieval_corpus(
        rollout_corpus_path(output_root, len(manifest.documents)).read_bytes()
    )
    report = evaluate_question_bank(bank, corpus)
    write_case_derivative(render_evaluation_bank(bank), bank_path)
    write_case_derivative(render_evaluation_report(report), report_path)
    return RolloutEvaluationResult(
        question_count=report.question_count,
        expected_recall_at_5=report.expected_recall_at_5,
        expected_recall_at_12=report.expected_recall_at_12,
        bank_path=bank_path,
        report_path=report_path,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evalúa la recuperación del rollout completo.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    result = export_rollout_evaluation(
        manifest_path=args.manifest,
        output_root=args.output_root,
        bank_path=args.bank,
        report_path=args.report,
        project_root=args.project_root,
    )
    print(
        json.dumps(
            {
                "questions": result.question_count,
                "expected_recall_at_5": result.expected_recall_at_5,
                "expected_recall_at_12": result.expected_recall_at_12,
                "bank": str(result.bank_path),
                "report": str(result.report_path),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
