from pathlib import Path

from netlify_chat_pricing_catalog import render_netlify_chat_pricing


def test_netlify_pricing_is_derived_from_shared_gateway_catalog() -> None:
    artifact = Path("frontend/netlify/functions/chat/pricing.generated.json")

    assert artifact.read_text(encoding="utf-8") == render_netlify_chat_pricing()
