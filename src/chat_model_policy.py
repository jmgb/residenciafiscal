"""Política de inferencia del chat, separada del pipeline offline del corpus."""

import os

from dotenv import load_dotenv
from llm_gateway import ReasoningEffort
from llm_gateway.models import lookup_model

load_dotenv()

CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-5.6-luna").strip()
CHAT_REASONING_EFFORT: ReasoningEffort = "high"
"""Tipado con el literal del paquete: un esfuerzo inválido se ve al comprobar
tipos, no al recibir un 400 del proveedor.

`max` se descartó por lo que cuesta y no por lo que rinde. Frente a `medium`
multiplicaba por 3,3 la latencia y por 7 los tokens de salida, y en un chat que
no puede transmitir tokens según se generan eso es tiempo de pantalla en blanco
pagado a precio de salida. Nadie había medido qué calidad compraba a cambio."""


def _fallback_models() -> tuple[str, ...]:
    raw = os.getenv("CHAT_FALLBACK_MODELS", "gpt-5.6-terra")
    return tuple(dict.fromkeys(model.strip() for model in raw.split(",") if model.strip()))


CHAT_FALLBACK_MODELS = _fallback_models()
"""Modelos alternativos en el orden que ejecutará el gateway."""

_chat_model_info = lookup_model(CHAT_MODEL)
if _chat_model_info is None or not _chat_model_info.reasoning_efforts:
    raise RuntimeError(f"El catálogo del gateway no declara reasoning_efforts para {CHAT_MODEL}")

CHAT_SUPPORTED_REASONING_EFFORTS = _chat_model_info.reasoning_efforts
if CHAT_REASONING_EFFORT not in CHAT_SUPPORTED_REASONING_EFFORTS:
    raise RuntimeError(
        f"{CHAT_REASONING_EFFORT} no está admitido por {CHAT_MODEL} en el catálogo del gateway"
    )

for _fallback_model in CHAT_FALLBACK_MODELS:
    if lookup_model(_fallback_model) is None:
        raise RuntimeError(f"El catálogo del gateway no declara el fallback {_fallback_model}")
