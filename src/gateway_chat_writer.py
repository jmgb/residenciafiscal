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

from chat_answer_contract import StructuredChatAnswerDraft
from structured_answer_writer import (
    ChatWriterRequest,
    ChatWriterResult,
    ChatWriterUsage,
)

WRITER_TIMEOUT_SECONDS = 200.0
"""Presupuesto de la llamada completa, reintento incluido."""

WRITER_ATTEMPT_TIMEOUT_SECONDS = 90.0
"""Tope de cada intento, para que el reintento quepa dentro del presupuesto.

La cifra sigue al esfuerzo declarado en `chat_model_policy`, porque la latencia
la manda el razonamiento y no el tamaño de la pregunta. Con `max` hubo que
subirla: cuatro respuestas reales tardaron 81,0 s, 81,7 s, 93,4 s y 95,9 s, dos
de ellas por encima de este tope, y la misma pregunta caía a un lado y al otro
según la ejecución. Con `high`, ocho respuestas a las mismas preguntas se
reparten entre 11,1 s y 36,7 s: los 90 s son 2,4× el peor caso.

No conviene dejarlo más alto «por si acaso». Un presupuesto holgado no evita
ningún corte que 90 s no eviten ya, y en cambio alarga hasta 300 s lo que tarda
en rendirse una llamada colgada, que en un chat es tiempo del usuario mirando
una pantalla vacía.

Los 200 s de total mantienen que quepan dos intentos: un tope por intento que no
quepa dos veces en el presupuesto deja el reintento en decorativo."""

WRITER_MAX_ATTEMPTS = 2


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
                temperature=request.temperature,
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
            cost=result.cost,
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
