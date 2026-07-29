from __future__ import annotations

from config import detect_provider


def test_modelos_se_enrutan_al_proveedor_que_expresa_su_id() -> None:
    assert detect_provider("gpt-5.6-luna") == "openai"
    assert detect_provider("gemini-3.6-flash") == "gemini"
    assert detect_provider("models/gemini-3.6-flash") == "gemini"
    assert detect_provider("groq-llama-3.3") == "groq"
    assert detect_provider("meta-llama/llama-4-scout-17b-16e-instruct") == "groq"
    assert detect_provider("openai/gpt-oss-120b") == "groq"
    assert detect_provider("google/gemini-3.6-flash") == "openrouter"
    assert detect_provider("anthropic/claude-sonnet") == "openrouter"
