"""Model pricing configuration for AI cost tracking.

Prices are in USD per million tokens.
"""

from typing import TypedDict


class ModelPrice(TypedDict):
    """Price per million tokens."""

    input: float
    output: float
    provider: str


MODEL_PRICING: dict[str, ModelPrice] = {
    # OpenAI Models
    "gpt-5.1-2025-11-13": {"input": 1.25, "output": 10.00, "provider": "OpenAI"},
    "gpt-5.2-2025-12-11": {"input": 1.75, "output": 14.00, "provider": "OpenAI"},
    "gpt-5.6-sol": {"input": 5.00, "output": 30.00, "provider": "OpenAI"},
    "gpt-5.6-terra": {"input": 2.50, "output": 15.00, "provider": "OpenAI"},
    "gpt-5.6-luna": {"input": 1.00, "output": 6.00, "provider": "OpenAI"},
    "gpt-realtime-2025-08-28": {"input": 32.00, "output": 64.00, "provider": "OpenAI"},
    "gpt-realtime-mini-2025-10-06": {"input": 10.00, "output": 20.00, "provider": "OpenAI"},
    "gpt-realtime-mini-2025-12-15": {"input": 10.00, "output": 20.00, "provider": "OpenAI"},
    "gpt-realtime-1.5-2026-02-25": {"input": 32.00, "output": 64.00, "provider": "OpenAI"},
    # Groq Models (via OpenAI-compatible API)
    "openai/gpt-oss-120b": {"input": 0.15, "output": 0.60, "provider": "Groq"},
    "openai/gpt-oss-20b": {"input": 0.075, "output": 0.30, "provider": "Groq"},
    # Google Gemini Models
    "gemini-2.5-flash": {"input": 0.30, "output": 2.50, "provider": "Google"},
    "gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40, "provider": "Google"},
    # gemini-3.1-flash-lite-preview: official Google rate (text/image/video share).
    "gemini-3.1-flash-lite-preview": {"input": 0.25, "output": 1.50, "provider": "Google"},
    "gemini-2.5-flash-image": {"input": 0.30, "output": 2.50, "provider": "Google"},
    "gemini-3.1-flash-lite-image": {"input": 0.25, "output": 1.50, "provider": "Google"},
    "gemini-3.1-flash-image": {"input": 0.50, "output": 3.00, "provider": "Google"},
    "gemini-3-pro-image": {"input": 2.00, "output": 12.00, "provider": "Google"},
    "gemini-3.1-flash-image-preview": {"input": 0.50, "output": 3.00, "provider": "Google"},
    "gemini-3-flash-preview": {"input": 0.50, "output": 3.00, "provider": "Google"},
    "gemini-3-pro-preview": {"input": 2.00, "output": 12.00, "provider": "Google"},
    "gemini-3.1-pro-preview": {"input": 2.00, "output": 12.00, "provider": "Google"},
    "gemini-pro-latest": {"input": 2.00, "output": 12.00, "provider": "Google"},
    "gemini-flash-latest": {"input": 1.50, "output": 9.00, "provider": "Google"},
    "gemini-flash-lite-latest": {"input": 0.25, "output": 1.50, "provider": "Google"},
    "gemini-3.5-flash": {"input": 1.50, "output": 9.00, "provider": "Google"},
    "gemini-3.6-flash": {"input": 1.50, "output": 7.50, "provider": "Google"},
    "gemini-3.5-flash-lite": {"input": 0.30, "output": 2.50, "provider": "Google"},
    # OpenRouter Models
    "google/gemini-2.5-flash-lite": {
        "input": 0.10,
        "output": 0.40,
        "provider": "OpenRouter",
    },
    "google/gemini-3.1-flash-lite-preview": {
        "input": 0.25,
        "output": 1.50,
        "provider": "OpenRouter",
    },
    "google/gemini-3.1-flash-image": {"input": 0.50, "output": 3.00, "provider": "OpenRouter"},
    "google/gemini-2.5-flash-image": {"input": 0.30, "output": 2.50, "provider": "OpenRouter"},
    "google/gemini-3-flash-preview": {
        "input": 0.50,
        "output": 3.00,
        "provider": "OpenRouter",
    },
    "google/gemini-3-pro-preview": {
        "input": 2.00,
        "output": 12.00,
        "provider": "OpenRouter",
    },
    "google/gemini-3.1-pro-preview": {
        "input": 2.00,
        "output": 12.00,
        "provider": "OpenRouter",
    },
    "google/gemini-3.5-flash": {
        "input": 1.50,
        "output": 9.00,
        "provider": "OpenRouter",
    },
    "google/gemini-3.6-flash": {
        "input": 1.50,
        "output": 7.50,
        "provider": "OpenRouter",
    },
    "google/gemini-3.5-flash-lite": {
        "input": 0.30,
        "output": 2.50,
        "provider": "OpenRouter",
    },
    "deepseek/deepseek-chat-v3.1": {
        "input": 0.28,
        "output": 0.42,
        "provider": "OpenRouter",
    },
    "deepseek/deepseek-r1-distill-qwen-7b": {
        "input": 0.55,
        "output": 2.19,
        "provider": "OpenRouter",
    },
    "moonshotai/kimi-k2-thinking": {
        "input": 0.50,
        "output": 1.50,
        "provider": "OpenRouter",
    },
}


def get_model_pricing(model_id: str) -> ModelPrice | None:
    """Get pricing for a model."""
    return MODEL_PRICING.get(model_id)


def calculate_cost(
    model_id: str, input_tokens: int, output_tokens: int
) -> dict[str, float | str | None]:
    """Calculate cost for a model execution."""
    pricing = get_model_pricing(model_id)

    if not pricing:
        return {
            "input_cost": None,
            "output_cost": None,
            "total_cost": None,
            "provider": "Unknown",
        }

    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    total_cost = input_cost + output_cost

    return {
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": total_cost,
        "provider": pricing["provider"],
    }
