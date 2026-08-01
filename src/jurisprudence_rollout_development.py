"""Banco de desarrollo sintético, separado del holdout histórico congelado."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Literal

from jurisprudence_case_catalogs import JurisprudenceCaseModel
from jurisprudence_case_derivative_artifacts import write_case_derivative
from jurisprudence_retrieval_corpus import _tokens, rank_retrieval_units
from jurisprudence_retrieval_corpus_models import RetrievalCorpus
from jurisprudence_rollout_evaluation import build_rollout_evaluation_bank
from jurisprudence_sample_evaluation import render_evaluation_bank
from jurisprudence_sample_evaluation_models import (
    RetrievalEvaluationBank,
    RetrievalEvaluationQuestion,
)


class RolloutDevelopmentReport(JurisprudenceCaseModel):
    schema_version: Literal["residenciafiscal-rollout-development/1"]
    evaluation_policy: Literal["DEVELOPMENT_ONLY_HOLDOUT_EXCLUDED"]
    evaluation_scope: Literal["EXPLICIT_JUDGMENT_LOOKUP"]
    question_count: int
    baseline_top_1_accuracy: float
    baseline_expected_recall_at_3: float
    candidate_top_1_accuracy: float
    candidate_expected_recall_at_3: float
    gate_status: Literal["PASSED", "FAILED"]


def _relative_resource(path: Path, project_root: Path) -> str:
    resolved = path.resolve()
    root = project_root.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("el manifiesto debe estar dentro de project_root")
    return resolved.relative_to(root).as_posix()


def _display_identifier(judgment_id: str) -> str:
    court, number, year = judgment_id.split("-")
    return f"{court.upper()} {number}/{year}"


def build_rollout_development_bank(
    *, manifest_path: Path, output_root: Path, project_root: Path
) -> RetrievalEvaluationBank:
    """Crea consultas de lookup inequívocas; no abre ni deriva datos del holdout."""

    source = build_rollout_evaluation_bank(
        manifest_path=manifest_path,
        output_root=output_root,
        project_root=project_root,
    )
    questions = tuple(
        RetrievalEvaluationQuestion(
            question_id=item.question_id,
            question=(
                f"En relación con {_display_identifier(item.expected_judgment_ids[0])}, "
                f"{item.question[0].lower()}{item.question[1:]}"
            ),
            behavior="responder",
            expected_judgment_ids=item.expected_judgment_ids,
            contrast_judgment_ids=(),
        )
        for item in source.questions
    )
    return RetrievalEvaluationBank(
        schema_version="residenciafiscal-retrieval-evaluation-bank/1",
        source_resource=_relative_resource(manifest_path, project_root),
        questions=questions,
    )


def _legacy_rank(corpus: RetrievalCorpus, query: str, limit: int) -> tuple[str, ...]:
    """Baseline TF-IDF anterior, conservado solo para comparar en desarrollo."""

    documents = tuple(Counter(_tokens(unit.search_text)) for unit in corpus.units)
    document_frequency = Counter(token for document in documents for token in document)
    query_counts = Counter(_tokens(query, expand=True))
    total = len(documents)
    scored = []
    for unit, document in zip(corpus.units, documents, strict=True):
        score = sum(
            min(query_frequency, document.get(token, 0))
            * (math.log((total + 1) / (document_frequency.get(token, 0) + 1)) + 1)
            for token, query_frequency in query_counts.items()
        )
        scored.append((score, unit.unit_id, unit.judgment_id))
    return tuple(item[2] for item in sorted(scored, key=lambda item: (-item[0], item[1]))[:limit])


def _metrics(
    bank: RetrievalEvaluationBank,
    ranker: Callable[[str], Sequence[str]],
) -> tuple[float, float]:
    top_1 = 0
    recall = 0.0
    for question in bank.questions:
        retrieved = tuple(dict.fromkeys(ranker(question.question)))
        expected = set(question.expected_judgment_ids)
        top_1 += bool(retrieved and retrieved[0] in expected)
        recall += len(expected & set(retrieved[:3])) / len(expected)
    count = len(bank.questions)
    return round(top_1 / count, 4), round(recall / count, 4)


def evaluate_rollout_development(
    *, bank: RetrievalEvaluationBank, corpus: RetrievalCorpus
) -> RolloutDevelopmentReport:
    baseline_top_1, baseline_recall = _metrics(bank, lambda query: _legacy_rank(corpus, query, 3))
    candidate_top_1, candidate_recall = _metrics(
        bank,
        lambda query: tuple(
            hit.judgment_id for hit in rank_retrieval_units(corpus, query, limit=3)
        ),
    )
    passed = candidate_top_1 >= 0.95 and candidate_recall >= baseline_recall
    return RolloutDevelopmentReport(
        schema_version="residenciafiscal-rollout-development/1",
        evaluation_policy="DEVELOPMENT_ONLY_HOLDOUT_EXCLUDED",
        evaluation_scope="EXPLICIT_JUDGMENT_LOOKUP",
        question_count=len(bank.questions),
        baseline_top_1_accuracy=baseline_top_1,
        baseline_expected_recall_at_3=baseline_recall,
        candidate_top_1_accuracy=candidate_top_1,
        candidate_expected_recall_at_3=candidate_recall,
        gate_status="PASSED" if passed else "FAILED",
    )


def _render(model: JurisprudenceCaseModel) -> str:
    return (
        json.dumps(model.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evalúa lookup por sentencia sin usar holdout.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    from jurisprudence_retrieval_corpus import load_retrieval_corpus

    bank = build_rollout_development_bank(
        manifest_path=args.manifest,
        output_root=args.output_root,
        project_root=args.project_root,
    )
    report = evaluate_rollout_development(
        bank=bank, corpus=load_retrieval_corpus(args.corpus.read_bytes())
    )
    write_case_derivative(render_evaluation_bank(bank), args.bank)
    write_case_derivative(_render(report), args.report)
    print(_render(report), end="")
    return 0 if report.gate_status == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
