"""Persistencia atómica de derivados legibles y recuperables del caso v3."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def write_case_derivative(payload: str, destination: Path) -> Path:
    """Escribe UTF-8 mediante reemplazo atómico."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as temporary:
            temporary.write(payload)
            temporary.flush()
            os.fsync(temporary.fileno())
        temporary_path.replace(destination)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise
    return destination
