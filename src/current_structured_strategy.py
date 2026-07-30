"""Recuperación local y redacción LLM verificable de la estrategia A."""

from __future__ import annotations

import time

from chat_answer_contract import StructuredChatAnswerDraft
from chat_answer_prompt import (
    STRUCTURED_ANSWER_INSTRUCTIONS,
    structured_answer_prompt,
)
from chat_strategy_costs import (
    DEFAULT_FILE_SEARCH_MODEL,
    GeminiUsage,
    calculate_gemini_request_cost,
    zero_marginal_cost,
)
from chat_strategy_models import MarginalCost, StrategyAnswer
from jurisprudence_phase_d_retrieval import retrieve_for_chat
from jurisprudence_retrieval_corpus_models import RetrievalCorpus
from structured_answer_writer import (
    ChatWriterRequest,
    StructuredAnswerWriter,
)
from structured_evidence_context import build_structured_evidence_bundle


class CurrentStructuredStrategy:
    """Redacta solo con hits locales y resuelve sus fuentes por identificador."""

    def __init__(
        self,
        corpus: RetrievalCorpus,
        *,
        writer: StructuredAnswerWriter,
        model: str = DEFAULT_FILE_SEARCH_MODEL,
    ) -> None:
        self._corpus = corpus
        self._units = {unit.unit_id: unit for unit in corpus.units}
        self._writer = writer
        self._model = model

    async def answer(self, question: str, *, request_id: str) -> StrategyAnswer:
        started = time.perf_counter()
        retrieval = retrieve_for_chat(self._corpus, question, limit=5)
        status = {
            "responder": "completa",
            "parcial": "parcial",
            "preguntar": "pregunta",
            "abstenerse": "abstención",
        }[retrieval.behavior]
        limits = (*retrieval.missing_facts, *retrieval.uncovered_facets)
        if status in {"pregunta", "abstención"}:
            return StrategyAnswer(
                strategy="current_structured",
                status=status,
                text=_non_answer_text(
                    status,
                    retrieval.behavior_reasons,
                    retrieval.missing_facts,
                    retrieval.uncovered_facets,
                ),
                sources=(),
                limits=limits,
                cost=zero_marginal_cost(),
                model="deterministic-structured-v3",
                latency_ms=round((time.perf_counter() - started) * 1000),
            )

        bundle = build_structured_evidence_bundle(
            retrieval,
            self._units,
            question,
        )
        writer_result = await self._writer.write(
            ChatWriterRequest(
                model=self._model,
                system_prompt=STRUCTURED_ANSWER_INSTRUCTIONS,
                user_prompt=structured_answer_prompt(question, bundle.context_json),
                evidence_context=bundle.context_json,
                response_schema=StructuredChatAnswerDraft.model_json_schema(),
            )
        )
        cost = calculate_gemini_request_cost(
            GeminiUsage(
                input_tokens=writer_result.usage.input_tokens,
                retrieved_document_tokens=0,
                output_tokens=writer_result.usage.output_tokens,
                usage_complete=writer_result.usage.usage_complete,
            ),
            model=writer_result.model_used,
        )
        evidence_ids = tuple(dict.fromkeys(writer_result.draft.evidence_ids))
        unknown = tuple(
            evidence_id
            for evidence_id in evidence_ids
            if evidence_id not in bundle.sources_by_evidence_id
        )
        if unknown:
            return _grounding_error(
                f"El redactor devolvió evidencias desconocidas: {', '.join(unknown)}.",
                cost=cost,
                model=writer_result.model_used,
                started=started,
            )
        if writer_result.draft.status in {"completa", "parcial"} and not evidence_ids:
            return _grounding_error(
                "El redactor no vinculó ninguna evidencia a la respuesta sustantiva.",
                cost=cost,
                model=writer_result.model_used,
                started=started,
            )

        final_status = writer_result.draft.status
        if retrieval.behavior == "parcial" and final_status == "completa":
            final_status = "parcial"
        sources = tuple(
            dict.fromkeys(
                bundle.sources_by_evidence_id[evidence_id] for evidence_id in evidence_ids
            )
        )
        return StrategyAnswer(
            strategy="current_structured",
            status=final_status,
            text=writer_result.draft.answer,
            sources=sources,
            limits=(*limits, *writer_result.draft.limits),
            cost=cost,
            model=writer_result.model_used,
            latency_ms=round((time.perf_counter() - started) * 1000),
        )


def _grounding_error(
    reason: str,
    *,
    cost: MarginalCost,
    model: str,
    started: float,
) -> StrategyAnswer:
    return StrategyAnswer(
        strategy="current_structured",
        status="error",
        text="",
        sources=(),
        limits=(reason,),
        cost=cost,
        model=model,
        latency_ms=round((time.perf_counter() - started) * 1000),
    )


def _non_answer_text(
    status: str,
    reasons: tuple[str, ...],
    missing_facts: tuple[str, ...],
    uncovered_facets: tuple[str, ...],
) -> str:
    if status == "pregunta" and missing_facts:
        return (
            "Para buscar casos realmente comparables necesito que indiques: "
            f"{'; '.join(missing_facts)}."
        )
    if status == "abstención":
        uncovered = "; ".join(uncovered_facets)
        detail = uncovered or " ".join(reasons)
        return f"El corpus actual no cubre con suficiente precisión esta cuestión: {detail}."
    return " ".join(reasons)
