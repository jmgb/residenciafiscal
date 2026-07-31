"""Composition root del chat comparativo de producción.

Se importa de forma perezosa desde la ruta HTTP. Preparar sentencias, ejecutar
tests o servir `/health` no inicializa clientes ni exige credenciales.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException

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

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS = PROJECT_ROOT / "knowledge/jurisprudencia-v3/retrieval/corpus.json"
DEFAULT_STORE_STATE = PROJECT_ROOT / "output/file-search/f0-store.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output/file-search/live"
DEFAULT_LOG = PROJECT_ROOT / "output/logs/chat-strategy-comparison.jsonl"


def _enabled(name: str) -> bool:
    return os.getenv(name, "false").strip().lower() in {"1", "true", "yes"}


def _path_from_env(name: str, default: Path) -> Path:
    value = os.getenv(name, "").strip()
    return Path(value).resolve() if value else default


class ProductionChatRunner:
    def __init__(
        self,
        *,
        structured: CurrentStructuredStrategy,
        file_search: GeminiFileSearchResponder,
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

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="Falta la credencial de Gemini")

    corpus_path = _path_from_env("CHAT_RETRIEVAL_CORPUS", DEFAULT_CORPUS)
    store_state_path = _path_from_env("CHAT_FILE_SEARCH_STORE_STATE", DEFAULT_STORE_STATE)
    if not corpus_path.is_file() or not store_state_path.is_file():
        raise HTTPException(status_code=503, detail="Faltan artefactos del chat")

    file_search_model = os.getenv("CHAT_FILE_SEARCH_MODEL", DEFAULT_FILE_SEARCH_MODEL).strip()
    if file_search_model not in SUPPORTED_FILE_SEARCH_MODELS:
        raise HTTPException(status_code=503, detail="Modelo File Search no permitido")

    receipt = StoreReceipt.model_validate_json(store_state_path.read_bytes())
    corpus = load_retrieval_corpus(corpus_path.read_bytes())
    google_gateway = create_google_genai_gateway(api_key)
    verbatim_artifacts = {
        document.judgment_id: (
            PROJECT_ROOT / f"knowledge/jurisprudencia-v3/verbatim/{document.judgment_id}.pages.json"
        )
        for document in receipt.documents
    }
    if any(not path.is_file() for path in verbatim_artifacts.values()):
        raise HTTPException(status_code=503, detail="Faltan textos literales para validar citas")

    return ProductionChatRunner(
        structured=CurrentStructuredStrategy(
            corpus,
            writer=GatewayChatWriter(get_gateway()),
        ),
        file_search=GeminiFileSearchResponder(
            gateway=google_gateway,
            store_name=receipt.store_name,
            verbatim_artifacts=verbatim_artifacts,
            model=file_search_model,
        ),
        output_dir=_path_from_env("CHAT_COMPARISON_OUTPUT_DIR", DEFAULT_OUTPUT_DIR),
        log_path=_path_from_env("CHAT_COMPARISON_LOG", DEFAULT_LOG),
    )
