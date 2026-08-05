"""Regresión ejecutable del contrato de migración del chat a Alfredo."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient


def test_firma_hmac_cubre_timestamp_request_id_y_body_y_rechaza_replay() -> None:
    from api.chat_security import ReplayCache, sign_chat_request, verify_chat_request

    secret = "test-secret"
    timestamp = int(datetime.now(UTC).timestamp())
    request_id = "chat-00000000-0000-4000-8000-000000000001"
    body = b'{"messages":[]}'
    signature = sign_chat_request(secret, timestamp, request_id, body)
    cache = ReplayCache()

    verify_chat_request(
        secret,
        timestamp=timestamp,
        request_id=request_id,
        signature=signature,
        body=body,
        replay_cache=cache,
    )

    with pytest.raises(ValueError, match="reutilizada"):
        verify_chat_request(
            secret,
            timestamp=timestamp,
            request_id=request_id,
            signature=signature,
            body=body,
            replay_cache=cache,
        )

    with pytest.raises(ValueError, match="firma"):
        verify_chat_request(
            secret,
            timestamp=timestamp,
            request_id="chat-00000000-0000-4000-8000-000000000002",
            signature=signature,
            body=body,
            replay_cache=ReplayCache(),
        )


def test_chat_request_mantiene_ids_jurisdiccion_y_limites_de_la_v1() -> None:
    from api.chat import MAX_MESSAGE_CHARS, ChatRequest

    request = ChatRequest.model_validate(
        {
            "conversation_id": "conversation-1",
            "country_path": "/espana",
            "messages": [
                {
                    "id": "message-1",
                    "role": "user",
                    "content": " pregunta ",
                }
            ],
        }
    )

    assert request.conversation_id == "conversation-1"
    assert request.country_path == "/espana"
    assert request.messages[0].id == "message-1"
    assert MAX_MESSAGE_CHARS == 500
    with pytest.raises(ValueError):
        ChatRequest.model_validate({"messages": [{"role": "user", "content": "x" * 501}]})


def test_los_identificadores_mal_formados_se_sustituyen_como_en_la_v1() -> None:
    """La V1 genera identificadores en vez de rechazar; endurecerlo divergiría."""
    from api.chat import ChatRequest

    request = ChatRequest.model_validate(
        {
            "conversation_id": "conversación con espacios",
            "country_path": "/Espana Con Mayúsculas",
            "messages": [{"id": "id inválido", "role": "user", "content": "pregunta"}],
        }
    )

    assert request.conversation_id is None
    assert request.country_path == "/espana"
    assert request.messages[0].id is None


def test_un_cuerpo_invalido_devuelve_400_y_no_el_422_de_pydantic() -> None:
    from api.chat import parse_chat_request

    with pytest.raises(HTTPException) as error:
        parse_chat_request(b'{"messages":[]}')

    assert error.value.status_code == 400


def test_coste_no_disponible_no_se_convierte_en_cero() -> None:
    from chat_strategy_costs import unavailable_cost

    cost = unavailable_cost()

    assert cost.measurement == "UNAVAILABLE"
    assert cost.amount_usd is None
    assert cost.cost_microusd is None
    assert cost.input_tokens is None
    assert cost.output_tokens is None
    assert cost.retrieved_document_tokens is None


@dataclass
class _Answer:
    strategy: str
    status: str = "completa"
    text: str = "ok"
    sources: tuple[Any, ...] = ()
    limits: tuple[str, ...] = ()
    cost: Any = None
    model: str = "fake"
    latency_ms: int = 1


class _DelayedStrategy:
    def __init__(self, strategy: str, delay: float) -> None:
        self.strategy = strategy
        self.delay = delay
        self.started_at: float | None = None

    async def answer(self, question: str, *, request_id: str) -> Any:
        self.started_at = asyncio.get_running_loop().time()
        await asyncio.sleep(self.delay)
        return _Answer(self.strategy)


@pytest.mark.asyncio
async def test_las_estrategias_empiezan_en_paralelo() -> None:
    from chat_strategy_comparison import compare_strategies
    from chat_strategy_costs import zero_marginal_cost
    from chat_strategy_models import StrategyAnswer

    structured = _DelayedStrategy("current_structured", 0.03)
    file_search = _DelayedStrategy("gemini_file_search", 0.03)
    structured_answer = StrategyAnswer(
        strategy="current_structured",
        status="completa",
        text="ok",
        sources=(),
        limits=(),
        cost=zero_marginal_cost(),
        model="fake",
        latency_ms=1,
    )
    file_search_answer = StrategyAnswer(
        strategy="gemini_file_search",
        status="completa",
        text="ok",
        sources=(),
        limits=(),
        cost=zero_marginal_cost(),
        model="fake",
        latency_ms=1,
    )

    async def answer_structured(question: str, *, request_id: str) -> Any:
        structured.started_at = asyncio.get_running_loop().time()
        await asyncio.sleep(structured.delay)
        return structured_answer

    async def answer_file_search(question: str, *, request_id: str) -> Any:
        file_search.started_at = asyncio.get_running_loop().time()
        await asyncio.sleep(file_search.delay)
        return file_search_answer

    structured.answer = answer_structured  # type: ignore[method-assign]
    file_search.answer = answer_file_search  # type: ignore[method-assign]
    report = await compare_strategies(
        question="pregunta",
        structured=structured,
        file_search=file_search,
        output_path=Path("/tmp/chat-migration-report.json"),
        log_path=Path("/tmp/chat-migration-log.jsonl"),
        request_id="chat-test",
    )

    assert report.answers[0].strategy == "current_structured"
    assert report.answers[1].strategy == "gemini_file_search"
    assert structured.started_at is not None
    assert file_search.started_at is not None
    assert abs(structured.started_at - file_search.started_at) < 0.02


def test_repositorio_de_chat_usa_solo_rpc_de_ciclo_de_vida() -> None:
    from api.chat_persistence import ChatExperimentContext, SupabaseChatRepository

    class RpcClient:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, Any]]] = []

        async def rpc(self, function_name: str, parameters: dict[str, Any]) -> Any:
            self.calls.append((function_name, parameters))
            if function_name == "create_chat_request":
                return {"request_id": "chat-effective"}
            return True

    client = RpcClient()
    repository = SupabaseChatRepository(
        client,
        ChatExperimentContext(
            experiment_version="chat-alfredo/1",
            deployed_commit="abc123",
            comparison_schema_version="residenciafiscal-chat-comparison/1",
            structured_corpus_version="residenciafiscal-case/3",
            structured_prompt_version="structured-claims-v4",
            file_search_store="fileSearchStores/synthetic",
            file_search_prompt_version="file-search-authority-v8",
        ),
    )

    async def exercise() -> None:
        await repository.record(
            request_id="chat-request",
            conversation_id="conversation-1",
            user_message_id="message-1",
            country_path="/espana",
            question="pregunta",
        )
        await repository.fail(
            request_id="chat-effective", status="failed", failure_code="comparison_error"
        )

    asyncio.run(exercise())
    assert [name for name, _ in client.calls] == ["create_chat_request", "fail_chat_request"]
    assert "p_question" in client.calls[0][1]
    assert "p_experiment" in client.calls[0][1]
    assert "p_failure_code" in client.calls[1][1]


def test_health_live_y_ready_no_inicializan_proveedores(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHAT_COMPARISON_ENABLED", "false")
    from api.main import app

    with TestClient(app) as client:
        assert client.get("/health/live").json() == {"status": "ok"}
        assert client.get("/health/ready").status_code == 200
        assert client.get("/health/ready").json()["chat_enabled"] is False


def test_readiness_activa_falla_cerrado_si_faltan_artefactos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CHAT_COMPARISON_ENABLED", "true")
    monkeypatch.setenv("CHAT_RETRIEVAL_CORPUS", "/tmp/no-corpus-for-chat-test.json")
    monkeypatch.setenv("CHAT_FILE_SEARCH_STORE_STATE", "/tmp/no-store-for-chat-test.json")
    from api.main import app

    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"


def test_deadline_global_cierra_la_reserva_sin_exponer_detalle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from api.chat import get_chat_comparison_runner, get_chat_repository
    from api.main import app

    class SlowRunner:
        async def compare(self, question: str, *, request_id: str) -> Any:
            await asyncio.sleep(0.05)
            raise AssertionError("el deadline debía cancelar la comparación")

    class Repository:
        events: list[tuple[str, str]] = []

        async def record(self, **kwargs: Any) -> str:
            return "chat-effective"

        async def complete(self, **kwargs: Any) -> None:
            raise AssertionError("no debía completar una petición agotada")

        async def fail(self, *, request_id: str, status: str, failure_code: str) -> None:
            self.events.append((status, failure_code))

    repository = Repository()
    monkeypatch.setenv("CHAT_COMPARISON_ENABLED", "true")
    monkeypatch.setenv("CHAT_PROXY_SECRET", "test-secret")
    monkeypatch.setenv("CHAT_BACKEND_DEADLINE_SECONDS", "0.001")
    app.dependency_overrides[get_chat_comparison_runner] = lambda: SlowRunner()
    app.dependency_overrides[get_chat_repository] = lambda: repository
    try:
        with TestClient(app) as client:
            response = client.post(
                "/chat",
                headers={"x-chat-proxy-secret": "test-secret"},
                json={"messages": [{"role": "user", "content": "pregunta"}]},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert '"code":"comparison_timeout"' in response.text
    assert repository.events == [("timed_out", "comparison_timeout")]


def test_artefacto_de_chat_excluye_pdf_y_verifica_hashes(tmp_path: Path) -> None:
    from chat_runtime_artifact import build_chat_runtime_artifact, verify_artifact

    project = tmp_path / "project"
    (project / "src").mkdir(parents=True)
    (project / "src/api").mkdir()
    (project / "src/api/main.py").write_text("app = None\n", encoding="utf-8")
    (project / "knowledge/jurisprudencia-v3/retrieval").mkdir(parents=True)
    (project / "knowledge/jurisprudencia-v3/retrieval/rollout-106.corpus.json").write_text(
        "{}", encoding="utf-8"
    )
    (project / "knowledge/jurisprudencia-v3/verbatim").mkdir()
    (project / "knowledge/jurisprudencia-v3/verbatim/a.pages.json").write_text(
        "{}", encoding="utf-8"
    )
    (project / "sentencias").mkdir()
    (project / "sentencias/private.pdf").write_bytes(b"not allowed")

    artifact = tmp_path / "chat-runtime.tar.gz"
    build_chat_runtime_artifact(project, artifact)
    manifest = verify_artifact(artifact)

    assert manifest["schema_version"] == "residenciafiscal-chat-runtime-artifact/1"
    assert all(not path.endswith(".pdf") for path in manifest["files"])
    assert "sentencias/private.pdf" not in manifest["files"]


def test_rate_limit_autoritativo_vive_en_fastapi_y_expira_por_ventana() -> None:
    from api.chat_rate_limit import SlidingWindowRateLimiter

    limiter = SlidingWindowRateLimiter(limit=2, window_seconds=60)
    assert limiter.allow("client-a", now=100.0) is True
    assert limiter.allow("client-a", now=101.0) is True
    assert limiter.allow("client-a", now=102.0) is False
    assert limiter.allow("client-b", now=102.0) is True
    assert limiter.allow("client-a", now=161.0) is True


@pytest.mark.asyncio
async def test_el_stream_late_mientras_el_comparador_trabaja() -> None:
    """Sin latido, un intermediario cierra una conexión inactiva de 90 s.

    El comparador no emite tokens: entre la primera cabecera y el primer evento
    puede no salir un solo byte durante todo el presupuesto.
    """
    import api.chat as chat_module

    async def slow() -> Any:
        await asyncio.sleep(0.25)
        return "listo"

    comparison = asyncio.ensure_future(slow())
    monkey = chat_module.HEARTBEAT_SECONDS
    chat_module.HEARTBEAT_SECONDS = 0.05
    try:
        beats = [beat async for beat in chat_module._heartbeats(comparison, 5.0)]
    finally:
        chat_module.HEARTBEAT_SECONDS = monkey

    assert beats
    assert all(beat == b": keep-alive\n\n" for beat in beats)
    assert comparison.result() == "listo"


@pytest.mark.asyncio
async def test_el_latido_no_sobrevive_al_presupuesto_global() -> None:
    import api.chat as chat_module

    async def never() -> Any:
        await asyncio.sleep(30)

    comparison = asyncio.ensure_future(never())
    monkey = chat_module.HEARTBEAT_SECONDS
    chat_module.HEARTBEAT_SECONDS = 0.02
    try:
        with pytest.raises(TimeoutError):
            async for _ in chat_module._heartbeats(comparison, 0.1):
                pass
    finally:
        chat_module.HEARTBEAT_SECONDS = monkey

    # La cancelación se propaga al proveedor: agotar el presupuesto no puede
    # dejar una llamada de pago corriendo sin nadie esperándola.
    with pytest.raises(asyncio.CancelledError):
        await comparison
    assert comparison.cancelled()


def test_la_pregunta_de_gimnasio_recupera_su_sentencia_declarada() -> None:
    """Regresión obligatoria del plan, comprobada contra el corpus real.

    El corpus no dice «gimnasio»: dice «cuotas de clubs deportivos, de golf,
    polo, futbol o gimnasios». Sin la equivalencia léxica, la recuperación de A
    no llega a `san-2347-2022` y la respuesta se construye sobre otra sentencia
    sin que nada falle.
    """
    from jurisprudence_phase_d_retrieval import retrieve_for_chat
    from jurisprudence_retrieval_corpus import load_retrieval_corpus

    corpus_path = Path("knowledge/jurisprudencia-v3/retrieval/rollout-106.corpus.json")
    if not corpus_path.is_file():  # pragma: no cover - el rollout no está en todos los checkouts
        pytest.skip("el corpus del rollout no está disponible")
    corpus = load_retrieval_corpus(corpus_path.read_bytes())

    gimnasio = retrieve_for_chat(
        corpus, "¿Sirve la cuota de un gimnasio como prueba de presencia en España?", limit=5
    )
    assert "san-2347-2022" in [hit.judgment_id for hit in gimnasio.hits]

    # Recuperar la sentencia no basta: el anclaje literal de la página 7 tiene
    # que llegar al redactor, o la respuesta se abstiene por falta de extracto.
    from structured_evidence_context import build_structured_evidence_bundle

    bundle = build_structured_evidence_bundle(
        gimnasio,
        {unit.unit_id: unit for unit in corpus.units},
        "¿Sirve la cuota de un gimnasio como prueba de presencia en España?",
    )
    anclajes = [
        source
        for source in bundle.sources_by_evidence_id.values()
        if source.judgment_id == "san-2347-2022" and source.page == 7
    ]
    assert any("clubs deportivos" in source.quote for source in anclajes)

    # Y con las páginas verbatim la cita llega con su contexto: el anclaje corta
    # en «clubs deportivos» y se pierde justo la palabra por la que se pregunta.
    verbatim = {
        source.judgment_id: Path(
            f"knowledge/jurisprudencia-v3/verbatim/{source.judgment_id}.pages.json"
        )
        for source in corpus.sources
    }
    if all(path.is_file() for path in verbatim.values()):
        ampliado = build_structured_evidence_bundle(
            gimnasio,
            {unit.unit_id: unit for unit in corpus.units},
            "¿Sirve la cuota de un gimnasio como prueba de presencia en España?",
            verbatim,
        )
        citas = [
            source.quote
            for source in ampliado.sources_by_evidence_id.values()
            if source.judgment_id == "san-2347-2022" and source.page == 7
        ]
        assert any("gimnasios" in quote for quote in citas)


def test_una_release_manipulada_tumba_la_readiness(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """El monitor externo debe enterarse sin esperar a que llegue tráfico."""
    import api.chat_runtime as runtime_module
    from chat_runtime_artifact import build_chat_runtime_artifact

    release = tmp_path / "release"
    (release / "src").mkdir(parents=True)
    (release / "src" / "modulo.py").write_text("valor = 1\n", encoding="utf-8")
    (release / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    declarado = build_chat_runtime_artifact(release, tmp_path / "artefacto.tar.gz", version="test")
    manifest = release / "chat-runtime-manifest.json"
    manifest.write_text(json.dumps(declarado), encoding="utf-8")

    monkeypatch.setattr(runtime_module, "PROJECT_ROOT", release)
    monkeypatch.setenv("CHAT_RUNTIME_MANIFEST", str(manifest))
    monkeypatch.setenv("CHAT_RUNTIME_HASH_REQUIRED", "true")
    runtime_module._verified_release.cache_clear()

    assert runtime_module.runtime_release() == "test"

    (release / "src" / "modulo.py").write_text("valor = 2\n", encoding="utf-8")
    runtime_module._verified_release.cache_clear()

    with pytest.raises(HTTPException) as error:
        runtime_module.runtime_release()
    assert error.value.status_code == 503
    runtime_module._verified_release.cache_clear()


def test_el_limitador_no_acumula_claves_muertas() -> None:
    from api.chat_rate_limit import SlidingWindowRateLimiter

    limiter = SlidingWindowRateLimiter(limit=2, window_seconds=60, sweep_threshold=100)
    for index in range(500):
        limiter.allow(f"client-{index}", now=100.0)
    assert limiter.tracked_keys == 500

    # Los clientes que no vuelven se barren en la siguiente petición: sin eso el
    # diccionario crece con cada cliente visto y no baja nunca.
    limiter.allow("client-nuevo", now=10_000.0)

    assert limiter.tracked_keys == 1


def test_la_cuota_ignora_una_cabecera_que_el_cliente_puede_falsificar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import api.chat as chat_module
    from api.chat_rate_limit import SlidingWindowRateLimiter

    monkeypatch.setenv("CHAT_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setattr(
        chat_module, "chat_rate_limiter", SlidingWindowRateLimiter(limit=1, window_seconds=60)
    )

    chat_module.enforce_chat_rate_limit(x_chat_client_key=None)
    with pytest.raises(HTTPException) as error:
        chat_module.enforce_chat_rate_limit(x_chat_client_key=None)

    assert error.value.status_code == 429
    assert "x_forwarded_for" not in chat_module.enforce_chat_rate_limit.__code__.co_varnames


def test_varios_workers_no_pueden_arrancar_con_estado_en_memoria(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from api.chat_rate_limit import require_single_process_state

    monkeypatch.setenv("WEB_CONCURRENCY", "4")

    with pytest.raises(RuntimeError, match="workers"):
        require_single_process_state()


def test_el_coste_medido_del_primer_intento_sobrevive_a_un_retry_sin_medicion() -> None:
    from chat_strategy_costs import unavailable_cost, zero_marginal_cost
    from gemini_file_search_answer import _sum_costs

    measured = zero_marginal_cost().model_copy(
        update={"amount_usd": Decimal("0.000060"), "cost_microusd": 60, "input_tokens": 120}
    )

    total = _sum_costs(measured, unavailable_cost())

    assert total.cost_microusd == 60
    assert total.amount_usd == Decimal("0.000060")
    assert total.measurement == "ESTIMATED"
    assert _sum_costs(unavailable_cost(), unavailable_cost()).measurement == "UNAVAILABLE"


def test_request_id_legado_tambien_debe_ser_un_uuid_de_chat() -> None:
    from api.chat import _request_id

    with pytest.raises(HTTPException, match="Identificador"):
        _request_id("../../private-output")
