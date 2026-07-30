"""Serialización y persistencia atómica del caso jurisprudencial v3."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from jurisprudence_case_models import JurisprudenceCase


def render_jurisprudence_case(case: JurisprudenceCase) -> str:
    """Serializa un caso validado de forma determinista."""

    return (
        json.dumps(
            case.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def load_jurisprudence_case(serialized: str | bytes) -> JurisprudenceCase:
    """Valida un caso desde su representación JSON."""

    return JurisprudenceCase.model_validate_json(serialized)


def write_jurisprudence_case(
    case: JurisprudenceCase,
    destination: Path,
) -> Path:
    """Escribe mediante reemplazo atómico sin dejar archivos parciales."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = render_jurisprudence_case(case).encode("utf-8")
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
