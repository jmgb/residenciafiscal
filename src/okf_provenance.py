"""Artefactos y metadatos reproducibles del export jurisprudencial."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from importlib.metadata import version
from pathlib import Path


def sha256_file(path: Path) -> str:
    """Calcula la huella binaria sin transformar el contenido."""

    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def analysis_snapshot_bytes(raw_record: Mapping[str, object]) -> bytes:
    """Serializa el registro con el mismo contrato usado por el snapshot."""

    content = json.dumps(raw_record, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    return content.encode()


def sha256_analysis_record(raw_record: Mapping[str, object]) -> str:
    """Calcula la huella de la representación canónica del registro."""

    return hashlib.sha256(analysis_snapshot_bytes(raw_record)).hexdigest()


def write_analysis_snapshot(
    output_dir: Path,
    slug: str,
    raw_record: Mapping[str, object],
) -> Path:
    """Versiona solo el registro exacto que permite reconstruir el concepto."""

    snapshot_path = output_dir / "sources" / f"{slug}.analysis.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_bytes(analysis_snapshot_bytes(raw_record))
    return snapshot_path


def analysis_provenance(raw_record: Mapping[str, object]) -> dict[str, object]:
    """Conserva únicamente procedencia disponible; nunca inventa el prompt histórico."""

    execution = raw_record.get("tiempo_ejecucion")
    model_id = "not_recorded"
    if isinstance(execution, str) and execution.strip():
        model_id = execution.split(" - ", 1)[0].strip()
    return {
        "model_id": model_id,
        "prompt_sha256": None,
        "prompt_provenance": "not_recorded_in_source_analysis",
    }


def extractor_id() -> str:
    """Identificador versionado del extractor determinista."""

    return f"pypdf/{version('pypdf')}"
