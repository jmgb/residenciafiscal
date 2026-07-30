"""Contratos comunes del comparador local de estrategias F0."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import Field

from jurisprudence_case_catalogs import (
    Identifier,
    JurisprudenceCaseModel,
    NonEmptyText,
    Sha256,
)

StrategyId = Literal["current_structured", "gemini_file_search"]
AnswerStatus = Literal["completa", "parcial", "pregunta", "abstención", "error"]
CostMeasurement = Literal["ACTUAL", "ESTIMATED"]


class MarginalCost(JurisprudenceCaseModel):
    """Coste marginal auditable de una respuesta, sin preparación de corpus."""

    currency: Literal["USD"] = "USD"
    amount_usd: Annotated[Decimal, Field(ge=0, decimal_places=6)]
    cost_microusd: Annotated[int, Field(ge=0)]
    measurement: CostMeasurement
    scope: Literal["REQUEST_MARGINAL"] = "REQUEST_MARGINAL"
    pricing_version: NonEmptyText
    input_tokens: Annotated[int, Field(ge=0)]
    output_tokens: Annotated[int, Field(ge=0)]
    retrieved_document_tokens: Annotated[int, Field(ge=0)]
    excludes_corpus_preparation: Literal[True] = True


class StrategySource(JurisprudenceCaseModel):
    """Extracto judicial que ha superado la verificación literal local."""

    strategy: StrategyId
    judgment_id: Identifier
    page: Annotated[int, Field(gt=0)]
    source_sha256: Sha256
    quote: NonEmptyText
    verification: Literal["EXACT"]


class StrategyAnswer(JurisprudenceCaseModel):
    """Una respuesta terminal e independiente del comparador."""

    strategy: StrategyId
    status: AnswerStatus
    text: str
    sources: tuple[StrategySource, ...]
    limits: tuple[str, ...]
    cost: MarginalCost
    model: NonEmptyText
    latency_ms: Annotated[int, Field(ge=0)]


class ComparisonReport(JurisprudenceCaseModel):
    """Dos respuestas hermanas correlacionadas, sin persistir la pregunta."""

    schema_version: Literal["residenciafiscal-chat-comparison/1"] = (
        "residenciafiscal-chat-comparison/1"
    )
    request_id: NonEmptyText
    experimental: Literal[True] = True
    answers: Annotated[tuple[StrategyAnswer, StrategyAnswer], Field(min_length=2, max_length=2)]
