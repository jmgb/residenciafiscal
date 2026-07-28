"""API HTTP mínima sobre el pipeline de residencia fiscal.

No duplica lógica: reutiliza `process_pdf_async()` de `residenciafiscal.py`,
que es la unidad de trabajo por PDF (extracción de texto + llamada LLM +
normalización de schema).

Arranque en local:
    make dev            # uvicorn con reload en 127.0.0.1:8000
    make dev-public     # accesible desde la red local (0.0.0.0)

Endpoints:
    GET  /health        Estado del servicio y proveedor configurado
    GET  /config        Modelos, criterios y categorías vigentes
    POST /analizar      Sube un PDF y devuelve el análisis en JSON
    GET  /docs          Swagger UI (autogenerado por FastAPI)
"""

from __future__ import annotations

import logging
import os
import secrets
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse

from config import (
    DEFAULT_MODEL,
    GEMINI_FLASH,
    GEMINI_PRO,
    GPT_4,
    GPT_4_MINI,
    GPT_4_TURBO,
    GPT_5,
    GPT_5_MINI,
    GPT_5_NANO,
    REASONING_EFFORT,
    SENTENCIA_CLAVE_MODEL,
    VALID_CATEGORIAS_PRUEBA,
    VALID_CRITERIOS,
    VALID_RESULTADO_FINAL,
)
from residenciafiscal import initialize_client, load_key_sentencias, process_pdf_async

load_dotenv()

logger = logging.getLogger(__name__)

# Límite de tamaño para el PDF subido (evita agotar memoria/disco con un upload
# hostil; una sentencia del CENDOJ rara vez pasa de 2 MB).
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
UPLOAD_CHUNK_BYTES = 1024 * 1024

# Modelos que /analizar acepta en el campo `modelo`. Es una allowlist deliberada:
# `initialize_client()` y `_detect_provider()` del adaptador difieren en el fallback
# para IDs desconocidos (openrouter vs openai), así que un ID arbitrario validaría
# una API key y usaría otra. Restringiendo a los modelos declarados en config.py
# ambos coinciden siempre.
MODELOS_PERMITIDOS = {
    GPT_4,
    GPT_4_MINI,
    GPT_4_TURBO,
    GPT_5,
    GPT_5_MINI,
    GPT_5_NANO,
    GEMINI_PRO,
    GEMINI_FLASH,
}

# Token opcional. Si RESIDENCIAFISCAL_API_TOKEN está definido, /analizar (la única
# ruta que gasta dinero) exige la cabecera X-API-Token. Sin token definido la API
# queda abierta, que es lo cómodo en local con `make dev` (127.0.0.1). Para
# `make dev-public`, que escucha en 0.0.0.0, define el token en .env.
API_TOKEN = os.getenv("RESIDENCIAFISCAL_API_TOKEN", "").strip()

# Se rellena en el lifespan: nombres de sentencias que usan el modelo premium.
_key_sentencias: set[str] = set()


