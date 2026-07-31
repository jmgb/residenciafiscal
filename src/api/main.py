"""API HTTP de estado y contratos públicos de residencia fiscal.

Arranque en local:
    make dev            # API + frontend en desarrollo
    make dev-api        # uvicorn con reload en 127.0.0.1:8010
    make dev-public     # accesible desde la red local (0.0.0.0)

Endpoints:
    GET  /health        Estado del servicio y separación de pipelines
    GET  /config        Política del chat y taxonomías vigentes
    GET  /docs          Swagger UI (autogenerado por FastAPI)

La preparación de sentencias no se expone por HTTP: es un workflow offline
Python + agente, sin llamadas del repositorio a un LLM.
"""

from __future__ import annotations

from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

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

app = FastAPI(
    title="Residencia Fiscal API",
    description="Contratos del corpus offline y del futuro chat jurisprudencial.",
    version="0.2.0",
)


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


@app.get("/config")
async def get_config() -> dict[str, Any]:
    """Política del futuro chat y taxonomías del corpus."""
    return {
        "chat_model": CHAT_MODEL,
        "chat_reasoning_effort": CHAT_REASONING_EFFORT,
        "chat_reasoning_efforts_permitidos": list(CHAT_SUPPORTED_REASONING_EFFORTS),
        "criterios": sorted(VALID_CRITERIOS),
        "categorias_prueba": sorted(VALID_CATEGORIAS_PRUEBA),
        "resultados_finales": sorted(VALID_RESULTADO_FINAL),
    }
