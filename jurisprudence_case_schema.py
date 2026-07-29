"""Exportación determinista del JSON Schema jurisprudencial v3."""

from __future__ import annotations

import json
from pathlib import Path

from jurisprudence_case_models import JurisprudenceCase


def render_case_json_schema() -> str:
    """Serializa el schema Pydantic de forma estable y legible."""

    return (
        json.dumps(
            JurisprudenceCase.model_json_schema(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def write_case_json_schema(destination: Path) -> Path:
    """Escribe el schema generado en un destino explícito."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_case_json_schema(), encoding="utf-8")
    return destination
