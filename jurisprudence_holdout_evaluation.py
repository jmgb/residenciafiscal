"""Carga y primera medición del holdout E0 sin usarlo para ajustar."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from jurisprudence_case_derivative_artifacts import write_case_derivative
from jurisprudence_holdout_models import (
    HoldoutEvaluationReport,
    HoldoutLock,
    HoldoutQuestionResult,
)
from jurisprudence_phase_d_retrieval import retrieve_for_chat
from jurisprudence_retrieval_corpus import load_retrieval_corpus
from jurisprudence_sample_evaluation_models import RetrievalEvaluationBank
from okf_provenance import sha256_file


@dataclass(frozen=True)
class FrozenHoldout:
    lock: HoldoutLock
    bank: RetrievalEvaluationBank
    bank_path: Path


@dataclass(frozen=True)
class HoldoutExportResult:
    artifact_path: Path
    report: HoldoutEvaluationReport


def _resolve_resource(project_root: Path, resource: str) -> Path:
    root = project_root.resolve()
    path = (root / resource).resolve()
    if not path.is_relative_to(root):
        raise ValueError("bank_resource queda fuera de project_root")
    if not path.is_file():
        raise ValueError(f"bank_resource inexistente: {resource}")
    return path


def load_frozen_holdout(*, lock_path: Path, project_root: Path) -> FrozenHoldout:
    lock = HoldoutLock.model_validate_json(lock_path.read_bytes())
    bank_path = _resolve_resource(project_root, lock.bank_resource)
    if sha256_file(bank_path) != lock.bank_sha256:
        raise ValueError("bank_sha256 no coincide con el banco congelado")
    bank = RetrievalEvaluationBank.model_validate_json(bank_path.read_bytes())
    if len(bank.questions) != lock.question_count:
        raise ValueError("question_count no coincide con el banco congelado")
    return FrozenHoldout(lock=lock, bank=bank, bank_path=bank_path)


def _recall(expected: tuple[str, ...], retrieved: tuple[str, ...]) -> float | None:
    if not expected:
        return None
    return len(set(expected) & set(retrieved)) / len(set(expected))


def _mean(values: Sequence[float | None]) -> float:
    measured = [item for item in values if item is not None]
    return sum(measured) / len(measured) if measured else 1.0


def _evaluate(
    frozen: FrozenHoldout,
    *,
    corpus_path: Path,
    lock_path: Path,
) -> HoldoutEvaluationReport:
    corpus = load_retrieval_corpus(corpus_path.read_bytes())
    results = []
    expected_recalls = []
    contrast_recalls = []
    precisions = []
    behavior_correct = 0
    safety_expected = 0
    safety_correct = 0
    answerable_count = 0
    for question in frozen.bank.questions:
        retrieval = retrieve_for_chat(corpus, question.question, limit=3)
        retrieved = tuple(item.judgment_id for item in retrieval.hits)
        behavior_correct += retrieval.behavior == question.behavior
        if question.behavior in {"preguntar", "abstenerse"}:
            safety_expected += 1
            safety_correct += not retrieved
        else:
            answerable_count += 1
            expected_recalls.append(_recall(question.expected_judgment_ids, retrieved))
            contrast_recalls.append(_recall(question.contrast_judgment_ids, retrieved))
            relevant = set(question.expected_judgment_ids) | set(question.contrast_judgment_ids)
            if relevant and retrieved:
                precisions.append(len(relevant & set(retrieved)) / len(set(retrieved)))
        results.append(
            HoldoutQuestionResult(
                question_id=question.question_id,
                expected_behavior=question.behavior,
                predicted_behavior=retrieval.behavior,
                retrieved_judgment_ids=retrieved,
                expected_recall_at_3=_recall(question.expected_judgment_ids, retrieved),
                contrast_recall_at_3=_recall(question.contrast_judgment_ids, retrieved),
            )
        )
    return HoldoutEvaluationReport(
        schema_version="residenciafiscal-holdout-evaluation/1",
        evaluation_policy="OBSERVE_ONLY_NO_TUNING",
        status="RECORDED",
        sample_id=corpus.sample_id,
        lock_sha256=sha256_file(lock_path),
        bank_sha256=frozen.lock.bank_sha256,
        corpus_sha256=sha256_file(corpus_path),
        question_count=len(results),
        answerable_question_count=answerable_count,
        behavior_accuracy=behavior_correct / len(results),
        zero_source_safety=safety_correct / safety_expected if safety_expected else 1,
        expected_recall_at_3=_mean(expected_recalls),
        relevant_case_precision_at_3=_mean(precisions),
        contrast_recall_at_3=_mean(contrast_recalls),
        results=tuple(results),
    )


def export_holdout_evaluation(
    *,
    corpus_path: Path,
    lock_path: Path,
    output_path: Path,
    project_root: Path,
) -> HoldoutExportResult:
    frozen = load_frozen_holdout(lock_path=lock_path, project_root=project_root)
    report = _evaluate(frozen, corpus_path=corpus_path, lock_path=lock_path)
    payload = json.dumps(
        report.model_dump(mode="json"),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    write_case_derivative(payload + "\n", output_path)
    return HoldoutExportResult(artifact_path=output_path, report=report)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mide el holdout congelado de fase E0.")
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    result = export_holdout_evaluation(
        corpus_path=args.corpus,
        lock_path=args.lock,
        output_path=args.output,
        project_root=args.project_root,
    )
    print(
        json.dumps(
            {
                "artifact": str(result.artifact_path),
                "behavior_accuracy": result.report.behavior_accuracy,
                "contrast_recall_at_3": result.report.contrast_recall_at_3,
                "evaluation_policy": result.report.evaluation_policy,
                "expected_recall_at_3": result.report.expected_recall_at_3,
                "relevant_case_precision_at_3": (result.report.relevant_case_precision_at_3),
                "zero_source_safety": result.report.zero_source_safety,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