async def require_token(
    x_api_token: Annotated[str | None, Header(alias="X-API-Token")] = None,
) -> None:
    """Exige X-API-Token solo si RESIDENCIAFISCAL_API_TOKEN está configurado."""
    if not API_TOKEN:
        return
    if not x_api_token or not secrets.compare_digest(x_api_token, API_TOKEN):
        raise HTTPException(
            status_code=401, detail="Token ausente o inválido (cabecera X-API-Token)"
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Valida credenciales al arrancar y precarga la lista de sentencias clave."""
    global _key_sentencias
    try:
        provider = initialize_client(DEFAULT_MODEL)
        logger.info("✅ API lista (proveedor: %s)", provider)
    except RuntimeError as exc:
        # No abortamos el arranque: /health lo reporta y el error real sale al
        # llamar a /analizar. Así `make dev` sirve para inspeccionar /docs sin
        # tener las API keys exportadas.
        logger.warning("⚠️ Credenciales incompletas: %s", exc)
    _key_sentencias = load_key_sentencias()
    if not API_TOKEN:
        logger.warning(
            "⚠️ RESIDENCIAFISCAL_API_TOKEN no definido: /analizar queda sin autenticar. "
            "Defínelo en .env si expones la API fuera de localhost."
        )
    yield


app = FastAPI(
    title="Residencia Fiscal API",
    description="Analiza sentencias judiciales sobre residencia fiscal (Art. 9 LIRPF) con LLMs.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def rechazar_uploads_grandes(request: Request, call_next):
    """Corta por Content-Length antes de que Starlette parsee y vuelque el multipart.

    Sin esto, el límite del handler solo se aplica cuando el upload ya está entero en
    disco. No es infalible (una petición con Transfer-Encoding: chunked no trae
    Content-Length), por eso el handler mantiene su propio contador como respaldo.
    """
    if request.method in {"POST", "PUT", "PATCH"}:
        raw_length = request.headers.get("content-length")
        if raw_length is not None:
            try:
                if int(raw_length) > MAX_UPLOAD_BYTES:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": f"Petición demasiado grande "
                            f"(máximo {MAX_UPLOAD_BYTES // 1024 // 1024} MB)"
                        },
                    )
            except ValueError:
                return JSONResponse(
                    status_code=400, content={"detail": "Cabecera Content-Length inválida"}
                )
    return await call_next(request)


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health() -> dict[str, Any]:
    """Estado del servicio y disponibilidad de credenciales."""
    api_keys = {
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "groq": bool(os.getenv("GROQ_API_KEY")),
        "gemini": bool(os.getenv("GEMINI_API_KEY")),
    }
    return {
        "status": "ok",
        "modelo_default": DEFAULT_MODEL,
        "modelo_sentencias_clave": SENTENCIA_CLAVE_MODEL,
        "api_keys_presentes": api_keys,
        "sentencias_clave_cargadas": len(_key_sentencias),
    }


@app.get("/config")
async def get_config() -> dict[str, Any]:
    """Enums y modelos vigentes, para que un cliente sepa qué esperar."""
    return {
        "modelo_default": DEFAULT_MODEL,
        "modelo_sentencias_clave": SENTENCIA_CLAVE_MODEL,
        "reasoning_effort_default": REASONING_EFFORT,
        "modelos_permitidos": sorted(MODELOS_PERMITIDOS),
        "criterios": sorted(VALID_CRITERIOS),
        "categorias_prueba": sorted(VALID_CATEGORIAS_PRUEBA),
        "resultados_finales": sorted(VALID_RESULTADO_FINAL),
        "auth_requerida": bool(API_TOKEN),
    }


@app.post("/analizar", dependencies=[Depends(require_token)])
async def analizar(
    archivo: Annotated[UploadFile, File(description="Sentencia en PDF (con texto, no escaneada)")],
    modelo: Annotated[
        str | None, Form(description="Modelo LLM; ver /config → modelos_permitidos")
    ] = None,
    reasoning_effort: Annotated[
        str | None, Form(description="low | medium | high (solo modelos GPT-5+)")
    ] = None,
    max_pages: Annotated[
        int | None, Form(description="Limitar páginas leídas del PDF (entero positivo)")
    ] = None,
) -> dict[str, Any]:
    """Analiza un PDF y devuelve el objeto estructurado del pipeline.

    Si el nombre del fichero está en `sentencias_CLAVE.txt` se usa el modelo
    premium, igual que en la ejecución por lotes.
    """
    filename = archivo.filename or "upload.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se aceptan ficheros .pdf")

    if reasoning_effort is not None and reasoning_effort not in {"low", "medium", "high"}:
        raise HTTPException(
            status_code=400, detail="reasoning_effort debe ser low, medium o high"
        )

    if max_pages is not None and max_pages < 1:
        # Sin esto, extract_pdf_text_with_pages() calcula un límite negativo, no lee
        # nada y la API devolvería un 200 con un registro de confianza BAJA.
        raise HTTPException(status_code=400, detail="max_pages debe ser un entero positivo")

    if modelo is not None and modelo not in MODELOS_PERMITIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Modelo no soportado. Permitidos: {', '.join(sorted(MODELOS_PERMITIDOS))}",
        )

    ai_model = modelo or DEFAULT_MODEL
    if Path(filename).name in _key_sentencias:
        ai_model = SENTENCIA_CLAVE_MODEL
        logger.info("🔑 %s es sentencia clave: se usa %s", filename, ai_model)

    # Fallamos antes de escribir el fichero si falta la API key del proveedor.
    try:
        initialize_client(ai_model)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # `process_pdf_async` trabaja sobre una ruta, así que volcamos el upload a
    # un temporal con el nombre original (el pipeline lo usa como `archivo`).
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / Path(filename).name
        written = 0
        with pdf_path.open("wb") as fh:
            while chunk := await archivo.read(UPLOAD_CHUNK_BYTES):
                written += len(chunk)
                if written > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"PDF demasiado grande (máximo {MAX_UPLOAD_BYTES // 1024 // 1024} MB)",
                    )
                fh.write(chunk)

        if written == 0:
            raise HTTPException(status_code=400, detail="El fichero subido está vacío")

        resultado = await process_pdf_async(
            pdf_path=pdf_path,
            ai_model=ai_model,
            max_pages=max_pages,
            reasoning_effort=reasoning_effort or REASONING_EFFORT,
        )

    return {"modelo_usado": ai_model, "analisis": resultado}
