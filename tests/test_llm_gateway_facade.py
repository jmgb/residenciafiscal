"""Contrato de la fachada funcional que traduce llamadas al gateway."""

from __future__ import annotations

from typing import Any

import pytest
from llm_gateway import ResponseFormat


class RecordingGateway:
    def __init__(self, result: Any) -> None:
        self.result = result
        self.request: Any = None

    async def generate(self, request: Any) -> Any:
        self.request = request
        return self.result


async def test_gpt_request_traduce_el_contrato_y_devuelve_el_resultado_del_gateway() -> None:
    from llm_gateway_facade import gpt_request

    expected = object()
    gateway = RecordingGateway(expected)

    result = await gpt_request(
        "gpt-5.6-luna",
        "Responde solo desde la evidencia.",
        "¿Qué valor se dio al certificado?",
        gateway=gateway,
        temperature=0,
        reasoning_effort="high",
        fallback_models=("gemini-3.7-flash",),
        request_id="req-facade",
        source="test-facade",
    )

    assert result is expected
    assert gateway.request.model == "gpt-5.6-luna"
    assert gateway.request.system_prompt == "Responde solo desde la evidencia."
    assert gateway.request.messages[0].content == "¿Qué valor se dio al certificado?"
    assert gateway.request.temperature == 0
    assert gateway.request.reasoning_effort == "high"
    assert gateway.request.fallback_policy.models == ("gemini-3.7-flash",)
    assert gateway.request.request_id == "req-facade"
    assert gateway.request.source == "test-facade"
    assert gateway.request.response_format is ResponseFormat.TEXT


async def test_gpt_request_rechaza_fallback_del_mismo_proveedor() -> None:
    from llm_gateway_facade import gpt_request

    with pytest.raises(ValueError, match="otro proveedor"):
        await gpt_request(
            "gpt-5.6-luna",
            None,
            "mensaje",
            gateway=RecordingGateway(object()),
            fallback_models=("gpt-5.6-terra",),
        )
