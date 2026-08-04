"""Respuesta Gemini File Search con gate local de citas literales."""

from __future__ import annotations

import asyncio
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

from chat_answer_contract import ChatAnswerDraft
from chat_answer_prompt import file_search_answer_prompt
from chat_error_names import safe_error_name
from chat_strategy_costs import (
    DEFAULT_FILE_SEARCH_MODEL,
    SUPPORTED_FILE_SEARCH_MODELS,
    GeminiUsage,
    calculate_gemini_file_search_cost,
)
from chat_strategy_models import AnswerStatus, MarginalCost, StrategyAnswer, StrategySource
from judicial_authority import (
    authority_label,
    authority_match,
    authority_metadata_filter,
    requested_judicial_authority,
)
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
        first, retry = await self._answer_once(question, request_id=request_id)
        if not retry:
            return first
        try:
            second, _ = await self._answer_once(question, request_id=request_id)
        except Exception as error:
            return first.model_copy(
                update={
                    "limits": (*first.limits, "El segundo intento no pudo completarse."),
                    "diagnostics": {
                        **(first.diagnostics or {}),
                        "failure_code": "citation_verification",
                        "retry_error_name": safe_error_name(error),
                    },
                }
            )
        return second.model_copy(update={"cost": _sum_costs(first.cost, second.cost)})

    async def _answer_once(self, question: str, *, request_id: str) -> tuple[StrategyAnswer, bool]:
        started = time.perf_counter()
        authority_intent = requested_judicial_authority(question)
        metadata_filter = authority_metadata_filter(authority_intent)
        authority_instruction = (
            f" La pregunta pide {authority_label(authority_intent)}: usa autoridad directa de ese "
            "órgano y no presentes como propia doctrina contenida solo en una sentencia de otro "
            "tribunal."
            if authority_intent
            else ""
        )
        interaction = await asyncio.to_thread(
            self._gateway.query,
            model=self._model,
            store_name=self._store_name,
            prompt=file_search_answer_prompt(question, authority_instruction=authority_instruction),
            response_schema=ChatAnswerDraft.model_json_schema(),
            metadata_filter=metadata_filter,
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
        had_substantive_response = provider_answer.status in {"completa", "parcial"} and bool(
            answer_text
        )
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
        direct_authority = authority_match(
            authority_intent, tuple(source.judgment_id for source in sources)
        )
        if authority_intent and direct_authority == "missing" and status != "error":
            limits = (
                *limits,
                "Las citas verificadas no proceden directamente del "
                f"{authority_label(authority_intent)}.",
            )
            if status == "completa":
                status = "parcial"
        diagnostics = {
            "authority_intent": authority_intent,
            "authority_match": direct_authority,
            "retrieval_filter": metadata_filter,
            "retrieved_judgment_ids": list(dict.fromkeys(source.judgment_id for source in sources)),
            "citation_candidates": citation_count,
            "citation_verified": len(sources),
            "failure_code": "citation_verification" if status == "error" else None,
            "error_name": None,
        }
        result = StrategyAnswer(
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
            reasoning_effort=None,
            latency_ms=round((time.perf_counter() - started) * 1000),
            diagnostics=diagnostics,
        )
        should_retry = had_substantive_response and not sources
        return result, should_retry


def _sum_costs(first: MarginalCost, second: MarginalCost) -> MarginalCost:
    """Suma los dos intentos conservando lo que sí se midió.

    Descartar el importe del primer intento porque el segundo no trajo uso
    facturable convertiría gasto real en `UNAVAILABLE`, y el resumen diario lo
    leería como cero. Se suma lo conocido y la medición baja a `ESTIMATED`:
    hubo coste, y el total es un mínimo, no una incógnita.
    """
    measurements = {first.measurement, second.measurement}
    known = [cost for cost in (first, second) if cost.cost_microusd is not None]
    if not known:
        return first.model_copy(
            update={
                "amount_usd": None,
                "cost_microusd": None,
                "measurement": "UNAVAILABLE",
                "input_tokens": None,
                "output_tokens": None,
                "retrieved_document_tokens": None,
            }
        )
    measurement = "ACTUAL" if measurements == {"ACTUAL"} else "ESTIMATED"

    def total(name: str) -> int | None:
        values = [getattr(cost, name) for cost in known]
        return (
            sum(value for value in values if value is not None)
            if any(value is not None for value in values)
            else None
        )

    return first.model_copy(
        update={
            "amount_usd": sum(
                (cost.amount_usd for cost in known if cost.amount_usd is not None),
                Decimal("0"),
            ),
            "cost_microusd": sum(
                cost.cost_microusd for cost in known if cost.cost_microusd is not None
            ),
            "measurement": measurement,
            "input_tokens": total("input_tokens"),
            "output_tokens": total("output_tokens"),
            "retrieved_document_tokens": total("retrieved_document_tokens"),
        }
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
