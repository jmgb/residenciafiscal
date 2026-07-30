"""Contrato del manifiesto reproducible de cinco sentencias v3."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError


def _manifest(*, source_sha256: str = "a" * 64) -> dict[str, Any]:
    return {
        "schema_version": "residenciafiscal-jurisprudence-sample/1",
        "sample_id": "muestra-v3",
        "expected_documents": 1,
        "documents": [
            {
                "judgment_id": "san-1210-2023",
                "source_file": "sentencias/SAN_1210_2023.pdf",
                "source_sha256": source_sha256,
                "proposal_path": (
                    "knowledge/jurisprudence-case-proposals/san-1210-2023.proposal.json"
                ),
                "evaluation_path": (
                    "knowledge/jurisprudencia-v3/evaluations/san-1210-2023.questions.json"
                ),
            }
        ],
    }


def test_carga_un_manifiesto_portable_y_ordenado(tmp_path: Path) -> None:
    from jurisprudence_sample_manifest import load_sample_manifest

    manifest_path = tmp_path / "sample.json"
    manifest_path.write_text(json.dumps(_manifest()), encoding="utf-8")

    manifest = load_sample_manifest(manifest_path)

    assert manifest.sample_id == "muestra-v3"
    assert manifest.expected_documents == 1
    assert manifest.documents[0].judgment_id == "san-1210-2023"


def test_rechaza_recuentos_ids_y_rutas_inseguros() -> None:
    from jurisprudence_sample_manifest import JurisprudenceSampleManifest

    raw = _manifest()
    raw["expected_documents"] = 2
    with pytest.raises(ValidationError, match="expected_documents"):
        JurisprudenceSampleManifest.model_validate(raw)

    raw = _manifest()
    raw["documents"] = [raw["documents"][0], raw["documents"][0]]
    raw["expected_documents"] = 2
    with pytest.raises(ValidationError, match="judgment_id"):
        JurisprudenceSampleManifest.model_validate(raw)

    raw = _manifest()
    raw["documents"][0]["proposal_path"] = "../proposal.json"
    with pytest.raises(ValidationError, match="ruta relativa"):
        JurisprudenceSampleManifest.model_validate(raw)


def test_valida_hash_y_existencia_de_todas_las_entradas(tmp_path: Path) -> None:
    from jurisprudence_sample_manifest import (
        JurisprudenceSampleManifest,
        validate_sample_inputs,
    )
    from okf_provenance import sha256_file

    source = tmp_path / "sentencias/SAN_1210_2023.pdf"
    proposal = tmp_path / "knowledge/jurisprudence-case-proposals/san-1210-2023.proposal.json"
    evaluation = tmp_path / "knowledge/jurisprudencia-v3/evaluations/san-1210-2023.questions.json"
    for path, payload in (
        (source, b"pdf"),
        (proposal, b"{}"),
        (evaluation, b"{}"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    manifest = JurisprudenceSampleManifest.model_validate(
        _manifest(source_sha256=sha256_file(source))
    )

    result = validate_sample_inputs(manifest, project_root=tmp_path)

    assert result == ("san-1210-2023",)

    source.write_bytes(b"changed")
    with pytest.raises(ValueError, match="source_sha256"):
        validate_sample_inputs(manifest, project_root=tmp_path)
