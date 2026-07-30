"""JSON Schema reproducible del manifiesto de rollout E."""

from __future__ import annotations

import json

from jurisprudence_rollout_models import RolloutManifest


def render_rollout_json_schema() -> str:
    return (
        json.dumps(
            RolloutManifest.model_json_schema(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
