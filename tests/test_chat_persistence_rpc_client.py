"""Contrato del cliente RPC de Supabase: la única salida HTTP de `chat_persistence`."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Callable, Coroutine
from typing import Any

import httpx2
import pytest

from api.chat_persistence import (
    HttpSupabaseRpcClient,
    SupabaseChatRepository,
    SupabaseRpcError,
    get_production_chat_repository,
)

Handler = (
    Callable[[httpx2.Request], httpx2.Response]
    | Callable[[httpx2.Request], Coroutine[None, None, httpx2.Response]]
)


def rpc_client(handler: Handler, *, timeout_seconds: float = 10.0) -> HttpSupabaseRpcClient:
    return HttpSupabaseRpcClient(
        "https://proyecto.supabase.co/",
        "clave-del-runtime",
        timeout_seconds=timeout_seconds,
        transport=httpx2.MockTransport(handler),
    )


async def test_envia_post_a_la_rpc_con_credencial_y_cuerpo_json() -> None:
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(200, json={"request_id": "chat-1"})

    parameters = {"p_question": "¿Cañón?", "p_ids": [1, None]}
    result = await rpc_client(handler).rpc("create_chat_request", parameters)

    assert result == {"request_id": "chat-1"}
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST"
    assert str(request.url) == "https://proyecto.supabase.co/rest/v1/rpc/create_chat_request"
    assert request.headers["apikey"] == "clave-del-runtime"
    assert request.headers["authorization"] == "Bearer clave-del-runtime"
    assert request.headers["content-type"] == "application/json"
    assert json.loads(request.content) == parameters


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (httpx2.Response(200, json=True), True),
        (httpx2.Response(200, content=b"null", headers={"content-type": "application/json"}), None),
        (
            httpx2.Response(
                200,
                content=b'{"a": 1}',
                headers={"content-type": "application/vnd.pgrst.object+json; charset=utf-8"},
            ),
            {"a": 1},
        ),
        (httpx2.Response(204), None),
        (httpx2.Response(200, content=b" \n", headers={"content-type": "application/json"}), None),
    ],
    ids=["json", "null", "subtipo-json", "sin-contenido", "cuerpo-vacio"],
)
async def test_interpreta_las_respuestas_correctas(
    response: httpx2.Response, expected: object
) -> None:
    assert await rpc_client(lambda _: response).rpc("complete_chat_request", {}) == expected


@pytest.mark.parametrize("status", [400, 401, 404, 500, 503])
async def test_un_error_http_no_conserva_el_cuerpo_ni_la_credencial(status: int) -> None:
    def handler(_: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(status, json={"message": "dato sensible"})

    with pytest.raises(SupabaseRpcError) as captured:
        await rpc_client(handler).rpc("fail_chat_request", {})

    assert captured.value.operation == "fail_chat_request"
    assert captured.value.status == status
    assert str(captured.value) == f"RPC fail_chat_request devolvió HTTP {status}"
    assert "dato sensible" not in repr(captured.value)
    assert "clave-del-runtime" not in repr(captured.value)


@pytest.mark.parametrize(
    "headers",
    [{"content-type": "text/html"}, {}],
    ids=["html", "sin-tipo"],
)
async def test_rechaza_un_exito_que_no_es_json(headers: dict[str, str]) -> None:
    def handler(_: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, content=b"<html>", headers=headers)

    with pytest.raises(SupabaseRpcError) as captured:
        await rpc_client(handler).rpc("create_chat_request", {})

    assert captured.value.status == 502


async def test_propaga_un_json_invalido() -> None:
    def handler(_: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200, content=b"{no json", headers={"content-type": "application/json"}
        )

    with pytest.raises(json.JSONDecodeError):
        await rpc_client(handler).rpc("create_chat_request", {})


async def test_propaga_el_fallo_de_conexion() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("sin conexión", request=request)

    with pytest.raises(httpx2.ConnectError):
        await rpc_client(handler).rpc("create_chat_request", {})


async def test_agota_el_plazo_con_el_timeout_error_que_traduce_el_chat() -> None:
    async def handler(_: httpx2.Request) -> httpx2.Response:
        await asyncio.sleep(5)
        return httpx2.Response(200, json=True)

    with pytest.raises(TimeoutError):
        await rpc_client(handler, timeout_seconds=0.01).rpc("create_chat_request", {})


async def test_el_plazo_es_total_y_cubre_un_cuerpo_lento() -> None:
    async def slow_body() -> AsyncIterator[bytes]:
        for chunk in (b"[", b"1", b"]"):
            await asyncio.sleep(0.03)
            yield chunk

    def handler(_: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200, content=slow_body(), headers={"content-type": "application/json"}
        )

    with pytest.raises(TimeoutError):
        await rpc_client(handler, timeout_seconds=0.05).rpc("create_chat_request", {})


async def test_sigue_una_redireccion_conservando_metodo_y_cuerpo() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path.endswith("/antigua"):
            return httpx2.Response(307, headers={"location": "/rest/v1/rpc/nueva"})
        assert request.method == "POST"
        assert json.loads(request.content) == {"p_id": 1}
        return httpx2.Response(200, json=True)

    assert await rpc_client(handler).rpc("antigua", {"p_id": 1}) is True


async def test_no_hereda_proxies_del_entorno(monkeypatch: pytest.MonkeyPatch) -> None:
    real_client = httpx2.AsyncClient
    options: dict[str, object] = {}

    def spy(**kwargs: Any) -> httpx2.AsyncClient:
        options.update(kwargs)
        return real_client(**kwargs)

    monkeypatch.setattr(httpx2, "AsyncClient", spy)

    await rpc_client(lambda _: httpx2.Response(200, json=True)).rpc("complete_chat_request", {})

    assert options["trust_env"] is False


@pytest.mark.parametrize(("url", "key"), [("", "clave"), ("https://x.supabase.co", "")])
def test_exige_url_y_clave(url: str, key: str) -> None:
    with pytest.raises(ValueError, match="faltan credenciales"):
        HttpSupabaseRpcClient(url, key)


def test_el_repositorio_de_produccion_usa_este_cliente(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://proyecto.supabase.co")
    monkeypatch.setenv("SUPABASE_CHAT_RUNTIME_KEY", "clave-del-runtime")

    repository = get_production_chat_repository()

    assert isinstance(repository, SupabaseChatRepository)
    assert isinstance(repository._client, HttpSupabaseRpcClient)
