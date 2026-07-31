"""Tests de la capa HTTP. No llaman a ningún LLM."""

from __future__ import annotations

import importlib
import io
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from api.main import MAX_UPLOAD_BYTES, app


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


def _pdf(contenido: bytes = b"%PDF-1.4") -> dict[str, tuple[str, io.BytesIO, str]]:
    return {"archivo": ("sentencia.pdf", io.BytesIO(contenido), "application/pdf")}


def test_health_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "modelo_default" in body
    assert "api_keys_presentes" in body


def test_config_expone_enums(client: TestClient) -> None:
    response = client.get("/config")
    assert response.status_code == 200
    body = response.json()
    assert "CRIT_183_DIAS" in body["criterios"]
    assert "PRESENCIA_FISICA_Y_DESPLAZAMIENTOS" in body["categorias_prueba"]
    assert "GANA_AEAT" in body["resultados_finales"]
    assert body["modelos_permitidos"]
    assert body["modelo_default"] == "gpt-5.6-luna"
    assert body["reasoning_effort_default"] == "max"
    assert body["reasoning_efforts_permitidos"] == [
        "none",
        "low",
        "medium",
        "high",
        "xhigh",
        "max",
    ]


def test_analizar_rechaza_no_pdf(client: TestClient) -> None:
    response = client.post(
        "/analizar",
        files={"archivo": ("sentencia.txt", io.BytesIO(b"no soy un pdf"), "text/plain")},
    )
    assert response.status_code == 400
    assert "pdf" in response.json()["detail"].lower()


def test_analizar_rechaza_reasoning_effort_invalido(client: TestClient) -> None:
    response = client.post("/analizar", files=_pdf(), data={"reasoning_effort": "minimal"})
    assert response.status_code == 400
    assert "reasoning_effort" in response.json()["detail"]


def test_analizar_rechaza_max_pages_no_positivo(client: TestClient) -> None:
    response = client.post("/analizar", files=_pdf(), data={"max_pages": "-1"})
    assert response.status_code == 400
    assert "max_pages" in response.json()["detail"]


def test_analizar_rechaza_modelo_desconocido(client: TestClient) -> None:
    # La allowlist evita que el endpoint con coste actúe como proxy abierto para
    # cualquier modelo que proponga el cliente.
    response = client.post("/analizar", files=_pdf(), data={"modelo": "anthropic/claude-x"})
    assert response.status_code == 400
    assert "no soportado" in response.json()["detail"].lower()


def test_upload_grande_se_corta_por_content_length(client: TestClient) -> None:
    # El middleware rechaza por cabecera, sin llegar a parsear el multipart.
    response = client.post(
        "/analizar",
        content=b"x" * 16,
        headers={
            "content-type": "multipart/form-data; boundary=x",
            "content-length": str(MAX_UPLOAD_BYTES + 1),
        },
    )
    assert response.status_code == 413


def test_token_requerido_cuando_esta_configurado(monkeypatch: pytest.MonkeyPatch) -> None:
    """Con RESIDENCIAFISCAL_API_TOKEN definido, /analizar exige X-API-Token."""
    monkeypatch.setenv("RESIDENCIAFISCAL_API_TOKEN", "secreto-de-prueba")
    import api.main as api_main

    recargado = importlib.reload(api_main)
    try:
        with TestClient(recargado.app) as c:
            assert c.post("/analizar", files=_pdf()).status_code == 401

            # Token correcto: pasa la auth y falla más adelante, en la validación
            # del modelo, lo que demuestra que la dependencia dejó pasar.
            respuesta = c.post(
                "/analizar",
                files=_pdf(),
                data={"modelo": "modelo-inexistente"},
                headers={"X-API-Token": "secreto-de-prueba"},
            )
            assert respuesta.status_code == 400

            # /health sigue abierto (no gasta dinero).
            assert c.get("/health").status_code == 200
    finally:
        monkeypatch.delenv("RESIDENCIAFISCAL_API_TOKEN", raising=False)
        importlib.reload(api_main)
