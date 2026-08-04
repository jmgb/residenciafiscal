"""Puerto local del redactor LLM para la estrategia estructurada."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from llm_gateway import Cost, ReasoningEffort
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
    reasoning_effort: ReasoningEffort | None = None
    fallback_models: tuple[str, ...] = ()


class ChatWriterUsage(JurisprudenceCaseModel):
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    usage_complete: bool


class ChatWriterResult(JurisprudenceCaseModel):
    draft: StructuredChatAnswerDraft
    usage: ChatWriterUsage
    model_used: NonEmptyText
    cost: Cost
    """El importe que midió el gateway, transportado sin recalcular.

    Antes el redactor lo descartaba y la estrategia lo recomponía a partir de
    los tokens y del catálogo: las mismas tarifas y la misma aritmética en
    microdólares, hechas dos veces. Además esa cuenta se hacía sobre el uso
    agregado, así que perdía la degradación a `ESTIMATED` que el paquete aplica
    cuando un intento facturado no tiene importe conocido.

    Es un dato del gateway, no del producto: por eso viaja el `Cost` del paquete
    y no una copia local con otros nombres."""


class StructuredAnswerWriter(Protocol):
    async def write(self, request: ChatWriterRequest) -> ChatWriterResult: ...
