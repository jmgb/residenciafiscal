from pathlib import Path
from typing import Any

import yaml

AUTOFIX_CONTRACT = Path(__file__).parents[1] / ".autofix.yml"


def load_autofix_contract() -> dict[str, Any]:
    return yaml.safe_load(AUTOFIX_CONTRACT.read_text(encoding="utf-8"))


def test_autofix_covers_every_sentry_runtime() -> None:
    contract = load_autofix_contract()

    assert contract["incident_sources"]["sentry_projects"] == [
        "residencia-fiscal-backend",
        "residencia-fiscal-chat-backend",
        "residencia-fiscal-frontend",
        "residencia-fiscal-chat",
    ]


def test_autofix_merges_verified_fixes_automatically() -> None:
    contract = load_autofix_contract()

    assert contract["delivery"]["auto_merge"] is True
