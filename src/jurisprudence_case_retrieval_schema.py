"""Exportación determinista del JSON Schema de recuperación v1."""

from __future__ import annotations

import json
from pathlib import Path

from jurisprudence_case_retrieval_models import RetrievalIndex


def render_retrieval_json_schema() -> str:
    """Serializa el schema Pydantic de forma estable."""

    return (
        json.dumps(
            RetrievalIndex.model_json_schema(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def write_retrieval_json_schema(destination: Path) -> Path:
    """Escribe el schema generado en un destino explícito."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_retrieval_json_schema(), encoding="utf-8")
    return destination
