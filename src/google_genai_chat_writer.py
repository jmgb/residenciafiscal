"""Adaptador temporal y mínimo de Interactions para el redactor de A."""

from __future__ import annotations

import asyncio
from typing import Any

from chat_answer_contract import StructuredChatAnswerDraft
from structured_answer_writer import (
    ChatWriterRequest,
    ChatWriterResult,
    ChatWriterUsage,
)


def _output_text(interaction: Any) -> str:
    direct = getattr(interaction, "output_text", None)
    if direct:
        return str(direct)
    chunks = [
        str(getattr(content, "text", ""))
        for step in getattr(interaction, "steps", ()) or ()
        if getattr(step, "type", None) == "model_output"
        for content in getattr(step, "content", ()) or ()
        if getattr(content, "type", None) == "text"
    ]
    return "".join(chunks)


def _usage(interaction: Any) -> ChatWriterUsage:
    usage = getattr(interaction, "usage", None)
    if usage is None:
        return ChatWriterUsage(
            input_tokens=0,
            output_tokens=0,
            usage_complete=False,
        )
    input_value = getattr(usage, "total_input_tokens", None)
    output_value = getattr(usage, "total_output_tokens", None)
    thought_value = getattr(usage, "total_thought_tokens", 0)
    return ChatWriterUsage(
        input_tokens=int(input_value or 0),
        output_tokens=int(output_value or 0) + int(thought_value or 0),
        usage_complete=input_value is not None and output_value is not None,
    )


class GoogleGenAIChatWriter:
    """Una generación estructurada, sin tools, persistencia ni fallback."""

    def __init__(self, client: Any) -> None:
        self._client = client

    async def write(self, request: ChatWriterRequest) -> ChatWriterResult:
        interaction = await asyncio.to_thread(
            self._client.interactions.create,
            model=request.model,
            input=f"{request.system_prompt}\n\n{request.user_prompt}",
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": request.response_schema,
            },
            store=False,
        )
        model_used = str(getattr(interaction, "model", None) or request.model)
        return ChatWriterResult(
            draft=StructuredChatAnswerDraft.model_validate_json(_output_text(interaction)),
            usage=_usage(interaction),
            model_used=model_used,
        )


def create_google_genai_chat_writer(api_key: str) -> GoogleGenAIChatWriter:
    from google import genai

    return GoogleGenAIChatWriter(genai.Client(api_key=api_key))
