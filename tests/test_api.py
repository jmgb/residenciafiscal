"""Tests de la capa HTTP. No llaman a ningún LLM."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from api.main import app


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
