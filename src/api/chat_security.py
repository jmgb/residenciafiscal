"""Autenticación interna de la fachada same-origin del chat.

La firma no autentica al usuario final: autentica el salto Netlify → FastAPI y
liga el request-id al body exacto. El navegador nunca ve el secreto.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import time
from threading import Lock

SIGNATURE_VERSION = "v1"
DEFAULT_MAX_AGE_SECONDS = 300
REQUEST_ID_PATTERN = re.compile(
    r"^chat-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


class ReplayCache:
    """Cache de un solo proceso para bloquear replays durante la ventana HMAC."""

    def __init__(self, *, ttl_seconds: int = DEFAULT_MAX_AGE_SECONDS) -> None:
        self._ttl_seconds = ttl_seconds
        self._entries: dict[str, float] = {}
        self._lock = Lock()

    def claim(self, request_id: str, *, now: float | None = None) -> bool:
        current = time.time() if now is None else now
        with self._lock:
            expired = [key for key, expires_at in self._entries.items() if expires_at <= current]
            for key in expired:
                del self._entries[key]
            if request_id in self._entries:
                return False
            self._entries[request_id] = current + self._ttl_seconds
            return True


_replay_cache = ReplayCache()


def body_sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _signing_payload(timestamp: int, request_id: str, digest: str) -> bytes:
    return f"chat-proxy/{SIGNATURE_VERSION}\n{timestamp}\n{request_id}\n{digest}".encode()


def sign_chat_request(secret: str, timestamp: int, request_id: str, body: bytes) -> str:
    if not secret:
        raise ValueError("falta el secreto de firma")
    if not REQUEST_ID_PATTERN.fullmatch(request_id):
        raise ValueError("request_id inválido")
    digest = body_sha256(body)
    signature = hmac.new(
        secret.encode(), _signing_payload(timestamp, request_id, digest), hashlib.sha256
    ).hexdigest()
    return f"{SIGNATURE_VERSION}={signature}"


def verify_chat_request(
    secret: str,
    *,
    timestamp: str | int | None,
    request_id: str | None,
    signature: str | None,
    body: bytes,
    body_sha256: str | None = None,
    replay_cache: ReplayCache | None = None,
    now: float | None = None,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
) -> None:
    """Valida integridad, frescura y unicidad de una petición firmada."""
    if not secret or not timestamp or not request_id or not signature:
        raise ValueError("firma ausente")
    if not REQUEST_ID_PATTERN.fullmatch(request_id):
        raise ValueError("request_id inválido")
    try:
        parsed_timestamp = int(timestamp)
    except (TypeError, ValueError) as error:
        raise ValueError("timestamp inválido") from error
    current = time.time() if now is None else now
    if abs(current - parsed_timestamp) > max_age_seconds:
        raise ValueError("firma caducada")

    digest = hashlib.sha256(body).hexdigest()
    if body_sha256 is not None and (
        len(body_sha256) != 64 or not hmac.compare_digest(body_sha256.lower(), digest)
    ):
        raise ValueError("hash del body inválido")
    expected = sign_chat_request(secret, parsed_timestamp, request_id, body)
    if not hmac.compare_digest(signature, expected):
        raise ValueError("firma inválida")
    cache = replay_cache or _replay_cache
    if not cache.claim(request_id, now=current):
        raise ValueError("petición reutilizada")
