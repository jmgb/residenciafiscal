"""Cálculo decimal de costes de las dos estrategias del comparador F0.

Las tarifas **no se declaran aquí**: se derivan del catálogo compartido de
`llm_gateway`, que es la fuente única de precios del parque. Una copia local
sería una tabla más que actualizar a mano, y el día que divergiera el importe
mostrado dejaría de reconciliarse contra la factura.

La conversión es la identidad: USD por millón de tokens y microUSD por token
son el mismo número.

Las dos estrategias ya no comparten modelo, así que tarifar y permitir son
cosas distintas. `SUPPORTED_FILE_SEARCH_MODELS` sigue siendo la lista de lo que
**B** puede usar —File Search es una capacidad de Gemini y ahí no cabe otro
proveedor—, pero el cálculo del importe acepta cualquier modelo catalogado: A
corre sobre el modelo que declare `chat_model_policy`, y negarle tarifa por no
estar en la lista de B lo mataba después de haber pagado la llamada.
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
    "gemini-3.8-flash",
)
PRICING_VERSION = CATALOG_VERSION


def _rate_for(model: str) -> tuple[Decimal, Decimal]:
    """Tarifa de cualquier modelo catalogado, sin lista local que mantener."""
    info = lookup_model(model)
    if info is None:
        raise ValueError(
            f"modelo sin tarifa en el catálogo compartido: {model}; "
            "añádelo en llm_gateway.models antes de usarlo aquí"
        )
    return info.input_usd_per_mtok, info.output_usd_per_mtok


def _rates_from_shared_catalog() -> dict[str, tuple[Decimal, Decimal]]:
    """Tarifas de los modelos que B puede usar, comprobadas al importar.

    Sirve de gate, no de fuente: si alguien añade un modelo a la lista de File
    Search sin tarifa en el catálogo, esto falla al arrancar y no a mitad de una
    comparación ya pagada.
    """
    try:
        return {model: _rate_for(model) for model in SUPPORTED_FILE_SEARCH_MODELS}
    except ValueError as error:
        raise RuntimeError(f"modelo permitido en File Search sin tarifa: {error}") from error


MODEL_RATES_MICROUSD_PER_TOKEN = _rates_from_shared_catalog()


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
    """Importe de B, la única estrategia que aún calcula el suyo.

    A dejó de hacerlo: su importe lo mide el gateway y viaja en
    `ChatWriterResult.cost`. B no puede delegarlo porque mide sobre la
    Interactions API, fuera del paquete, y porque su coste incluye los tokens de
    documento recuperado, que se facturan como contexto de entrada y ninguna
    llamada del gateway produce.
    """

    if model not in SUPPORTED_FILE_SEARCH_MODELS:
        raise ValueError(
            f"modelo no admitido en File Search: {model}; "
            f"permitidos: {', '.join(SUPPORTED_FILE_SEARCH_MODELS)}"
        )
    input_rate, output_rate = _rate_for(model)
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
    """Coste no disponible cuando un fallo no devuelve uso facturable."""

    return unavailable_cost()


def unavailable_cost() -> MarginalCost:
    """Representa una ausencia de medición, nunca un coste cero."""

    return MarginalCost(
        amount_usd=None,
        cost_microusd=None,
        measurement="UNAVAILABLE",
        pricing_version=PRICING_VERSION,
        input_tokens=None,
        output_tokens=None,
        retrieved_document_tokens=None,
    )
