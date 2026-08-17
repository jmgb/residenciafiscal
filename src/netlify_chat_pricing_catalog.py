"""Export reproducible del catálogo compartido para la Function TypeScript."""

from __future__ import annotations

import json
from pathlib import Path

from llm_gateway.models import CATALOG_VERSION, lookup_model

CHAT_MODELS = (
    "gemini-3.5-flash-lite",
    "gemini-3.7-flash",
    "gpt-5.6-luna",
)


def render_netlify_chat_pricing() -> str:
    models: dict[str, dict[str, float]] = {}
    for model in CHAT_MODELS:
        info = lookup_model(model)
        if info is None:
            raise RuntimeError(f"modelo ausente del catálogo compartido: {model}")
        models[model] = {
            "input_usd_per_mtok": float(info.input_usd_per_mtok),
            "output_usd_per_mtok": float(info.output_usd_per_mtok),
        }
    return (
        json.dumps(
            {"catalog_version": CATALOG_VERSION, "models": models},
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def export_netlify_chat_pricing(target: Path) -> None:
    target.write_text(render_netlify_chat_pricing(), encoding="utf-8")


if __name__ == "__main__":
    export_netlify_chat_pricing(Path("frontend/netlify/functions/chat/pricing.generated.json"))
