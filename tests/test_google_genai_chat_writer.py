from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any


class FakeInteractions:
    def __init__(self, response: Any) -> None:
        self.response = response
        self.requests: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.requests.append(kwargs)
        return self.response


class FakeGoogleClient:
    def __init__(self, response: Any) -> None:
        self.interactions = FakeInteractions(response)


def _request() -> Any:
    from chat_answer_contract import StructuredChatAnswerDraft
    from structured_answer_writer import ChatWriterRequest

    return ChatWriterRequest(
        model="gemini-3.5-flash-lite",
        system_prompt="Instrucciones jurídicas comunes.",
        user_prompt="Pregunta y contexto E1.",
        evidence_context='{"evidence":[]}',
        response_schema=StructuredChatAnswerDraft.model_json_schema(),
    )


async def test_writer_interactions_hace_una_llamada_sin_tools_ni_fallback() -> None:
    from google_genai_chat_writer import GoogleGenAIChatWriter

    payload = {
        "status": "completa",
        "answer": "Respuesta fundamentada.",
        "limits": [],
        "evidence_ids": ["E1"],
    }
    response = SimpleNamespace(
        model="gemini-3.5-flash-lite",
        output_text=json.dumps(payload),
        usage=SimpleNamespace(
            total_input_tokens=120,
            total_output_tokens=25,
            total_thought_tokens=5,
        ),
    )
    client = FakeGoogleClient(response)

    result = await GoogleGenAIChatWriter(client).write(_request())

    assert result.draft.evidence_ids == ("E1",)
    assert result.usage.input_tokens == 120
    assert result.usage.output_tokens == 30
    assert result.usage.usage_complete is True
    assert result.model_used == "gemini-3.5-flash-lite"
    assert len(client.interactions.requests) == 1
    provider_request = client.interactions.requests[0]
    assert provider_request["model"] == "gemini-3.5-flash-lite"
    assert provider_request["store"] is False
    assert "tools" not in provider_request
    assert provider_request["input"] == (
        "Instrucciones jurídicas comunes.\n\nPregunta y contexto E1."
    )
    assert provider_request["response_format"]["schema"]["title"] == "StructuredChatAnswerDraft"


async def test_writer_marca_usage_incompleto_si_el_proveedor_no_lo_devuelve() -> None:
    from google_genai_chat_writer import GoogleGenAIChatWriter

    payload = {
        "status": "abstención",
        "answer": "",
        "limits": ["Sin cobertura."],
        "evidence_ids": [],
    }
    client = FakeGoogleClient(
        SimpleNamespace(
            model=None,
            output_text=json.dumps(payload),
            usage=None,
        )
    )

    result = await GoogleGenAIChatWriter(client).write(_request())

    assert result.usage.input_tokens == 0
    assert result.usage.output_tokens == 0
    assert result.usage.usage_complete is False
    assert result.model_used == "gemini-3.5-flash-lite"
