"""Serialización y persistencia atómica del corpus verbatim."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from verbatim_models import VerbatimCorpus


def render_verbatim_corpus(corpus: VerbatimCorpus) -> str:
    """Serializa un corpus validado de forma determinista."""

    return (
        json.dumps(
            corpus.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def load_verbatim_corpus(serialized: str | bytes) -> VerbatimCorpus:
    """Valida un corpus desde su representación JSON."""

    return VerbatimCorpus.model_validate_json(serialized)


def write_verbatim_corpus(
    corpus: VerbatimCorpus,
    destination: Path,
) -> Path:
    """Escribe mediante reemplazo atómico sin dejar archivos parciales."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = render_verbatim_corpus(corpus).encode("utf-8")
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "wb") as temporary:
            temporary.write(payload)
            temporary.flush()
            os.fsync(temporary.fileno())
        temporary_path.replace(destination)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise
    return destination
