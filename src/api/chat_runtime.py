"""Composition root del chat comparativo de producción.

Se importa de forma perezosa desde la ruta HTTP. Preparar sentencias, ejecutar
tests o servir `/health` no inicializa clientes ni exige credenciales.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException

from chat_runtime_artifact import verify_runtime_directory
from chat_strategy_comparison import compare_strategies
from chat_strategy_costs import DEFAULT_FILE_SEARCH_MODEL, SUPPORTED_FILE_SEARCH_MODELS
from chat_strategy_models import ComparisonReport
from current_structured_strategy import CurrentStructuredStrategy
from gateway_chat_writer import GatewayChatWriter
from gateway_setup import get_gateway
from gemini_file_search_answer import GeminiFileSearchResponder
from gemini_file_search_store import StoreReceipt
from google_genai_file_search import create_google_genai_gateway
from jurisprudence_retrieval_corpus import load_retrieval_corpus
from verbatim_models import VerbatimCorpus

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS = PROJECT_ROOT / "knowledge/jurisprudencia-v3/retrieval/rollout-106.corpus.json"
DEFAULT_STORE_STATE = PROJECT_ROOT / "output/file-search/rollout-106-store.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output/file-search/live"
DEFAULT_LOG = PROJECT_ROOT / "output/logs/chat-strategy-comparison.jsonl"


def _enabled(name: str, *, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes"}


def _path_from_env(name: str, default: Path) -> Path:
    value = os.getenv(name, "").strip()
    return Path(value).resolve() if value else default


def chat_artifacts_ready() -> tuple[bool, dict[str, bool]]:
    """Comprueba los artefactos de las estrategias activas, sin abrir clientes.

    Comparte con el constructor del runner las rutas y los interruptores por
    estrategia: una readiness con su propia copia acabaría declarando `ok`
    justo donde el runner responde `503`.
    """
    structured_enabled = _enabled("CHAT_STRATEGY_A_ENABLED", default=True)
    file_search_enabled = _enabled("CHAT_STRATEGY_B_ENABLED", default=True)
    corpus_ready = (
        not structured_enabled or _path_from_env("CHAT_RETRIEVAL_CORPUS", DEFAULT_CORPUS).is_file()
    )
    store_ready = (
        not file_search_enabled
        or _path_from_env("CHAT_FILE_SEARCH_STORE_STATE", DEFAULT_STORE_STATE).is_file()
    )
    # Sin esto, una release manipulada solo se detectaría en la primera
    # petición: el monitor externo diría `ok` hasta que llegara tráfico.
    try:
        runtime_release()
        hashes_ready = True
    except HTTPException:
        hashes_ready = False
    detail = {
        "strategy_a": structured_enabled,
        "strategy_b": file_search_enabled,
        "corpus": corpus_ready,
        "file_search_store": store_ready,
        "runtime_hashes": hashes_ready,
    }
    ready = (
        (structured_enabled or file_search_enabled)
        and corpus_ready
        and store_ready
        and hashes_ready
    )
    return ready, detail


@lru_cache(maxsize=1)
def _verified_release(manifest_key: str, required: bool, expected_version: str) -> str | None:
    """Verifica la release una vez por proceso y devuelve su versión.

    Se cachea porque también la consulta la readiness, y recorrer los 263
    ficheros en cada sonda del monitor sería gasto puro. Un artefacto no cambia
    bajo un proceso vivo: activar una release nueva recrea el contenedor.
    """
    manifest_path = (
        Path(manifest_key).resolve()
        if manifest_key
        else PROJECT_ROOT / "chat-runtime-manifest.json"
    )
    if not manifest_path.is_file():
        if required:
            raise HTTPException(status_code=503, detail="Falta el manifiesto del runtime")
        return None
    try:
        manifest = verify_runtime_directory(PROJECT_ROOT, manifest_path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=503, detail="Hashes del runtime no verificados") from error
    release = manifest.get("release_version")
    if expected_version and release != expected_version:
        raise HTTPException(status_code=503, detail="Versión del runtime no autorizada")
    return str(release) if release is not None else None


def runtime_release() -> str | None:
    """Release verificada, o `None` cuando no se exige manifiesto."""
    return _verified_release(
        os.getenv("CHAT_RUNTIME_MANIFEST", "").strip(),
        _enabled("CHAT_RUNTIME_HASH_REQUIRED"),
        os.getenv("CHAT_RUNTIME_VERSION", "").strip(),
    )


class ProductionChatRunner:
    def __init__(
        self,
        *,
        structured: CurrentStructuredStrategy | None,
        file_search: GeminiFileSearchResponder | None,
        output_dir: Path,
        log_path: Path,
    ) -> None:
        self._structured = structured
        self._file_search = file_search
        self._output_dir = output_dir
        self._log_path = log_path

    async def compare(self, question: str, *, request_id: str) -> ComparisonReport:
        return await compare_strategies(
            question=question,
            structured=self._structured,
            file_search=self._file_search,
            output_path=self._output_dir / f"{request_id}.json",
            log_path=self._log_path,
            request_id=request_id,
        )


@lru_cache(maxsize=1)
def get_production_chat_runner() -> ProductionChatRunner:
    """Crea un único runtime y permanece cerrado por defecto.

    La bandera es deliberadamente server-side. `VITE_*` nunca puede activar
    gasto ni exponer claves desde el navegador.
    """
    if not _enabled("CHAT_COMPARISON_ENABLED"):
        raise HTTPException(status_code=503, detail="Chat comparativo no habilitado")

    structured_enabled = _enabled("CHAT_STRATEGY_A_ENABLED", default=True)
    file_search_enabled = _enabled("CHAT_STRATEGY_B_ENABLED", default=True)
    if not structured_enabled and not file_search_enabled:
        raise HTTPException(status_code=503, detail="No hay estrategias activas")

    runtime_release()
    corpus_path = _path_from_env("CHAT_RETRIEVAL_CORPUS", DEFAULT_CORPUS)
    store_state_path = _path_from_env("CHAT_FILE_SEARCH_STORE_STATE", DEFAULT_STORE_STATE)
    if structured_enabled and not corpus_path.is_file():
        raise HTTPException(status_code=503, detail="Falta el corpus del chat")
    if file_search_enabled and not store_state_path.is_file():
        raise HTTPException(status_code=503, detail="Faltan artefactos del chat")

    corpus = load_retrieval_corpus(corpus_path.read_bytes()) if structured_enabled else None
    # A también necesita las páginas verbatim: sin ellas publica el anclaje
    # suelto en lugar de la cita con su contexto de la misma página.
    structured_verbatim: dict[str, Path] = (
        {
            source.judgment_id: (
                PROJECT_ROOT
                / f"knowledge/jurisprudencia-v3/verbatim/{source.judgment_id}.pages.json"
            )
            for source in corpus.sources
        }
        if corpus is not None
        else {}
    )
    receipt = None
    file_search_model = DEFAULT_FILE_SEARCH_MODEL
    google_gateway = None
    verbatim_artifacts: dict[str, Path] = {}
    if file_search_enabled:
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise HTTPException(status_code=503, detail="Falta la credencial de Gemini")
        file_search_model = os.getenv("CHAT_FILE_SEARCH_MODEL", DEFAULT_FILE_SEARCH_MODEL).strip()
        if file_search_model not in SUPPORTED_FILE_SEARCH_MODELS:
            raise HTTPException(status_code=503, detail="Modelo File Search no permitido")
        try:
            receipt = StoreReceipt.model_validate_json(store_state_path.read_bytes())
        except (OSError, ValueError) as error:
            raise HTTPException(status_code=503, detail="Recibo del store no válido") from error
        receipt_ids = {document.judgment_id for document in receipt.documents}
        corpus_ids = {source.judgment_id for source in corpus.sources} if corpus else set()
        if (
            receipt.schema_version != "residenciafiscal-file-search-store/2"
            or receipt.status != "ACTIVE"
            or receipt.expected_documents != 106
            or len(receipt.documents) != 106
            or (structured_enabled and receipt_ids != corpus_ids)
        ):
            raise HTTPException(status_code=503, detail="Store y corpus del chat no coinciden")
        google_gateway = create_google_genai_gateway(api_key)
        verbatim_artifacts = {
            document.judgment_id: (
                PROJECT_ROOT
                / f"knowledge/jurisprudencia-v3/verbatim/{document.judgment_id}.pages.json"
            )
            for document in receipt.documents
        }
        if any(not path.is_file() for path in verbatim_artifacts.values()):
            raise HTTPException(
                status_code=503, detail="Faltan textos literales para validar citas"
            )
        for document in receipt.documents:
            try:
                verbatim = VerbatimCorpus.model_validate_json(
                    verbatim_artifacts[document.judgment_id].read_bytes()
                )
            except ValueError as error:
                raise HTTPException(
                    status_code=503, detail="Verbatim del chat no válido"
                ) from error
            if (
                verbatim.document_id != document.judgment_id
                or verbatim.source_sha256 != document.source_sha256
            ):
                raise HTTPException(status_code=503, detail="Verbatim y store no coinciden")

    return ProductionChatRunner(
        structured=(
            CurrentStructuredStrategy(
                corpus,
                writer=GatewayChatWriter(get_gateway()),
                verbatim_artifacts=structured_verbatim,
            )
            if structured_enabled and corpus is not None
            else None
        ),
        file_search=(
            GeminiFileSearchResponder(
                gateway=google_gateway,
                store_name=receipt.store_name if receipt is not None else "",
                verbatim_artifacts=verbatim_artifacts,
                model=file_search_model,
            )
            if file_search_enabled and google_gateway is not None and receipt is not None
            else None
        ),
        output_dir=_path_from_env("CHAT_COMPARISON_OUTPUT_DIR", DEFAULT_OUTPUT_DIR),
        log_path=_path_from_env("CHAT_COMPARISON_LOG", DEFAULT_LOG),
    )
