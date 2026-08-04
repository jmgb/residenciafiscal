"""Contrato HTTP/SSE y composition boundary del chat comparativo.

La ruta valida y persiste el ciclo de vida; no consulta tablas ni conoce
proveedores. El único texto que sale a observabilidad es un identificador y el
único texto que sale al navegador es el contrato SSE ya saneado.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import secrets
import time
import uuid
from collections.abc import AsyncIterator
from typing import Annotated, Literal, Protocol

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ValidationError, field_validator

from api.chat_rate_limit import chat_rate_limiter
from api.chat_security import REQUEST_ID_PATTERN
from chat_strategy_models import ComparisonReport

CHAT_PROTOCOL_VERSION = "2"
MAX_REQUEST_BYTES = 200_000
MAX_MESSAGES = 20
MAX_MESSAGE_CHARS = 500
HEARTBEAT_SECONDS = 15.0
IDENTIFIER_PATTERN = re.compile(r"^[\w-]{1,128}$")
COUNTRY_PATH_PATTERN = re.compile(r"^/[a-z0-9-]{1,63}$")
DEFAULT_COUNTRY_PATH = "/espana"
logger = logging.getLogger("residenciafiscal.chat")


class ChatComparisonRunner(Protocol):
    async def compare(self, question: str, *, request_id: str) -> ComparisonReport: ...


class ChatRepository(Protocol):
    async def record(
        self,
        *,
        request_id: str,
        conversation_id: str,
        user_message_id: str,
        country_path: str,
        question: str,
    ) -> str: ...

    async def complete(self, *, request_id: str, report: ComparisonReport) -> None: ...

    async def fail(self, *, request_id: str, status: str, failure_code: str) -> None: ...


class ChatRequestMessage(BaseModel):
    """Mensaje del historial local; solo el último usuario sale del navegador."""

    id: str | None = None
    role: Literal["user", "assistant"]
    content: Annotated[str, Field(min_length=1, max_length=MAX_MESSAGE_CHARS)]

    @field_validator("id")
    @classmethod
    def discard_invalid_identifier(cls, value: str | None) -> str | None:
        # La V1 sustituye un identificador mal formado por uno generado en vez
        # de rechazar la petición. Endurecerlo aquí devolvería un error donde
        # producción responde, y eso es una divergencia de contrato.
        return value if value is not None and IDENTIFIER_PATTERN.fullmatch(value) else None


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    country_path: str = DEFAULT_COUNTRY_PATH
    messages: Annotated[list[ChatRequestMessage], Field(min_length=1, max_length=MAX_MESSAGES)]

    @field_validator("conversation_id")
    @classmethod
    def discard_invalid_conversation(cls, value: str | None) -> str | None:
        return value if value is not None and IDENTIFIER_PATTERN.fullmatch(value) else None

    @field_validator("country_path")
    @classmethod
    def default_invalid_country(cls, value: str) -> str:
        return value if COUNTRY_PATH_PATTERN.fullmatch(value) else DEFAULT_COUNTRY_PATH


def _enabled(name: str, *, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes"}


def get_chat_comparison_runner() -> ChatComparisonRunner:
    """Construye el runtime solo si el operador ha habilitado llamadas de pago."""
    from api.chat_runtime import get_production_chat_runner

    return get_production_chat_runner()


def get_chat_repository() -> ChatRepository | None:
    """Devuelve el adaptador RPC si el despliegue tiene persistencia configurada."""
    from api.chat_persistence import get_production_chat_repository

    return get_production_chat_repository()


async def read_chat_body(request: Request) -> bytes:
    """Lee el cuerpo abortando en cuanto supera el límite, sin bufferizarlo entero."""
    declared_length = request.headers.get("content-length")
    if declared_length and declared_length.isdigit() and int(declared_length) > MAX_REQUEST_BYTES:
        raise HTTPException(status_code=413, detail="Petición demasiado grande")
    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > MAX_REQUEST_BYTES:
            raise HTTPException(status_code=413, detail="Petición demasiado grande")
        chunks.append(chunk)
    return b"".join(chunks)


def parse_chat_request(body: bytes) -> ChatRequest:
    """Reproduce el 400 de la V1; el 422 de Pydantic sería otro contrato."""
    try:
        return ChatRequest.model_validate_json(body)
    except ValidationError as error:
        raise HTTPException(status_code=400, detail="Petición inválida") from error


async def verify_chat_proxy(
    request: Request,
    body: Annotated[bytes, Depends(read_chat_body)],
    x_chat_timestamp: Annotated[str | None, Header()] = None,
    x_chat_request_id: Annotated[str | None, Header()] = None,
    x_chat_signature: Annotated[str | None, Header()] = None,
    x_chat_body_sha256: Annotated[str | None, Header()] = None,
    x_chat_proxy_secret: Annotated[str | None, Header()] = None,
) -> None:
    """Valida HMAC en preview/producción y conserva compatibilidad local.

    La ruta local no pasa por la fachada (D8). Un despliegue real debe activar
    ``CHAT_PROXY_HMAC_REQUIRED=true``; el secreto estático solo se acepta en el
    modo legado explícito para no romper la V1 durante la ventana de rollback.
    """
    if not _enabled("CHAT_COMPARISON_ENABLED"):
        return

    hmac_required = _enabled("CHAT_PROXY_HMAC_REQUIRED") or bool(
        os.getenv("CHAT_HMAC_SECRET", "").strip()
    )
    if hmac_required:
        from api.chat_security import verify_chat_request

        secret = os.getenv("CHAT_HMAC_SECRET", os.getenv("CHAT_PROXY_SECRET", "")).strip()
        try:
            verify_chat_request(
                secret,
                timestamp=x_chat_timestamp,
                request_id=x_chat_request_id,
                signature=x_chat_signature,
                body=body,
                body_sha256=x_chat_body_sha256,
            )
        except ValueError as error:
            raise HTTPException(status_code=403, detail="Proxy no autorizado") from error
        return

    expected = os.getenv("CHAT_PROXY_SECRET", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="Falta el secreto del proxy")
    if x_chat_proxy_secret is None or not secrets.compare_digest(x_chat_proxy_secret, expected):
        raise HTTPException(status_code=403, detail="Proxy no autorizado")


def enforce_chat_rate_limit(
    x_chat_client_key: Annotated[str | None, Header()] = None,
) -> None:
    """Aplica la cuota autoritativa del backend.

    La clave es la que firma la fachada. `X-Forwarded-For` no se usa: lo fija
    quien llama y convertiría la cuota en una sugerencia. Sin clave firmada,
    todo el tráfico comparte un único cubo en vez de uno por petición.
    """
    if not _enabled("CHAT_RATE_LIMIT_ENABLED"):
        return
    key = (x_chat_client_key or "").strip() or "unsigned"
    if not chat_rate_limiter.allow(key):
        raise HTTPException(status_code=429, detail="Demasiadas consultas seguidas")


def _event(name: str, data: object) -> bytes:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {name}\ndata: {payload}\n\n".encode()


def comparison_events(report: ComparisonReport, *, request_id: str | None = None) -> list[bytes]:
    """Convierte un informe terminal en el protocolo comparativo v2.

    Los límites viajan tal cual: son ya texto público, y sustituirlos por un
    genérico borraría el motivo real —por ejemplo, qué evidencia se retiró— que
    la V1 sí muestra. Que ningún mensaje de proveedor llegue hasta aquí es
    responsabilidad de cada estrategia, no de la serialización.
    """
    events: list[bytes] = []
    for answer in report.answers:
        events.append(_event("answer_start", {"strategy": answer.strategy}))
        if answer.text:
            events.append(_event("token", {"strategy": answer.strategy, "text": answer.text}))
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
                    "claims": [claim.model_dump(mode="json") for claim in answer.claims],
                    "limits": list(answer.limits),
                    "cost": answer.cost.model_dump(mode="json"),
                    "model": answer.model,
                    "latency_ms": answer.latency_ms,
                },
            )
        )
    # El terminal lleva el `request_id`: es lo que ata el voto ciego a la
    # petición persistida. Sin él la UI recibe la comparación pero no puede
    # votarla.
    events.append(_event("done", {"request_id": request_id or report.request_id}))
    return events


def _request_id(header_value: str | None) -> str:
    request_id = header_value or f"chat-{uuid.uuid4()}"
    if not REQUEST_ID_PATTERN.fullmatch(request_id):
        raise HTTPException(status_code=400, detail="Identificador de petición inválido")
    return request_id


def _deadline_seconds() -> float:
    raw_value = os.getenv("CHAT_BACKEND_DEADLINE_SECONDS", "90").strip()
    try:
        value = float(raw_value)
    except ValueError:
        return 90.0
    return value if value > 0 else 90.0


async def _reconcile_failure(
    repository: ChatRepository | None,
    *,
    request_id: str,
    status: str,
    failure_code: str,
) -> None:
    if repository is None:
        return
    try:
        await repository.fail(request_id=request_id, status=status, failure_code=failure_code)
    except Exception:
        logger.error(
            "No se pudo reconciliar el fallo del chat",
            extra={"request_id": request_id, "failure_code": "persistence_error"},
        )


async def _heartbeats(
    comparison: asyncio.Future[ComparisonReport], deadline_seconds: float
) -> AsyncIterator[bytes]:
    """Emite comentarios SSE mientras el comparador trabaja, dentro del deadline."""
    started = time.monotonic()
    while True:
        remaining = deadline_seconds - (time.monotonic() - started)
        if remaining <= 0:
            comparison.cancel()
            raise TimeoutError
        try:
            await asyncio.wait_for(
                asyncio.shield(comparison), timeout=min(HEARTBEAT_SECONDS, remaining)
            )
            return
        except TimeoutError:
            if comparison.done():
                return
            yield b": keep-alive\n\n"


def _latest_question(payload: ChatRequest) -> tuple[str, str]:
    for message in reversed(payload.messages):
        if message.role == "user" and message.content.strip():
            return message.content.strip(), message.id or f"message-{uuid.uuid4()}"
    raise HTTPException(status_code=400, detail="Falta una pregunta de usuario")


router = APIRouter()


@router.post("/chat")
async def chat(
    body: Annotated[bytes, Depends(read_chat_body)],
    _proxy_verified: Annotated[None, Depends(verify_chat_proxy)],
    _rate_limit_verified: Annotated[None, Depends(enforce_chat_rate_limit)],
    runner: Annotated[ChatComparisonRunner, Depends(get_chat_comparison_runner)],
    repository: Annotated[ChatRepository | None, Depends(get_chat_repository)],
    x_chat_request_id: Annotated[str | None, Header()] = None,
) -> StreamingResponse:
    payload = parse_chat_request(body)
    question, user_message_id = _latest_question(payload)
    request_id = _request_id(x_chat_request_id)
    conversation_id = payload.conversation_id or f"conversation-{uuid.uuid4()}"

    async def stream() -> AsyncIterator[bytes]:
        effective_request_id = request_id
        request_recorded = False
        request_terminal = False
        try:
            if repository is not None:
                effective_request_id = await repository.record(
                    request_id=request_id,
                    conversation_id=conversation_id,
                    user_message_id=user_message_id,
                    country_path=payload.country_path,
                    question=question,
                )
                request_recorded = True
            comparison = asyncio.ensure_future(
                runner.compare(question, request_id=effective_request_id)
            )
            # El comparador no emite tokens: sin latido, un intermediario puede
            # cerrar una conexión inactiva antes de que llegue la respuesta.
            async for beat in _heartbeats(comparison, _deadline_seconds()):
                yield beat
            report = comparison.result()
            if repository is not None:
                await repository.complete(request_id=effective_request_id, report=report)
            request_terminal = True
            for event in comparison_events(report, request_id=effective_request_id):
                yield event
        except asyncio.CancelledError:
            if request_recorded and not request_terminal:
                await _reconcile_failure(
                    repository,
                    request_id=effective_request_id,
                    status="timed_out",
                    failure_code="client_cancelled",
                )
            raise
        except TimeoutError:
            logger.error(
                "Deadline agotado en el comparador de chat",
                extra={"request_id": request_id, "failure_code": "comparison_timeout"},
            )
            if request_recorded and not request_terminal:
                await _reconcile_failure(
                    repository,
                    request_id=effective_request_id,
                    status="timed_out",
                    failure_code="comparison_timeout",
                )
            yield _event(
                "error",
                {
                    "code": "comparison_timeout",
                    "message": "No se ha podido completar la comparación.",
                    "retryable": True,
                },
            )
        except Exception:
            logger.error(
                "Fallo del comparador de chat",
                extra={"request_id": request_id, "failure_code": "comparison_error"},
            )
            if request_recorded and not request_terminal:
                await _reconcile_failure(
                    repository,
                    request_id=effective_request_id,
                    status="failed",
                    failure_code="comparison_error",
                )
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
