"""Puerto local del redactor LLM para la estrategia estructurada."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol

from pydantic import Field

from chat_answer_contract import StructuredChatAnswerDraft
from jurisprudence_case_catalogs import JurisprudenceCaseModel, NonEmptyText


@dataclass(frozen=True)
class ChatWriterRequest:
    model: str
    system_prompt: str
    user_prompt: str
    evidence_context: str
    response_schema: dict[str, Any]
    temperature: float = 0
    fallback_policy: Literal["disabled"] = "disabled"


class ChatWriterUsage(JurisprudenceCaseModel):
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    usage_complete: bool


class ChatWriterResult(JurisprudenceCaseModel):
    draft: StructuredChatAnswerDraft
    usage: ChatWriterUsage
    model_used: NonEmptyText


class StructuredAnswerWriter(Protocol):
    async def write(self, request: ChatWriterRequest) -> ChatWriterResult: ...
