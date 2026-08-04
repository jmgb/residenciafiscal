"""El serializador Python debe producir el mismo SSE que el runtime vigente.

Los fixtures son sintéticos y los comparte con `frontend/tests`. Un cambio en el
protocolo que solo toque uno de los dos runtimes rompe aquí antes de llegar al
navegador; sin este gate, un terminal sin `request_id` pasaba desapercibido y
dejaba la comparación sin voto.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from api.chat import comparison_events  # noqa: E402
from chat_strategy_models import ComparisonReport  # noqa: E402

FIXTURES = json.loads(Path("schemas/chat-protocol-2.fixtures.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", FIXTURES["cases"], ids=lambda case: case["name"])
def test_el_sse_python_coincide_con_el_contrato_compartido(case: dict[str, object]) -> None:
    report = ComparisonReport.model_validate(case["report"])
    serialized = b"".join(comparison_events(report)).decode("utf-8")

    assert serialized == case["expected_sse"]


def test_los_fixtures_no_contienen_material_real() -> None:
    raw = json.dumps(FIXTURES, ensure_ascii=False)

    assert "sintétic" in raw
    assert "sk-" not in raw
    assert "supabase.co" not in raw
