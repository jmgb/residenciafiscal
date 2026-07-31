"""Los precios de F0 se derivan del catálogo compartido, no de una copia local.

Una tarifa duplicada aquí es una tarifa que alguien tendrá que acordarse de
actualizar dos veces, y el día que no lo haga la comparación A/B dejará de
poder reconciliarse contra la factura.
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chat_strategy_costs import (  # noqa: E402
    MODEL_RATES_MICROUSD_PER_TOKEN,
    PRICING_VERSION,
    SUPPORTED_FILE_SEARCH_MODELS,
)


class TestRatesComeFromTheSharedCatalogue:
    @pytest.mark.parametrize("model", SUPPORTED_FILE_SEARCH_MODELS)
    def test_every_supported_model_matches_the_package(self, model: str) -> None:
        from llm_gateway.models import lookup_model

        info = lookup_model(model)
        assert info is not None, f"{model} no está en el catálogo compartido"

        local_input, local_output = MODEL_RATES_MICROUSD_PER_TOKEN[model]
        assert local_input == info.input_usd_per_mtok
        assert local_output == info.output_usd_per_mtok

    def test_the_pricing_version_is_the_shared_one(self) -> None:
        from llm_gateway.models import CATALOG_VERSION

        assert PRICING_VERSION == CATALOG_VERSION

    def test_no_rate_is_hardcoded_locally(self) -> None:
        """La tabla local debe construirse, no escribirse a mano."""
        source = (Path(__file__).resolve().parents[1] / "src" / "chat_strategy_costs.py").read_text(
            encoding="utf-8"
        )

        assert 'Decimal("0.3")' not in source
        assert 'Decimal("2.5")' not in source
        assert 'Decimal("7.5")' not in source


class TestCostsStillBehave:
    def test_a_known_model_is_priced_as_before(self) -> None:
        from chat_strategy_costs import GeminiUsage, calculate_gemini_file_search_cost

        cost = calculate_gemini_file_search_cost(
            GeminiUsage(
                input_tokens=1_000_000,
                retrieved_document_tokens=0,
                output_tokens=0,
                usage_complete=True,
            ),
            model="gemini-3.5-flash-lite",
        )

        assert cost.amount_usd == Decimal("0.300000")
        assert cost.measurement == "ACTUAL"

    def test_an_unsupported_model_still_raises(self) -> None:
        """B solo puede correr sobre File Search, que es una capacidad de Gemini.

        Ahora hay dos motivos distintos para rechazar un modelo, y conviene que
        el mensaje los distinga: uno catalogado pero ajeno a File Search —Luna,
        que sí tiene tarifa y sí usa A— no es lo mismo que uno inexistente.
        """
        from chat_strategy_costs import GeminiUsage, calculate_gemini_file_search_cost

        usage = GeminiUsage(
            input_tokens=1,
            retrieved_document_tokens=0,
            output_tokens=1,
            usage_complete=True,
        )

        with pytest.raises(ValueError, match="no admitido en File Search"):
            calculate_gemini_file_search_cost(usage, model="modelo-inexistente")

        with pytest.raises(ValueError, match="no admitido en File Search"):
            calculate_gemini_file_search_cost(usage, model="gpt-5.6-luna")

    def test_a_model_outside_the_catalogue_has_no_rate(self) -> None:
        """El cálculo general acepta cualquier modelo catalogado, no cualquiera."""
        from chat_strategy_costs import GeminiUsage, calculate_request_cost

        with pytest.raises(ValueError, match="sin tarifa en el catálogo"):
            calculate_request_cost(
                GeminiUsage(
                    input_tokens=1,
                    retrieved_document_tokens=0,
                    output_tokens=1,
                    usage_complete=True,
                ),
                model="modelo-inexistente",
            )
