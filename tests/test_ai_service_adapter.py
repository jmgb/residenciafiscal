"""La fachada del analizador: mismo contrato, otra implementación detrás.

`process_pdf_async` no se tocó en la migración, así que lo que estos tests
protegen es exactamente lo que esa función espera encontrar en el diccionario
de vuelta. Si algo de aquí se rompe, se rompe el JSONL de las 106 sentencias.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import ai_service_adapter  # noqa: E402
from ai_service_adapter import gpt_request_for_sentencia  # noqa: E402

ANALISIS_JSON = '{"resultado_final": "GANA_AEAT", "confianza_extraccion": "ALTA"}'


class FakeProviderAdapter:
    """Doble del adaptador de proveedor, dentro del gateway real."""

    def __init__(
        self,
        *,
        name: str = "openai",
        text: str = ANALISIS_JSON,
        usage: Any = None,
        error: Exception | None = None,
    ) -> None:
        self.name = name
        self._text = text
        self._usage = usage
        self._error = error
        self.requests: list[Any] = []

    async def generate(self, request: Any, *, model: str) -> Any:
        from llm_gateway import ProviderResponse, TokenUsage

        self.requests.append(request)
        if self._error is not None:
            raise self._error
        return ProviderResponse(
            output_text=self._text,
            usage=self._usage if self._usage is not None else TokenUsage(1000, 200),
            finish_reason="completed",
        )


@pytest.fixture
def credenciales(monkeypatch: pytest.MonkeyPatch) -> None:
    for variable in ("OPENAI_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.setenv(variable, "clave-de-prueba")


def _instalar_gateway(
    monkeypatch: pytest.MonkeyPatch, adapter: FakeProviderAdapter, *, prefixes: tuple[str, ...]
) -> None:
    from llm_gateway import LLMGateway, ProviderRegistry

    registry = ProviderRegistry()
    registry.register(adapter, model_prefixes=prefixes)
    gateway = LLMGateway(registry=registry)
    monkeypatch.setattr(ai_service_adapter, "get_gateway", lambda: gateway)


async def _analizar(model: str = "gpt-5.6-luna", **kwargs: Any) -> dict[str, Any]:
    import logging

    defaults: dict[str, Any] = {
        "ai_model": model,
        "system_prompt": "Analiza la sentencia y devuelve json.",
        "pdf_text": "--- PÁGINA 1 ---\nAUDIENCIA NACIONAL",
        "logger": logging.getLogger("test"),
    }
    defaults.update(kwargs)
    return await gpt_request_for_sentencia(**defaults)


class TestContratoDelPipeline:
    async def test_devuelve_el_analisis_aplanado_con_su_metadata(
        self, monkeypatch: pytest.MonkeyPatch, credenciales: None
    ) -> None:
        _instalar_gateway(monkeypatch, FakeProviderAdapter(), prefixes=("gpt-",))

        result = await _analizar()

        assert result["resultado_final"] == "GANA_AEAT"
        assert result["confianza_extraccion"] == "ALTA"
        assert result["tiempo_ejecucion"].startswith("gpt-5.6-luna - ")
        assert "error" not in result

    async def test_el_coste_sale_del_catalogo_del_paquete(
        self, monkeypatch: pytest.MonkeyPatch, credenciales: None
    ) -> None:
        """1000 entrada y 200 salida a las tarifas de Luna: 0,20 y 1,20 USD/Mtok."""
        _instalar_gateway(monkeypatch, FakeProviderAdapter(), prefixes=("gpt-",))

        result = await _analizar()

        assert result["cost_usd"] == pytest.approx(0.0002 + 0.00024)
        assert result["cost_measurement"] == "ACTUAL"

    async def test_un_coste_no_calculable_es_nulo_y_nunca_cero(
        self, monkeypatch: pytest.MonkeyPatch, credenciales: None
    ) -> None:
        """Cero significaría gratis, y una llamada sin uso informado no lo es."""
        from llm_gateway import TokenUsage

        _instalar_gateway(
            monkeypatch,
            FakeProviderAdapter(usage=TokenUsage.unknown()),
            prefixes=("gpt-",),
        )

        result = await _analizar()

        assert result["cost_usd"] is None
        assert result["cost_measurement"] == "UNAVAILABLE"

    async def test_el_formato_texto_devuelve_la_respuesta_cruda(
        self, monkeypatch: pytest.MonkeyPatch, credenciales: None
    ) -> None:
        _instalar_gateway(monkeypatch, FakeProviderAdapter(text="texto llano"), prefixes=("gpt-",))

        result = await _analizar(response_format="text")

        assert result["response"] == "texto llano"


class TestErrores:
    async def test_una_credencial_ausente_no_llega_a_llamar_al_proveedor(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        adapter = FakeProviderAdapter()
        _instalar_gateway(monkeypatch, adapter, prefixes=("gpt-",))

        result = await _analizar()

        assert result["error"] == "OPENAI_API_KEY not set"
        assert result["detail"] == "No API key available for OpenAI models"
        assert adapter.requests == []

    async def test_un_json_que_no_es_un_objeto_no_pasa_por_analisis(
        self, monkeypatch: pytest.MonkeyPatch, credenciales: None
    ) -> None:
        """Si se aceptase, el JSONL guardaría un registro con aspecto de analizado.

        `ensure_required_keys` rellenaría los campos con valores por defecto y
        nada delataría que el modelo no devolvió un análisis.
        """
        _instalar_gateway(
            monkeypatch,
            FakeProviderAdapter(text='["no", "es", "un", "objeto"]'),
            prefixes=("gpt-",),
        )

        result = await _analizar()

        assert result["detail"] == "LLM request failed"
        assert "list" in result["error"]

    async def test_un_fallo_del_proveedor_se_devuelve_como_dict_y_no_rompe_el_lote(
        self, monkeypatch: pytest.MonkeyPatch, credenciales: None
    ) -> None:
        """Una sentencia que falla no puede tumbar las otras 105."""
        _instalar_gateway(
            monkeypatch,
            FakeProviderAdapter(error=RuntimeError("el proveedor se cayó")),
            prefixes=("gpt-",),
        )

        result = await _analizar()

        assert result["detail"] == "LLM request failed"
        assert "error" in result


class TestTraduccionDeParametros:
    async def test_un_modelo_de_razonamiento_no_recibe_temperatura_cero(
        self, monkeypatch: pytest.MonkeyPatch, credenciales: None
    ) -> None:
        """La API la rechaza: 'temperature' is not supported with this model."""
        adapter = FakeProviderAdapter()
        _instalar_gateway(monkeypatch, adapter, prefixes=("gpt-",))

        await _analizar(temperature=0)

        assert adapter.requests[0].temperature == 1

    async def test_los_demas_modelos_conservan_la_temperatura_pedida(
        self, monkeypatch: pytest.MonkeyPatch, credenciales: None
    ) -> None:
        adapter = FakeProviderAdapter(name="gemini")
        _instalar_gateway(monkeypatch, adapter, prefixes=("gemini",))

        await _analizar(model="gemini-3.6-flash", temperature=0)

        assert adapter.requests[0].temperature == 0

    async def test_el_esfuerzo_de_razonamiento_solo_viaja_donde_existe(
        self, monkeypatch: pytest.MonkeyPatch, credenciales: None
    ) -> None:
        adapter = FakeProviderAdapter(name="gemini")
        _instalar_gateway(monkeypatch, adapter, prefixes=("gemini",))

        await _analizar(model="gemini-3.6-flash", reasoning_effort="high")

        assert adapter.requests[0].reasoning_effort is None

    async def test_el_esfuerzo_de_razonamiento_llega_a_openai(
        self, monkeypatch: pytest.MonkeyPatch, credenciales: None
    ) -> None:
        adapter = FakeProviderAdapter()
        _instalar_gateway(monkeypatch, adapter, prefixes=("gpt-",))

        await _analizar(reasoning_effort="max")

        assert adapter.requests[0].reasoning_effort == "max"

    async def test_el_prompt_de_sistema_no_se_mezcla_con_el_texto_de_la_sentencia(
        self, monkeypatch: pytest.MonkeyPatch, credenciales: None
    ) -> None:
        adapter = FakeProviderAdapter()
        _instalar_gateway(monkeypatch, adapter, prefixes=("gpt-",))

        await _analizar()

        peticion = adapter.requests[0]
        assert peticion.system_prompt == "Analiza la sentencia y devuelve json."
        assert [m.content for m in peticion.messages] == ["--- PÁGINA 1 ---\nAUDIENCIA NACIONAL"]


class TestPoliticas:
    async def test_no_hay_respaldo_de_modelo(
        self, monkeypatch: pytest.MonkeyPatch, credenciales: None
    ) -> None:
        """Si contestara otro modelo, el export declararía el que no respondió."""
        adapter = FakeProviderAdapter()
        _instalar_gateway(monkeypatch, adapter, prefixes=("gpt-",))

        await _analizar()

        assert adapter.requests[0].fallback_policy.enabled is False

    async def test_el_reintento_cabe_dentro_del_presupuesto_declarado(
        self, monkeypatch: pytest.MonkeyPatch, credenciales: None
    ) -> None:
        """Sin tope por intento, el primero puede agotar el presupuesto entero.

        `per_attempt_seconds` cae en `total_seconds` cuando no se fija, así que
        un intento colgado dejaría al reintento sin tiempo y el reintento sería
        decorativo.
        """
        adapter = FakeProviderAdapter()
        _instalar_gateway(monkeypatch, adapter, prefixes=("gpt-",))

        await _analizar()

        peticion = adapter.requests[0]
        presupuesto = peticion.timeout_policy
        assert peticion.retry_policy.max_attempts == 2
        assert peticion.retry_policy.retry_transient_only is True
        assert (
            presupuesto.per_attempt_seconds * peticion.retry_policy.max_attempts
            <= presupuesto.total_seconds
        )

    async def test_un_limite_de_ritmo_se_reintenta_y_la_sentencia_se_salva(
        self, monkeypatch: pytest.MonkeyPatch, credenciales: None
    ) -> None:
        """Es el caso que motiva el reintento: 106 sentencias en tandas de 10."""

        class FallaUnaVez(FakeProviderAdapter):
            async def generate(self, request: Any, *, model: str) -> Any:
                from llm_gateway import ProviderResponse, RateLimitedError, TokenUsage

                self.requests.append(request)
                if len(self.requests) == 1:
                    raise RateLimitedError("demasiadas peticiones")
                return ProviderResponse(
                    output_text=ANALISIS_JSON,
                    usage=TokenUsage(1000, 200),
                    finish_reason="completed",
                )

        adapter = FallaUnaVez()
        _instalar_gateway(monkeypatch, adapter, prefixes=("gpt-",))

        result = await _analizar()

        assert result["resultado_final"] == "GANA_AEAT"
        assert len(adapter.requests) == 2

    async def test_un_error_no_transitorio_no_se_reintenta(
        self, monkeypatch: pytest.MonkeyPatch, credenciales: None
    ) -> None:
        """Un prompt inválido falla igual la segunda vez, y se cobra dos veces."""
        from llm_gateway import InvalidRequestError

        adapter = FakeProviderAdapter(error=InvalidRequestError("schema inaceptable"))
        _instalar_gateway(monkeypatch, adapter, prefixes=("gpt-",))

        result = await _analizar()

        assert result["detail"] == "LLM request failed"
        assert len(adapter.requests) == 1
