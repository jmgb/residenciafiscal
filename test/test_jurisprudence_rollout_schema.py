"""Schema versionado del manifiesto de rollout, sin manifiesto real."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "schemas/residenciafiscal-rollout-v1.schema.json"


def test_schema_de_rollout_versionado_esta_sincronizado() -> None:
    from jurisprudence_rollout_schema import render_rollout_json_schema

    assert SCHEMA_PATH.read_text(encoding="utf-8") == render_rollout_json_schema()
