"""Redactor de la estrategia A sobre el paquete compartido `llm_gateway`.

Implementa el puerto `StructuredAnswerWriter`, así que
`CurrentStructuredStrategy` solo conoce el contrato local. El dominio jurídico
no cambia: las citas se siguen resolviendo localmente desde IDs de evidencia y
el texto judicial nunca sale del modelo.

Frente al adaptador anterior aporta tres cosas que el comparador necesita:

* uso ausente marcado como incompleto en lugar de contado como cero, que es lo
  que permite que el coste se rotule `ESTIMATED` y no `ACTUAL`;
* reintento acotado y visible ante errores transitorios;
* async nativo, sin `asyncio.to_thread` alrededor de un cliente síncrono.

El fallback de modelo queda desactivado: si A respondiera con un modelo distinto
del que declara, la comparación con B dejaría de ser una comparación.
"""

from __future__ import annotations

from typing import Any

from llm_gateway import (
    FallbackPolicy,
    LLMGateway,
    LLMRequest,
    Message,
    ResponseFormat,
    RetryPolicy,
    TimeoutPolicy,
)
from llm_gateway.models import lookup_model

from chat_answer_contract import StructuredChatAnswerDraft
from structured_answer_writer import (
    ChatWriterRequest,
    ChatWriterResult,
    ChatWriterUsage,
)

WRITER_TIMEOUT_SECONDS = 200.0
"""Presupuesto de la llamada completa, reintento incluido."""

WRITER_ATTEMPT_TIMEOUT_SECONDS = 90.0
"""Tope de cada intento, para que el reintento quepa dentro del presupuesto."""

WRITER_MAX_ATTEMPTS = 2


def _temperature_for(model: str, temperature: float | None) -> float | None:
    """Los modelos de razonamiento de OpenAI solo aceptan su temperatura por defecto.

    `ChatWriterRequest` pide `temperature=0` por defecto, que es lo correcto para
    una tarea jurídica y lo que Gemini venía aceptando. La Responses API, en
    cambio, responde `Unsupported parameter: 'temperature' is not supported with
    this model`, así que con la política del chat apuntando a Luna esa temperatura
    heredada convertía **todas** las respuestas de A en un fallo.

    La condición sale del catálogo del paquete y no de una lista de nombres, para
    que un modelo nuevo no obligue a tocar esto: declarar `reasoning_efforts` es
    lo que identifica a un modelo de razonamiento. Se acota a OpenAI a propósito;
    Gemini 3 también los declara y sí admite temperatura, y quitársela cambiaría
    el determinismo de la estrategia y con él las cifras ya medidas.

    El catálogo no dice qué modelos admiten temperatura, así que la regla vive
    aquí: mientras solo la necesite este proyecto, es su adaptador y no la API
    pública del paquete.
    """
    info = lookup_model(model)
    if info is None or info.provider != "openai" or not info.reasoning_efforts:
        return temperature
    return None


class GatewayChatWriter:
    """Una generación estructurada, sin tools, sin persistencia y sin fallback."""

    def __init__(self, gateway: LLMGateway) -> None:
        self._gateway = gateway

    async def write(self, request: ChatWriterRequest) -> ChatWriterResult:
        result = await self._gateway.generate(
            LLMRequest(
                model=request.model,
                system_prompt=request.system_prompt,
                messages=(Message("user", request.user_prompt),),
                response_format=ResponseFormat.JSON_SCHEMA,
                response_schema=StructuredChatAnswerDraft,
                temperature=_temperature_for(request.model, request.temperature),
                reasoning_effort=request.reasoning_effort,
                timeout_policy=TimeoutPolicy(
                    total_seconds=WRITER_TIMEOUT_SECONDS,
                    per_attempt_seconds_override=WRITER_ATTEMPT_TIMEOUT_SECONDS,
                ),
                retry_policy=RetryPolicy.transient(max_attempts=WRITER_MAX_ATTEMPTS),
                fallback_policy=FallbackPolicy.disabled(),
                source="f0.2-redactor-a",
            )
        )
        return ChatWriterResult(
            draft=_as_draft(result.output),
            usage=_as_writer_usage(result.usage),
            model_used=result.execution.model_used,
        )


def _as_draft(output: Any) -> StructuredChatAnswerDraft:
    """El gateway ya valida contra el schema; esto solo estrecha el tipo."""
    if isinstance(output, StructuredChatAnswerDraft):
        return output
    return StructuredChatAnswerDraft.model_validate(output)


def _as_writer_usage(usage: Any) -> ChatWriterUsage:
    """Traduce al contrato local, que exige enteros.

    El contrato local no admite `None`, así que un valor no informado se
    convierte a 0 **y** marca `usage_complete=False`. Esa bandera es la que
    impide que el coste se declare `ACTUAL`: el cero es de relleno, no una
    medición.

    `output_tokens` se usa tal cual. Desde la v0.5.0 del paquete los
    adaptadores normalizan el razonamiento en el borde, así que ya está dentro
    de esa cifra y `reasoning_tokens` es un desglose suyo, nunca un sumando:
    volver a añadirlo facturaría dos veces lo mismo.
    """
    return ChatWriterUsage(
        input_tokens=usage.input_tokens or 0,
        output_tokens=usage.output_tokens or 0,
        usage_complete=usage.complete,
    )
