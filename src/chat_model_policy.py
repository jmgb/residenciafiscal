"""Política de inferencia del chat, separada del pipeline offline del corpus."""

from llm_gateway.models import lookup_model

CHAT_MODEL = "gpt-5.6-luna"
CHAT_REASONING_EFFORT = "max"

_chat_model_info = lookup_model(CHAT_MODEL)
if _chat_model_info is None or not _chat_model_info.reasoning_efforts:
    raise RuntimeError(f"El catálogo del gateway no declara reasoning_efforts para {CHAT_MODEL}")

CHAT_SUPPORTED_REASONING_EFFORTS = _chat_model_info.reasoning_efforts
if CHAT_REASONING_EFFORT not in CHAT_SUPPORTED_REASONING_EFFORTS:
    raise RuntimeError(
        f"{CHAT_REASONING_EFFORT} no está admitido por {CHAT_MODEL} en el catálogo del gateway"
    )
