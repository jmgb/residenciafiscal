"""Verificación reproducible de los artefactos publicados del rollout."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_verifica_manifiesto_corpus_build_y_presupuesto_de_artefactos() -> None:
    from jurisprudence_rollout_release import verify_rollout_release

    result = verify_rollout_release(
        manifest_path=PROJECT_ROOT / "sentencias/jurisprudence_v3_rollout_106.json",
        output_root=PROJECT_ROOT / "knowledge/jurisprudencia-v3",
        project_root=PROJECT_ROOT,
    )

    assert result.document_count == 106
    assert result.retrieval_document_count == 67
    assert result.retrieval_unit_count == 74
    assert result.publication_status == "AGENT_REVIEWED_ONLY"
    assert result.artifact_file_count < 1_000
    assert result.artifact_bytes < 50_000_000
