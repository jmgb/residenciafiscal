"""Fachada estable para traducir llamadas del producto al gateway neutral."""

from __future__ import annotations

from typing import Protocol

from llm_gateway import (
    FallbackPolicy,
    LLMRequest,
    LLMResult,
    Message,
    ReasoningEffort,
    ResponseFormat,
    RetryPolicy,
    TimeoutPolicy,
)
from pydantic import BaseModel


class GatewayPort(Protocol):
    """Puerto mínimo que necesita la fachada; lo implementa `LLMGateway`."""

    async def generate(self, request: LLMRequest) -> LLMResult: ...


async def gpt_request(
    ai_model: str,
    system_prompt: str | None,
    user_message: str,
    *,
    gateway: GatewayPort | None = None,
    temperature: float | None = None,
    reasoning_effort: ReasoningEffort | None = None,
    response_format: ResponseFormat = ResponseFormat.TEXT,
    response_schema: type[BaseModel] | None = None,
    fallback_models: tuple[str, ...] = (),
    timeout_policy: TimeoutPolicy | None = None,
    retry_policy: RetryPolicy | None = None,
    request_id: str | None = None,
    source: str | None = None,
) -> LLMResult:
    """Conserva el punto de entrada del consumidor y delega toda la llamada.

    La función no conoce SDKs, credenciales, proveedores ni reglas de fallback:
    traduce el contrato estable ``(modelo, sistema, usuario)`` a
    :class:`llm_gateway.LLMRequest`. Los sinks conectados al gateway reciben
    uso, coste y alertas de fallback; el resultado conserva la forma neutral del
    paquete para que cada consumidor lo adapte a su contrato de dominio.
    """
    if gateway is None:
        from gateway_setup import get_gateway

        gateway = get_gateway()

    return await gateway.generate(
        LLMRequest(
            model=ai_model,
            system_prompt=system_prompt,
            messages=(Message("user", user_message),),
            temperature=temperature,
            reasoning_effort=reasoning_effort,
            response_format=response_format,
            response_schema=response_schema,
            fallback_policy=FallbackPolicy.models_in_order(*fallback_models),
            timeout_policy=timeout_policy or TimeoutPolicy(),
            retry_policy=retry_policy or RetryPolicy.disabled(),
            request_id=request_id,
            source=source,
        )
    )
