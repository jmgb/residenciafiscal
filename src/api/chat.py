"""Contrato HTTP/SSE del comparador de chat.

La ruta no conoce proveedores ni corpus. Recibe una conversación saneada,
selecciona la última pregunta del usuario y serializa el informe que entrega el
composition root de producción. Nunca registra el texto recibido.
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import uuid
from collections.abc import AsyncIterator
from typing import Annotated, Literal, Protocol

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from chat_strategy_models import ComparisonReport

CHAT_PROTOCOL_VERSION = "2"
MAX_MESSAGES = 20
MAX_MESSAGE_CHARS = 8_000
PUBLIC_STRATEGY_ERROR_LIMIT = "No se ha podido completar esta estrategia."
logger = logging.getLogger("residenciafiscal.chat")


class ChatComparisonRunner(Protocol):
    async def compare(self, question: str, *, request_id: str) -> ComparisonReport: ...


class ChatRequestMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: Annotated[str, Field(min_length=1, max_length=MAX_MESSAGE_CHARS)]


class ChatRequest(BaseModel):
    messages: Annotated[list[ChatRequestMessage], Field(min_length=1, max_length=MAX_MESSAGES)]


def get_chat_comparison_runner() -> ChatComparisonRunner:
    """Construye el runtime solo si el operador ha habilitado llamadas de pago."""
    from api.chat_runtime import get_production_chat_runner

    return get_production_chat_runner()


def verify_chat_proxy(
    x_chat_proxy_secret: Annotated[str | None, Header()] = None,
) -> None:
    """Impide saltarse el rate limit de Netlify cuando el chat está activo."""
    enabled = os.getenv("CHAT_COMPARISON_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    if not enabled:
        return
    expected = os.getenv("CHAT_PROXY_SECRET", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="Falta el secreto del proxy")
    if x_chat_proxy_secret is None or not secrets.compare_digest(x_chat_proxy_secret, expected):
        raise HTTPException(status_code=403, detail="Proxy no autorizado")


def _event(name: str, data: object) -> bytes:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {name}\ndata: {payload}\n\n".encode()


def comparison_events(report: ComparisonReport) -> list[bytes]:
    """Convierte un informe terminal en el protocolo comparativo v2."""
    events: list[bytes] = []
    for answer in report.answers:
        public_limits = (
            (PUBLIC_STRATEGY_ERROR_LIMIT,) if answer.status == "error" else answer.limits
        )
        events.append(_event("answer_start", {"strategy": answer.strategy}))
        if answer.text:
            events.append(
                _event(
                    "token",
                    {"strategy": answer.strategy, "text": answer.text},
                )
            )
        events.append(
            _event(
                "sources",
                {
                    "strategy": answer.strategy,
                    "sources": [source.model_dump(mode="json") for source in answer.sources],
                },
            )
        )
        events.append(
            _event(
                "answer_done",
                {
                    "strategy": answer.strategy,
                    "status": answer.status,
                    "limits": list(public_limits),
                    "cost": answer.cost.model_dump(mode="json"),
                    "model": answer.model,
                    "latency_ms": answer.latency_ms,
                },
            )
        )
    events.append(_event("done", {}))
    return events


router = APIRouter()


@router.post("/chat")
async def chat(
    payload: ChatRequest,
    _proxy_verified: Annotated[None, Depends(verify_chat_proxy)],
    runner: Annotated[ChatComparisonRunner, Depends(get_chat_comparison_runner)],
) -> StreamingResponse:
    question = next(
        (
            message.content.strip()
            for message in reversed(payload.messages)
            if message.role == "user" and message.content.strip()
        ),
        None,
    )
    if question is None:
        raise HTTPException(status_code=400, detail="Falta una pregunta de usuario")

    request_id = f"chat-{uuid.uuid4()}"

    async def stream() -> AsyncIterator[bytes]:
        try:
            report = await runner.compare(question, request_id=request_id)
            for event in comparison_events(report):
                yield event
        except Exception:
            # No incluir pregunta ni respuesta. El request_id permite correlacionar
            # este fallo con los logs de estrategia que hayan llegado a escribirse.
            logger.exception("Fallo del comparador de chat", extra={"request_id": request_id})
            yield _event(
                "error",
                {
                    "code": "comparison_failed",
                    "message": "No se ha podido completar la comparación.",
                    "retryable": True,
                },
            )

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-store",
            "X-Accel-Buffering": "no",
            "X-Chat-Protocol": CHAT_PROTOCOL_VERSION,
        },
    )
