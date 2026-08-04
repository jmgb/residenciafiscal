"""Frontera entre preparación offline del corpus e inferencia del chat."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"


def test_la_politica_del_modelo_pertenece_al_chat() -> None:
    from llm_gateway.models import lookup_model

    from chat_model_policy import (
        CHAT_FALLBACK_MODELS,
        CHAT_MODEL,
        CHAT_REASONING_EFFORT,
        CHAT_SUPPORTED_REASONING_EFFORTS,
    )

    assert CHAT_MODEL == "gpt-5.6-luna"
    assert CHAT_REASONING_EFFORT == "high"
    assert CHAT_REASONING_EFFORT in CHAT_SUPPORTED_REASONING_EFFORTS
    assert CHAT_FALLBACK_MODELS == ("gemini-3.6-flash",)
    fallback_info = lookup_model(CHAT_FALLBACK_MODELS[0])
    primary_info = lookup_model(CHAT_MODEL)
    assert fallback_info is not None
    assert primary_info is not None
    assert fallback_info.provider != primary_info.provider


def test_no_existe_una_fachada_llm_para_analizar_sentencias() -> None:
    source = "\n".join(path.read_text(encoding="utf-8") for path in SOURCE_ROOT.rglob("*.py"))

    assert "gpt_request_for_sentencia" not in source
    assert not (SOURCE_ROOT / "ai_service_adapter.py").exists()


def test_la_ruta_a_no_reimplementa_llamadas_de_proveedor() -> None:
    """A solo traduce el contrato al gateway; los SDK viven en la librería."""
    source = (SOURCE_ROOT / "gateway_chat_writer.py").read_text(encoding="utf-8")
    facade = (SOURCE_ROOT / "llm_gateway_facade.py").read_text(encoding="utf-8")

    assert "gpt_request" in source
    assert "LLMRequest" in facade
    assert "gateway.generate" in facade
    assert not any(
        call in source + facade
        for call in (
            "responses.create",
            "chat.completions.create",
            "interactions.create",
            "generate_content",
        )
    )


def test_el_pipeline_v3_no_importa_el_gateway() -> None:
    forbidden = ("llm_gateway", "gateway_setup", "chat_model_policy")
    corpus_modules = sorted(SOURCE_ROOT.glob("jurisprudence_*.py")) + [
        SOURCE_ROOT / "export_jurisprudence_case.py",
        SOURCE_ROOT / "export_jurisprudence_case_derivatives.py",
        SOURCE_ROOT / "export_jurisprudence_sample.py",
    ]

    for path in corpus_modules:
        source = path.read_text(encoding="utf-8")
        assert not any(module in source for module in forbidden), path.name


def test_la_api_no_expone_analisis_llm_de_sentencias() -> None:
    from fastapi.routing import APIRoute

    from api.main import app

    routes = {
        (method, route.path)
        for route in app.routes
        if isinstance(route, APIRoute)
        for method in route.methods or set()
    }

    assert ("POST", "/analizar") not in routes
