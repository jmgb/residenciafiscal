"""Respuesta Gemini File Search con gate local de citas literales."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

from chat_answer_contract import ChatAnswerDraft
from chat_answer_prompt import file_search_answer_prompt
from chat_strategy_costs import (
    DEFAULT_FILE_SEARCH_MODEL,
    SUPPORTED_FILE_SEARCH_MODELS,
    GeminiUsage,
    calculate_gemini_file_search_cost,
)
from chat_strategy_models import AnswerStatus, StrategyAnswer, StrategySource
from legal_text_matching import extract_verbatim_fragment, normalize_legal_text
from verbatim_models import VerbatimCorpus


def _metadata(annotation: Any) -> dict[str, object]:
    raw = getattr(annotation, "custom_metadata", None)
    if isinstance(raw, dict):
        return raw
    values: dict[str, object] = {}
    for item in raw or ():
        key = getattr(item, "key", None)
        if not key:
            continue
        string_value = getattr(item, "string_value", None)
        numeric_value = getattr(item, "numeric_value", None)
        values[str(key)] = string_value if string_value is not None else numeric_value
    return values


def _file_citations(interaction: Any) -> tuple[Any, ...]:
    citations: list[Any] = []
    for step in getattr(interaction, "steps", ()) or ():
        if getattr(step, "type", None) != "model_output":
            continue
        for content in getattr(step, "content", ()) or ():
            for annotation in getattr(content, "annotations", ()) or ():
                if getattr(annotation, "type", None) == "file_citation":
                    citations.append(annotation)
    return tuple(citations)


def _usage(interaction: Any) -> GeminiUsage:
    usage = getattr(interaction, "usage", None)
    if usage is None:
        return GeminiUsage(
            input_tokens=0,
            retrieved_document_tokens=0,
            output_tokens=0,
            usage_complete=False,
        )
    # `total_output_tokens` de la Interactions API **excluye** el razonamiento,
    # así que sumarlo es lo correcto: una llamada medida dio 33 de entrada, 9 de
    # salida y 1650 de razonamiento para un `total_tokens` de 1692. No confundir
    # con la Responses API de OpenAI, donde el razonamiento ya está dentro de la
    # salida y sumarlo lo factura dos veces.
    total_input = int(getattr(usage, "total_input_tokens", 0) or 0)
    total_output = int(getattr(usage, "total_output_tokens", 0) or 0)
    thought_tokens = int(getattr(usage, "total_thought_tokens", 0) or 0)
    modalities = getattr(usage, "input_tokens_by_modality", None)
    document_tokens = 0
    for item in modalities or ():
        modality = str(getattr(item, "modality", "")).lower()
        if modality.endswith("document"):
            document_tokens += int(getattr(item, "tokens", 0) or 0)
    complete = (
        getattr(usage, "total_input_tokens", None) is not None
        and getattr(usage, "total_output_tokens", None) is not None
        and modalities is not None
        and (not _file_citations(interaction) or document_tokens > 0)
    )
    return GeminiUsage(
        input_tokens=max(0, total_input - document_tokens),
        retrieved_document_tokens=document_tokens,
        output_tokens=total_output + thought_tokens,
        usage_complete=complete,
    )


def _load_verbatim(path: Path) -> VerbatimCorpus:
    return VerbatimCorpus.model_validate_json(path.read_bytes())


def _verify_citation(
    annotation: Any,
    artifacts: dict[str, Path],
) -> StrategySource | None:
    metadata = _metadata(annotation)
    judgment_id = metadata.get("judgment_id")
    source_sha256 = metadata.get("source_sha256")
    page_number = getattr(annotation, "page_number", None)
    candidate = getattr(annotation, "source", None)
    if not isinstance(judgment_id, str) or judgment_id not in artifacts:
        return None
    if not isinstance(source_sha256, str) or not isinstance(page_number, int):
        return None
    if not isinstance(candidate, str) or not candidate.strip():
        return None
    corpus = _load_verbatim(artifacts[judgment_id])
    if corpus.source_sha256 != source_sha256:
        return None
    if page_number < 1 or page_number > len(corpus.pages):
        return None
    page = corpus.pages[page_number - 1]
    quote = candidate if candidate in page.raw_page_text else None
    if quote is None:
        normalized = normalize_legal_text(candidate)
        quote = extract_verbatim_fragment(normalized, page.raw_page_text)
    if not quote:
        return None
    return StrategySource(
        strategy="gemini_file_search",
        judgment_id=judgment_id,
        page=page_number,
        source_sha256=source_sha256,
        quote=quote,
        verification="EXACT",
    )


class GeminiFileSearchResponder:
    """Consulta un único store y nunca publica una cita sin validarla localmente."""

    def __init__(
        self,
        *,
        gateway: Any,
        store_name: str,
        verbatim_artifacts: dict[str, Path],
        model: str = DEFAULT_FILE_SEARCH_MODEL,
    ) -> None:
        if model not in SUPPORTED_FILE_SEARCH_MODELS:
            raise ValueError(f"modelo File Search no permitido: {model}")
        self._gateway = gateway
        self._store_name = store_name
        self._verbatim_artifacts = verbatim_artifacts
        self._model = model

    async def answer(self, question: str, *, request_id: str) -> StrategyAnswer:
        started = time.perf_counter()
        interaction = await asyncio.to_thread(
            self._gateway.query,
            model=self._model,
            store_name=self._store_name,
            prompt=file_search_answer_prompt(question),
            response_schema=ChatAnswerDraft.model_json_schema(),
        )
        raw_output = getattr(interaction, "output_text", None)
        if not raw_output:
            raw_output = _model_output_text(interaction)
        provider_answer = ChatAnswerDraft.model_validate_json(raw_output)
        verified = tuple(
            source
            for annotation in _file_citations(interaction)
            if (source := _verify_citation(annotation, self._verbatim_artifacts)) is not None
        )
        sources = tuple(dict.fromkeys(verified))
        citation_count = len(_file_citations(interaction))
        status: AnswerStatus = provider_answer.status
        limits = provider_answer.limits
        answer_text = provider_answer.answer
        if status in {"completa", "parcial"} and answer_text and not sources:
            status = "error"
            answer_text = ""
            reason = (
                "Se retiraron citas no verificables contra el PDF original."
                if citation_count
                else "El proveedor no devolvió citas verificables para la respuesta."
            )
            limits = (
                reason,
                *limits,
            )
        return StrategyAnswer(
            strategy="gemini_file_search",
            status=status,
            text=answer_text,
            sources=sources,
            limits=limits,
            cost=calculate_gemini_file_search_cost(
                _usage(interaction),
                model=self._model,
            ),
            model=self._model,
            latency_ms=round((time.perf_counter() - started) * 1000),
        )


def _model_output_text(interaction: Any) -> str:
    chunks = [
        str(getattr(content, "text", ""))
        for step in getattr(interaction, "steps", ()) or ()
        if getattr(step, "type", None) == "model_output"
        for content in getattr(step, "content", ()) or ()
        if getattr(content, "type", None) == "text"
    ]
    return "".join(chunks)
