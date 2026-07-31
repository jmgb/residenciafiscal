"""Tests de la capa HTTP. No llaman a ningún LLM."""

from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from api.chat import ChatComparisonRunner, get_chat_comparison_runner
from api.chat_runtime import get_production_chat_runner
from api.main import app
from chat_strategy_models import ComparisonReport, MarginalCost, StrategyAnswer, StrategySource


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


def test_health_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["corpus_pipeline"] == "python_agent_offline"
    assert body["paid_sentence_analysis"] is False


def test_config_expone_enums(client: TestClient) -> None:
    response = client.get("/config")
    assert response.status_code == 200
    body = response.json()
    assert "CRIT_183_DIAS" in body["criterios"]
    assert "PRESENCIA_FISICA_Y_DESPLAZAMIENTOS" in body["categorias_prueba"]
    assert "GANA_AEAT" in body["resultados_finales"]
    assert body["chat_model"] == "gpt-5.6-luna"
    assert body["chat_reasoning_effort"] == "max"
    assert body["chat_reasoning_efforts_permitidos"] == [
        "none",
        "low",
        "medium",
        "high",
        "xhigh",
        "max",
    ]


def test_analizar_no_existe(client: TestClient) -> None:
    response = client.post("/analizar")

    assert response.status_code == 404


class FakeComparisonRunner(ChatComparisonRunner):
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def compare(self, question: str, *, request_id: str) -> ComparisonReport:
        self.calls.append((question, request_id))
        cost = MarginalCost(
            amount_usd=Decimal("0.012345"),
            cost_microusd=12345,
            measurement="ACTUAL",
            pricing_version="2026-07-31",
            input_tokens=100,
            output_tokens=20,
            retrieved_document_tokens=0,
        )
        source = StrategySource(
            strategy="current_structured",
            judgment_id="sts-107-2018",
            page=7,
            source_sha256="a" * 64,
            quote="Texto literal.",
            verification="EXACT",
        )
        return ComparisonReport(
            request_id=request_id,
            answers=(
                StrategyAnswer(
                    strategy="current_structured",
                    status="completa",
                    text="Respuesta A.",
                    sources=(source,),
                    limits=(),
                    cost=cost,
                    model="luna",
                    latency_ms=100,
                ),
                StrategyAnswer(
                    strategy="gemini_file_search",
                    status="parcial",
                    text="Respuesta B.",
                    sources=(),
                    limits=("Cobertura limitada.",),
                    cost=cost,
                    model="gemini-2.5-flash",
                    latency_ms=200,
                ),
            ),
        )


def test_chat_expone_comparacion_sse_sin_mezclar_estrategias(client: TestClient) -> None:
    runner = FakeComparisonRunner()
    app.dependency_overrides[get_chat_comparison_runner] = lambda: runner
    try:
        response = client.post(
            "/chat",
            json={
                "messages": [
                    {"role": "user", "content": "primera pregunta"},
                    {"role": "assistant", "content": "respuesta anterior"},
                    {"role": "user", "content": "¿Qué cuenta para los 183 días?"},
                ]
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["x-chat-protocol"] == "2"
    assert response.headers["cache-control"] == "no-store"
    assert [question for question, _request_id in runner.calls] == [
        "¿Qué cuenta para los 183 días?"
    ]
    assert runner.calls[0][1].startswith("chat-")
    assert response.text.count("event: answer_start") == 2
    assert response.text.count("event: answer_done") == 2
    assert '"strategy":"current_structured"' in response.text
    assert '"strategy":"gemini_file_search"' in response.text
    assert '"amount_usd":"0.012345"' in response.text
    assert "event: done\ndata: {}\n\n" in response.text


def test_chat_rechaza_una_conversacion_sin_pregunta_de_usuario(client: TestClient) -> None:
    runner = FakeComparisonRunner()
    app.dependency_overrides[get_chat_comparison_runner] = lambda: runner
    try:
        response = client.post(
            "/chat",
            json={"messages": [{"role": "assistant", "content": "solo asistente"}]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert runner.calls == []


def test_chat_de_produccion_permanece_cerrado_por_defecto(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CHAT_COMPARISON_ENABLED", raising=False)
    get_production_chat_runner.cache_clear()
    try:
        response = client.post(
            "/chat",
            json={"messages": [{"role": "user", "content": "pregunta"}]},
        )
    finally:
        get_production_chat_runner.cache_clear()

    assert response.status_code == 503
    assert response.json() == {"detail": "Chat comparativo no habilitado"}


def test_chat_habilitado_exige_el_secreto_del_proxy(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = FakeComparisonRunner()
    monkeypatch.setenv("CHAT_COMPARISON_ENABLED", "true")
    monkeypatch.setenv("CHAT_PROXY_SECRET", "secreto-esperado")
    app.dependency_overrides[get_chat_comparison_runner] = lambda: runner
    try:
        missing = client.post(
            "/chat",
            json={"messages": [{"role": "user", "content": "pregunta"}]},
        )
        valid = client.post(
            "/chat",
            headers={"x-chat-proxy-secret": "secreto-esperado"},
            json={"messages": [{"role": "user", "content": "pregunta"}]},
        )
    finally:
        app.dependency_overrides.clear()

    assert missing.status_code == 403
    assert valid.status_code == 200
    assert len(runner.calls) == 1


def test_chat_convierte_un_fallo_del_runner_en_error_sse_aislado(client: TestClient) -> None:
    class FailingRunner(ChatComparisonRunner):
        async def compare(self, question: str, *, request_id: str) -> ComparisonReport:
            raise RuntimeError("detalle interno que no debe salir")

    app.dependency_overrides[get_chat_comparison_runner] = lambda: FailingRunner()
    try:
        response = client.post(
            "/chat",
            json={"messages": [{"role": "user", "content": "pregunta privada"}]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "event: error" in response.text
    assert '"code":"comparison_failed"' in response.text
    assert "detalle interno" not in response.text
    assert "pregunta privada" not in response.text


def test_chat_no_expone_el_detalle_interno_de_una_estrategia_fallida(
    client: TestClient,
) -> None:
    class StrategyFailureRunner(ChatComparisonRunner):
        async def compare(self, question: str, *, request_id: str) -> ComparisonReport:
            cost = MarginalCost(
                amount_usd=Decimal("0.000000"),
                cost_microusd=0,
                measurement="ESTIMATED",
                pricing_version="2026-07-31",
                input_tokens=0,
                output_tokens=0,
                retrieved_document_tokens=0,
            )
            failed = StrategyAnswer(
                strategy="current_structured",
                status="error",
                text="",
                sources=(),
                limits=("ProviderError: Authorization: Bearer secreto-interno",),
                cost=cost,
                model="unavailable",
                latency_ms=0,
            )
            return ComparisonReport(
                request_id=request_id,
                answers=(
                    failed,
                    failed.model_copy(update={"strategy": "gemini_file_search"}),
                ),
            )

    app.dependency_overrides[get_chat_comparison_runner] = lambda: StrategyFailureRunner()
    try:
        response = client.post(
            "/chat",
            json={"messages": [{"role": "user", "content": "pregunta"}]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "secreto-interno" not in response.text
    assert "ProviderError" not in response.text
    assert "No se ha podido completar esta estrategia." in response.text
