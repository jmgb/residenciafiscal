"""Construcción del gateway compartido y conexión de sus efectos.

`llm_gateway` no lee el entorno ni guarda credenciales, así que las claves las
entrega la aplicación. Este módulo es el único punto del analizador donde eso
ocurre, y por eso es también donde se conectan los puertos: el recuento de
tokens y coste que el adaptador anterior imprimía a mano lo emite ahora
`LoggingUsageSink` desde el `UsageRecord`, que llega con el proveedor, el
modelo que de verdad respondió y ni una línea del prompt o de la respuesta.

Los precios no se declaran aquí. Salen del catálogo versionado del paquete, que
es exactamente la razón por la que `model_pricing.py` dejó de existir: dos
tablas de precios acaban divergiendo, y la que nadie actualiza sigue facturando
la tarifa del año pasado sin que nada lo delate.

El gateway se construye en la primera llamada y no en el import. Construirlo al
importar obligaría a cualquier módulo que toque `config` a tener claves de
proveedores que quizá no va a usar, y dejaría los tests dependiendo del `.env`.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any

from llm_gateway import CostMeasurement, LLMGateway, ProviderRegistry
from llm_gateway.factories import (
    build_registry,
    create_gemini_client,
    create_groq_client,
    create_openai_client,
    create_openrouter_client,
)
from llm_gateway.ports import UsageRecord

from config import LEGACY_MODEL_PREFIXES, PROVIDER_API_KEY_ENV

logger = logging.getLogger("residenciafiscal.llm")

_PROVIDER_LABELS = {
    "openai": "OpenAI",
    "gemini": "Gemini",
    "groq": "Groq",
    "openrouter": "OpenRouter",
}


class LoggingUsageSink:
    """El libro de cuentas del proyecto: por ahora, una línea de log.

    Sustituye al bloque que cada rama del adaptador repetía. La diferencia no
    es de forma: el sink recibe el desglose de *todos* los intentos facturables
    y la medición del coste, así que un importe estimado deja de parecer una
    medición, y un uso no informado deja de imprimirse como `$0.0000`.
    """

    def record(self, usage: UsageRecord) -> None:
        label = _PROVIDER_LABELS.get(usage.provider, usage.provider)
        tokens = _describe_tokens(usage)
        amount = _describe_cost(usage)
        detail = "" if usage.attempts == 1 else f", {usage.attempts} intentos"
        level = logging.INFO if usage.succeeded else logging.WARNING
        logger.log(level, "💰 %s - %s, %s%s", label, tokens, amount, detail)


class LoggingAlertSink:
    """Un modelo distinto del pedido no puede pasar en silencio."""

    def alert(self, message: str, fields: dict[str, object]) -> None:
        logger.warning("🚨 %s: %s", message, fields)


def _describe_tokens(usage: UsageRecord) -> str:
    if usage.usage.input_tokens is None and usage.usage.output_tokens is None:
        return "uso de tokens no informado"
    entrada = usage.usage.input_tokens
    salida = usage.usage.output_tokens
    razonamiento = usage.usage.reasoning_tokens
    desglose = f" (de ellos {razonamiento} de razonamiento)" if razonamiento else ""
    return (
        f"Tokens: {'?' if entrada is None else entrada} entrada, "
        f"{'?' if salida is None else salida} salida{desglose}"
    )


def _describe_cost(usage: UsageRecord) -> str:
    amount = usage.cost.amount_usd
    if amount is None:
        return "coste no disponible (no es lo mismo que gratis)"
    if usage.cost.measurement is CostMeasurement.ESTIMATED:
        return f"coste ≥ ${amount:.4f} (estimado)"
    return f"${amount:.4f}"


def build_gateway() -> LLMGateway:
    """Un gateway con los proveedores cuya credencial está realmente presente.

    Registrar solo lo que tiene clave hace que pedir un modelo sin credencial
    falle al resolverlo, antes de gastar nada, en lugar de fallar dentro del
    SDK con un mensaje del proveedor.
    """
    clients: dict[str, Any] = {}
    builders = {
        "openai": lambda key: create_openai_client(api_key=key),
        "gemini": lambda key: create_gemini_client(api_key=key),
        "groq": lambda key: create_groq_client(api_key=key),
        "openrouter": lambda key: create_openrouter_client(api_key=key),
    }
    for provider, variable in PROVIDER_API_KEY_ENV.items():
        key = os.getenv(variable)
        if key and key.strip():
            clients[f"{provider}_client"] = builders[provider](key)

    if not clients:
        raise RuntimeError(
            "No hay ninguna credencial de LLM en el entorno. "
            f"Define al menos una de: {', '.join(sorted(PROVIDER_API_KEY_ENV.values()))}"
        )

    registry = build_registry(**clients)
    _registrar_ids_heredados(registry)

    return LLMGateway(
        registry=registry,
        usage_sink=LoggingUsageSink(),
        alert_sink=LoggingAlertSink(),
    )


def _registrar_ids_heredados(registry: ProviderRegistry) -> None:
    """Lo que `detect_provider()` afirma, el registro tiene que poder servirlo.

    Sin esto, un id como `groq-llama-3.3` pasa la validación de credencial
    —`detect_provider()` lo reconoce— y muere después al resolverlo, porque los
    prefijos que el paquete registra para Groq (`llama`, `groq/`) no lo cubren.
    El lote entero saldría como registros fallidos de confianza BAJA.
    """
    disponibles = set(registry.provider_names)
    for prefix, provider in LEGACY_MODEL_PREFIXES:
        if provider in disponibles:
            registry.register(registry.by_name(provider), model_prefixes=(prefix,))


_gateway: LLMGateway | None = None
_lock = threading.Lock()


def get_gateway() -> LLMGateway:
    """El gateway del proceso, construido una sola vez.

    El candado importa: el CLI procesa lotes con `asyncio.gather`, pero los
    tests y la API pueden entrar desde hilos distintos, y construir dos
    registros duplicaría clientes HTTP sin que nadie lo notase.
    """
    global _gateway
    if _gateway is None:
        with _lock:
            if _gateway is None:
                _gateway = build_gateway()
    return _gateway


def reset_gateway() -> None:
    """Olvida el gateway construido. Para tests que cambian el entorno."""
    global _gateway
    with _lock:
        _gateway = None
