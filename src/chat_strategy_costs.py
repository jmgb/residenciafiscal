"""Cálculo decimal de costes para Gemini File Search en F0."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from pydantic import Field

from chat_strategy_models import MarginalCost
from jurisprudence_case_catalogs import JurisprudenceCaseModel

DEFAULT_FILE_SEARCH_MODEL = "gemini-3.5-flash-lite"
SUPPORTED_FILE_SEARCH_MODELS = (
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
)
PRICING_VERSION = "2026-07-30"
MODEL_RATES_MICROUSD_PER_TOKEN = {
    "gemini-3.5-flash-lite": (Decimal("0.3"), Decimal("2.5")),
    "gemini-3.6-flash": (Decimal("1.5"), Decimal("7.5")),
}


class GeminiUsage(JurisprudenceCaseModel):
    """Desglose facturable; input excluye los documentos recuperados."""

    input_tokens: int = Field(ge=0)
    retrieved_document_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    usage_complete: bool


def calculate_gemini_file_search_cost(
    usage: GeminiUsage,
    *,
    model: str = DEFAULT_FILE_SEARCH_MODEL,
) -> MarginalCost:
    """Calcula en microdólares enteros y serializa USD con seis decimales."""

    try:
        input_rate, output_rate = MODEL_RATES_MICROUSD_PER_TOKEN[model]
    except KeyError as error:
        raise ValueError(f"modelo File Search sin tarifa: {model}") from error
    input_total = usage.input_tokens + usage.retrieved_document_tokens
    raw_microusd = Decimal(input_total) * input_rate + Decimal(usage.output_tokens) * output_rate
    cost_microusd = int(raw_microusd.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    amount_usd = (Decimal(cost_microusd) / Decimal(1_000_000)).quantize(Decimal("0.000001"))
    return MarginalCost(
        amount_usd=amount_usd,
        cost_microusd=cost_microusd,
        measurement="ACTUAL" if usage.usage_complete else "ESTIMATED",
        pricing_version=PRICING_VERSION,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        retrieved_document_tokens=usage.retrieved_document_tokens,
    )


def zero_marginal_cost() -> MarginalCost:
    """Coste real cero para la estrategia determinista local."""

    return MarginalCost(
        amount_usd=Decimal("0.000000"),
        cost_microusd=0,
        measurement="ACTUAL",
        pricing_version=PRICING_VERSION,
        input_tokens=0,
        output_tokens=0,
        retrieved_document_tokens=0,
    )


def unknown_failure_cost() -> MarginalCost:
    """Límite inferior estimado cuando un fallo no devuelve uso facturable."""

    return MarginalCost(
        amount_usd=Decimal("0.000000"),
        cost_microusd=0,
        measurement="ESTIMATED",
        pricing_version=PRICING_VERSION,
        input_tokens=0,
        output_tokens=0,
        retrieved_document_tokens=0,
    )
