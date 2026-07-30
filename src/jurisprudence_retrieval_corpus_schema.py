"""Exportación determinista del JSON Schema del corpus de recuperación."""

from __future__ import annotations

import json
from pathlib import Path

from jurisprudence_case_derivative_artifacts import write_case_derivative
from jurisprudence_retrieval_corpus_models import RetrievalCorpus


def render_retrieval_corpus_json_schema() -> str:
    return (
        json.dumps(
            RetrievalCorpus.model_json_schema(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def write_retrieval_corpus_json_schema(destination: Path) -> Path:
    return write_case_derivative(
        render_retrieval_corpus_json_schema(),
        destination,
    )
