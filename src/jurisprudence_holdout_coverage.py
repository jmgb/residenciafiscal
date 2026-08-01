"""Diagnóstico de cobertura de etiquetas del holdout sobre un corpus."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from jurisprudence_case_catalogs import JurisprudenceCaseModel
from jurisprudence_case_derivative_artifacts import write_case_derivative
from jurisprudence_retrieval_corpus import load_retrieval_corpus
from jurisprudence_retrieval_corpus_models import RetrievalCorpus
from jurisprudence_sample_evaluation_models import RetrievalEvaluationBank


class HoldoutCoverageAssessment(JurisprudenceCaseModel):
    schema_version: Literal["residenciafiscal-holdout-coverage/1"]
    metric_policy: Literal["FULL_CORPUS_PRECISION_INVALID_WHEN_LABELS_INCOMPLETE"]
    status: Literal["LABELS_COMPLETE", "LEGACY_LABELS_INCOMPLETE"]
    corpus_source_count: int
    annotated_source_count: int
    unannotated_source_count: int
    full_corpus_precision_is_valid: bool
    annotated_judgment_ids: tuple[str, ...]
    unannotated_judgment_ids: tuple[str, ...]


def assess_holdout_coverage(
    *, bank: RetrievalEvaluationBank, corpus: RetrievalCorpus
) -> HoldoutCoverageAssessment:
    """Comprueba si todas las fuentes del corpus aparecen en las etiquetas."""

    corpus_ids = {source.judgment_id for source in corpus.sources}
    labelled_ids = {
        judgment_id
        for question in bank.questions
        for judgment_id in (
            *question.expected_judgment_ids,
            *question.contrast_judgment_ids,
        )
    }
    annotated = corpus_ids & labelled_ids
    unannotated = corpus_ids - labelled_ids
    complete = not unannotated
    return HoldoutCoverageAssessment(
        schema_version="residenciafiscal-holdout-coverage/1",
        metric_policy="FULL_CORPUS_PRECISION_INVALID_WHEN_LABELS_INCOMPLETE",
        status="LABELS_COMPLETE" if complete else "LEGACY_LABELS_INCOMPLETE",
        corpus_source_count=len(corpus_ids),
        annotated_source_count=len(annotated),
        unannotated_source_count=len(unannotated),
        full_corpus_precision_is_valid=complete,
        annotated_judgment_ids=tuple(sorted(annotated)),
        unannotated_judgment_ids=tuple(sorted(unannotated)),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mide cobertura de etiquetas del holdout.")
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    assessment = assess_holdout_coverage(
        bank=RetrievalEvaluationBank.model_validate_json(args.bank.read_bytes()),
        corpus=load_retrieval_corpus(args.corpus.read_bytes()),
    )
    rendered = (
        json.dumps(
            assessment.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    write_case_derivative(rendered, args.output)
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
