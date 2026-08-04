"""API HTTP de estado y contratos públicos de residencia fiscal.

Arranque en local:
    make dev            # API + frontend en desarrollo
    make dev-api        # uvicorn con reload en 127.0.0.1:8010
    make dev-public     # accesible desde la red local (0.0.0.0)

Endpoints:
    GET  /health        Estado del servicio y separación de pipelines
    GET  /config        Política del chat y taxonomías vigentes
    POST /chat          Comparación A/B por SSE; cerrada por defecto
    GET  /docs          Swagger UI (autogenerado por FastAPI)

La preparación de sentencias no se expone por HTTP: es un workflow offline
Python + agente, sin llamadas del repositorio a un LLM.
"""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse, RedirectResponse

from api.chat import router as chat_router
from api.chat_rate_limit import require_quota_when_exposed, require_single_process_state
from api.sentry_config import init_sentry
from chat_model_policy import (
    CHAT_MODEL,
    CHAT_REASONING_EFFORT,
    CHAT_SUPPORTED_REASONING_EFFORTS,
)
from config import (
    VALID_CATEGORIAS_PRUEBA,
    VALID_CRITERIOS,
    VALID_RESULTADO_FINAL,
)

load_dotenv()
init_sentry()
require_single_process_state()
require_quota_when_exposed()

app = FastAPI(
    title="Residencia Fiscal API",
    description="Contratos del corpus offline y del chat jurisprudencial comparativo.",
    version="0.3.0",
)
app.include_router(chat_router)


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health() -> dict[str, Any]:
    """Estado del servicio y frontera de responsabilidades."""
    return {
        "status": "ok",
        "corpus_pipeline": "python_agent_offline",
        "paid_sentence_analysis": False,
    }


@app.get("/health/live")
async def health_live() -> dict[str, str]:
    """Liveness sin filesystem, red ni inicialización de proveedores."""
    return {"status": "ok"}


@app.get("/health/ready", response_model=None)
async def health_ready() -> dict[str, Any] | JSONResponse:
    """Readiness barata para el monitor externo, sin llamadas pagadas."""
    from fastapi import HTTPException

    from api.chat_runtime import chat_artifacts_ready, runtime_release

    enabled = os.getenv("CHAT_COMPARISON_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    # La integridad de la release se comprueba también con el chat cerrado: un
    # servicio desplegado y en espera es justo donde una release manipulada
    # pasaría inadvertida hasta abrir tráfico.
    try:
        release = runtime_release()
        hashes_ready = True
    except HTTPException:
        release, hashes_ready = None, False

    body: dict[str, Any] = {
        "status": "ok" if hashes_ready else "not_ready",
        "chat_enabled": enabled,
        "paid_calls": False,
        "runtime_release": release,
        "runtime_hashes": hashes_ready,
    }
    if not enabled:
        return body if hashes_ready else JSONResponse(status_code=503, content=body)

    ready, detail = chat_artifacts_ready()
    body["status"] = "ok" if ready else "not_ready"
    body["artifacts"] = detail
    return body if ready else JSONResponse(status_code=503, content=body)


@app.get("/config")
async def get_config() -> dict[str, Any]:
    """Política vigente del chat y taxonomías del corpus."""
    return {
        "chat_model": CHAT_MODEL,
        "chat_reasoning_effort": CHAT_REASONING_EFFORT,
        "chat_reasoning_efforts_permitidos": list(CHAT_SUPPORTED_REASONING_EFFORTS),
        "criterios": sorted(VALID_CRITERIOS),
        "categorias_prueba": sorted(VALID_CATEGORIAS_PRUEBA),
        "resultados_finales": sorted(VALID_RESULTADO_FINAL),
    }
