"""Fachada del analizador de sentencias sobre el paquete `llm_gateway`.

`gpt_request_for_sentencia` conserva su nombre, su firma y la forma exacta de
su diccionario de retorno: `process_pdf_async` no distingue qué hay detrás, y
por tanto tampoco lo distinguen el CLI por lotes ni la API HTTP. Lo que cambió
es que esta función dejó de *hacer* la llamada para *traducirla*.

Lo que se fue al paquete es lo que cambia con el proveedor: elegir el SDK,
mapear su respuesta, contar tokens, aplicar tarifas, recuperar el JSON de una
respuesta envuelta en prosa. Lo que se queda aquí es lo que cambia con el
producto: qué modelo admite qué temperatura, qué presupuesto de tiempo tiene
una sentencia y qué forma tiene el diccionario que espera el pipeline.

Dos detalles del contrato con OpenAI que la traducción no puede ignorar:

* El *system prompt* viaja como primer mensaje de entrada, no como
  `instructions`. La Responses API rechaza `json_object` si la palabra «json»
  no aparece en la entrada, y el texto de una sentencia no la contiene: solo el
  prompt de sistema la menciona.
* Los modelos de razonamiento rechazan `temperature=0`, así que se les envía 1
  —su valor por defecto—, igual que hacía la implementación anterior.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from llm_gateway import (
    FallbackPolicy,
    LLMGatewayError,
    LLMRequest,
    LLMResult,
    Message,
    ResponseFormat,
    RetryPolicy,
    TimeoutPolicy,
)

from config import PROVIDER_API_KEY_ENV, detect_provider
from gateway_setup import get_gateway

REQUEST_TIMEOUT_SECONDS = 200.0
"""Presupuesto de una sentencia entera, reintento incluido. Heredado del cliente anterior."""

ATTEMPT_TIMEOUT_SECONDS = 90.0
"""Tope por intento, para que el reintento quepa dentro del presupuesto.

