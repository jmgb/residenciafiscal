from __future__ import annotations

import pytest

from config import LEGACY_MODEL_PREFIXES, detect_provider


def test_modelos_se_enrutan_al_proveedor_que_expresa_su_id() -> None:
    assert detect_provider("gpt-5.6-luna") == "openai"
    assert detect_provider("gemini-3.6-flash") == "gemini"
    assert detect_provider("models/gemini-3.6-flash") == "gemini"
    assert detect_provider("groq-llama-3.3") == "groq"
    assert detect_provider("meta-llama/llama-4-scout-17b-16e-instruct") == "groq"
    assert detect_provider("openai/gpt-oss-120b") == "groq"
    assert detect_provider("google/gemini-3.6-flash") == "openrouter"
    assert detect_provider("anthropic/claude-sonnet") == "openrouter"


@pytest.mark.parametrize(("prefix", "provider"), LEGACY_MODEL_PREFIXES)
def test_el_registro_sirve_todo_lo_que_detect_provider_afirma(prefix: str, provider: str) -> None:
    """Validar una credencial y no poder resolver el modelo es lo peor de ambos.

    El id pasaría la comprobación de clave y moriría después sin adaptador, así
    que el lote entero saldría como registros fallidos de confianza BAJA sin
    que el mensaje mencione siquiera al proveedor.
    """
    from types import SimpleNamespace

    from llm_gateway.factories import build_registry

    from gateway_setup import _registrar_ids_heredados

    modelo = f"{prefix}modelo-heredado"
    assert detect_provider(modelo) == provider

    registry = build_registry(
        openai_client=SimpleNamespace(),
        gemini_client=SimpleNamespace(),
        groq_client=SimpleNamespace(),
        openrouter_client=SimpleNamespace(),
    )
    _registrar_ids_heredados(registry)

    assert registry.resolve(modelo).name == provider


def test_la_api_solo_ofrece_modelos_con_tarifa_conocida() -> None:
    """Un modelo sin tarifa gasta dinero y lo declara como `UNAVAILABLE`.

    La allowlist de `/analizar` es la única superficie donde un tercero elige
    modelo, así que ofrecer ahí uno que el catálogo no sabe tarifar produce un
    gasto real sin importe reconciliable.
    """
    from llm_gateway.models import lookup_model

    from api.main import MODELOS_PERMITIDOS

    sin_tarifa = sorted(m for m in MODELOS_PERMITIDOS if lookup_model(m) is None)

    assert sin_tarifa == [], (
        f"modelos ofrecidos sin tarifa en el catálogo: {sin_tarifa}; "
        "añádelos en llm_gateway.models antes de permitirlos aquí"
    )
