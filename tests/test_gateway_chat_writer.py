"""Segunda implementación del puerto del redactor, sobre `llm_gateway`.

El dominio jurídico no cambia: `CurrentStructuredStrategy` sigue recibiendo un
`StructuredAnswerWriter` y no sabe qué hay detrás.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gateway_chat_writer import GatewayChatWriter  # noqa: E402
from structured_answer_writer import ChatWriterRequest  # noqa: E402

DRAFT_JSON = (
    '{"status": "completa", "limits": [],'
    ' "claims": [{"kind": "judicial_assessment", "text": '
    '"La sentencia valora la permanencia.", "evidence_ids": ["E1"]}]}'
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


class FallbackProviderAdapter(FakeProviderAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.models: list[str] = []

    async def generate(self, request: Any, *, model: str) -> Any:
        from llm_gateway import ProviderResponse, TokenUsage

        self.requests.append(request)
        self.models.append(model)
        return ProviderResponse(
            output_text="esto no es json" if model == "gpt-5.6-luna" else DRAFT_JSON,
            usage=TokenUsage(120, 30),
            finish_reason="stop",
            model_used=model,
        )


def _writer(adapter: FakeProviderAdapter) -> GatewayChatWriter:
    from llm_gateway import LLMGateway, ProviderRegistry

    registry = ProviderRegistry()
    prefixes = {
        "openai": ("gpt-", "gemini"),
        "groq": ("meta-llama/",),
    }.get(adapter.name, ("gemini",))
    registry.register(adapter, model_prefixes=prefixes)
    return GatewayChatWriter(LLMGateway(registry=registry))


def _request(**kwargs: Any) -> ChatWriterRequest:
    defaults: dict[str, Any] = {
        "model": "gemini-3.5-flash-lite",
        "fallback_models": (),
        "request_id": "req-writer",
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
        assert result.draft.claims[0].evidence_ids == ("E1",)
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
    async def test_luna_recibe_el_esfuerzo_declarado_en_la_politica_del_chat(self) -> None:
        """Se compara contra la política, no contra un literal.

        Fijar aquí el valor obligaba a tocar el test al cambiar de esfuerzo, que
        es justo cuando conviene que compruebe algo: que el redactor transmite
        lo declarado en vez de dejar que el proveedor aplique su defecto.
        """
        from chat_model_policy import CHAT_MODEL, CHAT_REASONING_EFFORT

        adapter = FakeProviderAdapter()
        adapter.name = "openai"

        await _writer(adapter).write(
            _request(model=CHAT_MODEL, reasoning_effort=CHAT_REASONING_EFFORT)
        )

        assert adapter.requests[0].reasoning_effort == CHAT_REASONING_EFFORT

    async def test_model_fallback_is_passed_to_the_gateway(self) -> None:
        """El gateway decide cuándo ejecutar el modelo alternativo."""
        adapter = FakeProviderAdapter()
        adapter.name = "openai"

        await _writer(adapter).write(
            _request(
                model="gpt-5.6-luna",
                fallback_models=("gemini-3.6-flash",),
            )
        )

        assert adapter.requests[0].fallback_policy.models == ("gemini-3.6-flash",)

    async def test_the_requested_model_is_pinned(self) -> None:
        adapter = FakeProviderAdapter()

        await _writer(adapter).write(_request(model="gemini-3.6-flash"))

        assert adapter.requests[0].model == "gemini-3.6-flash"

    async def test_a_retry_is_bounded_and_visible(self) -> None:
        adapter = FakeProviderAdapter()

        await _writer(adapter).write(_request())

        assert adapter.requests[0].retry_policy.max_attempts == 2


class TestFacadeBoundary:
    async def test_writer_uses_the_stable_gpt_request_facade(self, monkeypatch: Any) -> None:
        from types import SimpleNamespace
        from typing import cast

        from llm_gateway import Cost, CostMeasurement, TokenUsage

        import gateway_chat_writer
        from chat_answer_contract import StructuredChatAnswerDraft

        captured: dict[str, Any] = {}

        async def fake_gpt_request(**kwargs: Any) -> Any:
            captured.update(kwargs)
            return SimpleNamespace(
                output=StructuredChatAnswerDraft.model_validate(json.loads(DRAFT_JSON)),
                usage=TokenUsage(120, 30),
                execution=SimpleNamespace(model_used="gemini-3.5-flash-lite"),
                cost=Cost(
                    measurement=CostMeasurement.ACTUAL,
                    microusd=60,
                    pricing_version="2026-07-31",
                ),
            )

        monkeypatch.setattr(gateway_chat_writer, "gpt_request", fake_gpt_request)
        request = _request()

        await gateway_chat_writer.GatewayChatWriter(cast(Any, object())).write(request)

        assert captured["ai_model"] == request.model
        assert captured["system_prompt"] == request.system_prompt
        assert captured["user_message"] == request.user_prompt
        assert captured["response_schema"] is StructuredChatAnswerDraft
        assert captured["fallback_models"] == request.fallback_models
        assert captured["request_id"] == request.request_id


class TestPortFidelity:
    async def test_it_returns_exactly_the_port_contract_and_no_more(self) -> None:
        """El redactor transporta el coste medido; no lo calcula.

        La distinción importa: quien lo calcula sigue siendo el gateway, con su
        catálogo y su versión de tarifas. Antes este campo no viajaba y la
        estrategia rehacía la cuenta con las mismas tarifas, que es la
        duplicación que este contrato elimina.
        """
        result = await _writer(FakeProviderAdapter()).write(_request())

        assert set(result.model_dump()) == {"draft", "usage", "model_used", "cost"}

    async def test_the_transported_cost_is_the_one_the_gateway_measured(self) -> None:
        """120 de entrada y 30 de salida a la tarifa de Luna: 0,20 y 1,20 USD/Mtok."""
        from chat_model_policy import CHAT_MODEL

        adapter = FakeProviderAdapter()
        adapter.name = "openai"

        result = await _writer(adapter).write(_request(model=CHAT_MODEL))

        assert result.cost.microusd == 60
        assert result.cost.measurement.value == "ACTUAL"
        assert result.cost.pricing_version


class TestFailures:
    async def test_an_unparseable_draft_raises_rather_than_inventing_one(self) -> None:
        """Desde la v0.7.0 el error conserva los intentos, y con ellos el gasto.

        Antes se propagaba el error de salida a secas y se perdía la cuenta de
        lo pagado: una respuesta ilegible sigue siendo una llamada facturada.
        """
        from llm_gateway import AllAttemptsFailed, OutputError

        adapter = FakeProviderAdapter(text="esto no es json")

        with pytest.raises(AllAttemptsFailed) as fallo:
            await _writer(adapter).write(_request())

        assert isinstance(fallo.value.__cause__, OutputError)
        assert fallo.value.attempts
        assert all(intento.billable for intento in fallo.value.attempts)

    async def test_gateway_executes_the_declared_model_fallback(self) -> None:
        adapter = FallbackProviderAdapter()
        adapter.name = "openai"

        result = await _writer(adapter).write(
            _request(
                model="gpt-5.6-luna",
                fallback_models=("gemini-3.6-flash",),
            )
        )

        assert result.model_used == "gemini-3.6-flash"
        assert adapter.models == [
            "gpt-5.6-luna",
            "gemini-3.6-flash",
        ]

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
        # Medido con el esfuerzo vigente (`high`): 16,3 s, 17,8 s, 22,2 s y
        # 30,3 s en preguntas reales del corpus de cinco. El tope es 3× el peor
        # caso. Con `max` las mismas preguntas tardaban 81-96 s y no cabían.
        assert policy.total_seconds == 200.0
        assert policy.per_attempt_seconds == 90.0