Sin él, `per_attempt_seconds` cae en el total: un primer intento colgado 199 s
dejaría un segundo para el reintento y este no serviría de nada. 90 s son 2,3×
la llamada más lenta medida sobre el corpus (26,6 s a 38,3 s)."""

MAX_ATTEMPTS = 2
"""Un lote son 106 sentencias en tandas de 10 durante dos o tres horas: un
límite de ritmo del proveedor perdería esa sentencia como registro de confianza
BAJA. Solo se reintentan errores transitorios, y el intento fallido se factura
y se ve, porque el gateway lo cuenta como cualquier otro."""

SOURCE = "analizador-sentencias"

_REASONING_MODEL_MARKERS = ("gpt-5", "o1")

_PROVIDER_DESCRIPTIONS = {
    "openai": "OpenAI",
    "gemini": "Gemini",
    "groq": "Groq",
    "openrouter": "OpenRouter",
}


async def gpt_request_for_sentencia(
    ai_model: str,
    system_prompt: str,
    pdf_text: str,
    logger: logging.Logger,
    temperature: float = 0,
    response_format: str = "json_object",
    reasoning_effort: str | None = None,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    """Analiza una sentencia con el modelo indicado.

    Args:
        ai_model: Identificador del modelo (p. ej. "gpt-5.6-luna").
        system_prompt: Instrucciones de análisis.
        pdf_text: Texto extraído del PDF, con marcadores de página.
        logger: Logger del pipeline, para los errores.
        temperature: Temperatura (0-1).
        response_format: "json_object" o "text".
        reasoning_effort: nivel admitido por el modelo según el catálogo del gateway.
        max_tokens: Tope de tokens generados.

    Returns:
        El objeto analizado más `cost_usd`, `cost_measurement` y
        `tiempo_ejecucion`; o `{"error": ..., "detail": ...}` si la llamada no
        llegó a producir respuesta. `cost_usd` es `None` cuando el coste no se
        pudo calcular: eso no significa que la llamada fuese gratis.
    """
    started = time.perf_counter()

    faltante = _missing_credential(ai_model)
    if faltante is not None:
        return faltante

    try:
        result = await get_gateway().generate(
            _build_request(
                ai_model=ai_model,
                system_prompt=system_prompt,
                pdf_text=pdf_text,
                temperature=temperature,
                response_format=response_format,
                reasoning_effort=reasoning_effort,
                max_tokens=max_tokens,
            )
        )
    except LLMGatewayError as error:
        logger.error(f"LLM request failed: {error}")
        return {"error": str(error), "detail": "LLM request failed"}
    except Exception as error:  # noqa: BLE001 — el pipeline nunca debe romperse por un PDF
        logger.error(f"LLM request failed: {error}")
        return {"error": str(error), "detail": "LLM request failed"}

    if response_format == "json_object" and not isinstance(result.output, dict):
        # Un JSON válido que no es un objeto —una lista, un número, `null`— no
        # es un análisis. Darlo por bueno haría que `ensure_required_keys`
        # rellenase los campos con valores por defecto y escribiese en el JSONL
        # un registro con aspecto de analizado. El gasto de esta llamada no se
        # pierde: el `UsageSink` ya lo anotó antes de llegar aquí.
        tipo = type(result.output).__name__
        logger.error(f"LLM request failed: la respuesta JSON es {tipo}, no un objeto")
        return {
            "error": f"la respuesta JSON es {tipo}, no un objeto",
            "detail": "LLM request failed",
        }

    return _flatten(result, ai_model=ai_model, started=started, response_format=response_format)


def _missing_credential(ai_model: str) -> dict[str, Any] | None:
    """Falta de clave antes de construir nada, con el mensaje de siempre."""
    provider = detect_provider(ai_model)
    variable = PROVIDER_API_KEY_ENV.get(provider)
    if variable is None or os.getenv(variable):
        return None
    descripcion = _PROVIDER_DESCRIPTIONS.get(provider, provider)
    return {
        "error": f"{variable} not set",
        "detail": f"No API key available for {descripcion} models",
    }


def _build_request(
    *,
    ai_model: str,
    system_prompt: str,
    pdf_text: str,
    temperature: float,
    response_format: str,
    reasoning_effort: str | None,
    max_tokens: int | None,
) -> LLMRequest:
    return LLMRequest(
        model=ai_model,
        system_prompt=system_prompt,
        messages=(Message("user", pdf_text),),
        response_format=(
            ResponseFormat.JSON_OBJECT if response_format == "json_object" else ResponseFormat.TEXT
        ),
        temperature=_temperature_for(ai_model, temperature),
        max_output_tokens=max_tokens,
        reasoning_effort=_reasoning_effort_for(ai_model, reasoning_effort),
        timeout_policy=TimeoutPolicy(
            total_seconds=REQUEST_TIMEOUT_SECONDS,
            per_attempt_seconds_override=ATTEMPT_TIMEOUT_SECONDS,
        ),
        retry_policy=RetryPolicy.transient(max_attempts=MAX_ATTEMPTS),
        # El respaldo sí queda desactivado: si otro modelo contestara, el que
        # el export declara no sería el que respondió, y el coste quedaría
        # atribuido al modelo equivocado.
        fallback_policy=FallbackPolicy.disabled(),
        source=SOURCE,
    )


def _temperature_for(ai_model: str, temperature: float) -> float:
    """Los modelos de razonamiento solo aceptan su temperatura por defecto."""
    if temperature == 0 and _is_reasoning_model(ai_model):
        return 1
    return temperature


def _reasoning_effort_for(ai_model: str, reasoning_effort: str | None) -> Any:
    """Solo OpenAI lo admite; el resto de proveedores lo ignorarían."""
    if not reasoning_effort:
        return None
    if detect_provider(ai_model) != "openai" or not _is_reasoning_model(ai_model):
        return None
    return reasoning_effort


def _is_reasoning_model(ai_model: str) -> bool:
    lowered = ai_model.lower()
    return any(marker in lowered for marker in _REASONING_MODEL_MARKERS)


def _flatten(
    result: LLMResult, *, ai_model: str, started: float, response_format: str
) -> dict[str, Any]:
    """Aplana el resultado tipado a lo que el pipeline lleva años esperando.

    El paquete mantiene separados `output`, `usage`, `execution` y `cost` justo
    para que nadie confunda un recuento de tokens con un campo del análisis.
    Aquí se aplanan porque el JSONL histórico tiene esa forma; el precio es que
    un modelo que emitiese un campo llamado `cost_usd` lo pisaría, igual que
    antes.
    """
    payload: dict[str, Any]
    if response_format == "json_object":
        payload = dict(result.output)
    else:
        payload = {"response": result.text}

    amount = result.cost.amount_usd
    payload["cost_usd"] = float(amount) if amount is not None else None
    payload["cost_measurement"] = result.cost.measurement.value
    payload["tiempo_ejecucion"] = f"{ai_model} - {round(time.perf_counter() - started, 1)}s"
    return payload


__all__ = ["gpt_request_for_sentencia"]
