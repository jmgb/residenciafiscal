"""Segunda implementación del puerto del redactor, sobre `llm_gateway`.

El dominio jurídico no cambia: `CurrentStructuredStrategy` sigue recibiendo un
`StructuredAnswerWriter` y no sabe qué hay detrás.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gateway_chat_writer import GatewayChatWriter  # noqa: E402
from structured_answer_writer import ChatWriterRequest  # noqa: E402

DRAFT_JSON = (
    '{"status": "completa", "answer": "La sentencia valora la permanencia.",'
    ' "limits": [], "evidence_ids": ["E1"]}'
)


class FakeProviderAdapter:
    """Doble del adaptador de proveedor, dentro del gateway real."""

    name = "gemini"

    def __init__(self, *, text: str = DRAFT_JSON, usage: Any = None) -> None:
        self._text = text
        self._usage = usage
        self.requests: list[Any] = []

    async def generate(self, request: Any, *, model: str) -> Any:
        from llm_gateway import ProviderResponse, TokenUsage

        self.requests.append(request)
        return ProviderResponse(
            output_text=self._text,
            usage=self._usage if self._usage is not None else TokenUsage(120, 30),
            finish_reason="stop",
        )


def _writer(adapter: FakeProviderAdapter) -> GatewayChatWriter:
    from llm_gateway import LLMGateway, ProviderRegistry

    registry = ProviderRegistry()
    prefixes = ("gpt-",) if adapter.name == "openai" else ("gemini",)
    registry.register(adapter, model_prefixes=prefixes)
    return GatewayChatWriter(LLMGateway(registry=registry))


def _request(**kwargs: Any) -> ChatWriterRequest:
    defaults: dict[str, Any] = {
        "model": "gemini-3.5-flash-lite",
        "system_prompt": "Responde solo desde la evidencia.",
        "user_prompt": "¿Qué valor se dio al certificado?",
        "evidence_context": "[E1] Fragmento literal.",
        "response_schema": {"type": "object"},
        "temperature": 0,
    }
    defaults.update(kwargs)
    return ChatWriterRequest(**defaults)


class TestContractParity:
    async def test_it_returns_the_same_result_type_as_the_legacy_writer(self) -> None:
        result = await _writer(FakeProviderAdapter()).write(_request())

        assert result.draft.status == "completa"
        assert result.draft.evidence_ids == ("E1",)
        assert result.model_used == "gemini-3.5-flash-lite"

    async def test_it_maps_usage(self) -> None:
        result = await _writer(FakeProviderAdapter()).write(_request())

        assert result.usage.input_tokens == 120
        assert result.usage.output_tokens == 30
        assert result.usage.usage_complete is True

    async def test_unreported_usage_is_flagged_incomplete_not_silently_zero(self) -> None:
        from llm_gateway import TokenUsage

        adapter = FakeProviderAdapter(usage=TokenUsage.unknown())

        result = await _writer(adapter).write(_request())

        assert result.usage.usage_complete is False

    async def test_reasoning_tokens_are_a_breakdown_of_the_output_not_an_extra(self) -> None:
        """Sumarlos facturaría dos veces el mismo razonamiento.

        Los adaptadores normalizan en el borde: lo que se factura a tarifa de
        salida ya está dentro de `output_tokens` cuando llega hasta aquí.
        """
        from llm_gateway import TokenUsage

        adapter = FakeProviderAdapter(
            usage=TokenUsage(input_tokens=120, output_tokens=30, reasoning_tokens=18)
        )

        result = await _writer(adapter).write(_request())

        assert result.usage.output_tokens == 30


class TestEvidenceAndPrompt:
    async def test_the_user_prompt_is_sent_verbatim(self) -> None:
        """Paridad con el redactor legado: la evidencia ya viene dentro del
        `user_prompt` que compone la estrategia, así que `evidence_context` no
        se envía por separado. Duplicarlo cambiaría los tokens y el coste."""
        adapter = FakeProviderAdapter()

        await _writer(adapter).write(_request())

        sent = adapter.requests[0]
        assert sent.messages[0].content == "¿Qué valor se dio al certificado?"
        assert len(sent.messages) == 1

    async def test_the_system_prompt_travels_separately(self) -> None:
        adapter = FakeProviderAdapter()

        await _writer(adapter).write(_request())

        assert adapter.requests[0].system_prompt == "Responde solo desde la evidencia."


class TestPolicies:
    async def test_luna_recibe_el_esfuerzo_maximo_de_la_politica_del_chat(self) -> None:
        from chat_model_policy import CHAT_MODEL, CHAT_REASONING_EFFORT

        adapter = FakeProviderAdapter()
        adapter.name = "openai"

        await _writer(adapter).write(
            _request(model=CHAT_MODEL, reasoning_effort=CHAT_REASONING_EFFORT)
        )

        assert adapter.requests[0].reasoning_effort == "max"

    async def test_model_fallback_stays_disabled(self) -> None:
        """A no puede responder con un modelo distinto del que declara."""
        adapter = FakeProviderAdapter()

        await _writer(adapter).write(_request())

        assert adapter.requests[0].fallback_policy.models == ()

    async def test_the_requested_model_is_pinned(self) -> None:
        adapter = FakeProviderAdapter()

        await _writer(adapter).write(_request(model="gemini-3.6-flash"))

        assert adapter.requests[0].model == "gemini-3.6-flash"

    async def test_a_retry_is_bounded_and_visible(self) -> None:
        adapter = FakeProviderAdapter()

        await _writer(adapter).write(_request())

        assert adapter.requests[0].retry_policy.max_attempts == 2


class TestPortFidelity:
    async def test_it_returns_exactly_the_port_contract_and_no_more(self) -> None:
        """El coste lo calcula la estrategia, no el redactor."""
        result = await _writer(FakeProviderAdapter()).write(_request())

        assert set(result.model_dump()) == {"draft", "usage", "model_used"}


class TestFailures:
    async def test_an_unparseable_draft_raises_rather_than_inventing_one(self) -> None:
        from llm_gateway import OutputError

        adapter = FakeProviderAdapter(text="esto no es json")

        with pytest.raises((OutputError, ValueError)):
            await _writer(adapter).write(_request())

    async def test_the_writer_exposes_no_factory_that_builds_its_own_client(self) -> None:
        """Las credenciales son de la aplicación, no del redactor."""
        import gateway_chat_writer

        assert not hasattr(gateway_chat_writer, "create_gateway_chat_writer")


class TestTimeBudget:
    async def test_two_attempts_fit_inside_the_declared_budget(self) -> None:
        """Un reintento no puede doblar el tiempo que el redactor declara."""
        from gateway_chat_writer import (
            WRITER_ATTEMPT_TIMEOUT_SECONDS,
            WRITER_MAX_ATTEMPTS,
            WRITER_TIMEOUT_SECONDS,
        )

        assert WRITER_ATTEMPT_TIMEOUT_SECONDS * WRITER_MAX_ATTEMPTS <= WRITER_TIMEOUT_SECONDS

    async def test_the_request_declares_both_budgets(self) -> None:
        adapter = FakeProviderAdapter()

        await _writer(adapter).write(_request())

        policy = adapter.requests[0].timeout_policy
        assert policy.total_seconds == 200.0
        assert policy.per_attempt_seconds == 90.0


class TestTemperature:
    """La temperatura heredada rompía A al apuntar la política del chat a Luna."""

    async def test_un_modelo_de_razonamiento_de_openai_no_recibe_temperatura(self) -> None:
        """La Responses API responde `Unsupported parameter` y falla la respuesta entera."""
        adapter = FakeProviderAdapter()
        adapter.name = "openai"
        from llm_gateway import LLMGateway, ProviderRegistry

        registry = ProviderRegistry()
        registry.register(adapter, model_prefixes=("gpt-",))
        writer = GatewayChatWriter(LLMGateway(registry=registry))

        await writer.write(_request(model="gpt-5.6-luna", temperature=0))

        assert adapter.requests[0].temperature is None

    async def test_gemini_conserva_la_temperatura_pedida(self) -> None:
        """Sí la admite, y quitársela cambiaría el determinismo ya medido."""
        adapter = FakeProviderAdapter()

        await _writer(adapter).write(_request(model="gemini-3.6-flash", temperature=0))

        assert adapter.requests[0].temperature == 0
