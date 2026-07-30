"""Cálculo decimal de costes para Gemini File Search en F0.

Las tarifas **no se declaran aquí**: se derivan del catálogo compartido de
`llm_gateway`, que es la fuente única de precios del parque. Una copia local
sería una tabla más que actualizar a mano, y el día que divergiera el importe
mostrado dejaría de reconciliarse contra la factura.

La conversión es la identidad: USD por millón de tokens y microUSD por token
son el mismo número.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from llm_gateway.models import CATALOG_VERSION, lookup_model
from pydantic import Field

from chat_strategy_models import MarginalCost
from jurisprudence_case_catalogs import JurisprudenceCaseModel

DEFAULT_FILE_SEARCH_MODEL = "gemini-3.5-flash-lite"
SUPPORTED_FILE_SEARCH_MODELS = (
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
)
PRICING_VERSION = CATALOG_VERSION


def _rates_from_shared_catalog() -> dict[str, tuple[Decimal, Decimal]]:
    """Tarifas de los modelos permitidos, tomadas del catálogo del paquete."""
    rates: dict[str, tuple[Decimal, Decimal]] = {}
    for model in SUPPORTED_FILE_SEARCH_MODELS:
        info = lookup_model(model)
        if info is None:
            raise RuntimeError(
                f"el modelo permitido {model!r} no está en el catálogo compartido; "
                "añádelo en llm_gateway.models antes de permitirlo aquí"
            )
        rates[model] = (info.input_usd_per_mtok, info.output_usd_per_mtok)
    return rates


MODEL_RATES_MICROUSD_PER_TOKEN = _rates_from_shared_catalog()


class GeminiUsage(JurisprudenceCaseModel):
    """Desglose facturable; input excluye los documentos recuperados."""

    input_tokens: int = Field(ge=0)
    retrieved_document_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    usage_complete: bool


def calculate_gemini_request_cost(
    usage: GeminiUsage,
    *,
    model: str = DEFAULT_FILE_SEARCH_MODEL,
) -> MarginalCost:
    """Calcula cualquier generación Gemini, con documentos si los hubiera."""

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


def calculate_gemini_file_search_cost(
    usage: GeminiUsage,
    *,
    model: str = DEFAULT_FILE_SEARCH_MODEL,
) -> MarginalCost:
    """Compatibilidad semántica para el consumidor de Gemini File Search."""

    return calculate_gemini_request_cost(usage, model=model)


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
