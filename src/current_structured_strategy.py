"""Recuperación local y redacción LLM verificable de la estrategia A."""

from __future__ import annotations

import time
from collections.abc import Mapping
from pathlib import Path

from llm_gateway import CostMeasurement, ReasoningEffort

from chat_answer_contract import StructuredChatAnswerDraft
from chat_answer_prompt import (
    STRUCTURED_ANSWER_INSTRUCTIONS,
    structured_answer_prompt,
)
from chat_model_policy import CHAT_FALLBACK_MODELS, CHAT_MODEL, CHAT_REASONING_EFFORT
from chat_strategy_costs import PRICING_VERSION, unknown_failure_cost, zero_marginal_cost
from chat_strategy_models import MarginalCost, StrategyAnswer, StrategyClaim
from claim_evidence_relevance import claim_has_lexical_evidence
from judicial_authority import (
    JudicialAuthorityIntent,
    authority_label,
    authority_match,
    local_authority_filter,
    requested_judicial_authority,
)
from jurisprudence_phase_d_retrieval import ChatRetrievalResult, retrieve_for_chat
from jurisprudence_retrieval_corpus_models import RetrievalCorpus
from structured_answer_writer import (
    ChatWriterRequest,
    ChatWriterResult,
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
        model: str = CHAT_MODEL,
        reasoning_effort: ReasoningEffort | None = CHAT_REASONING_EFFORT,
        fallback_models: tuple[str, ...] = CHAT_FALLBACK_MODELS,
        verbatim_artifacts: Mapping[str, Path] | None = None,
    ) -> None:
        """A corre sobre el modelo del chat, no sobre el de File Search.

        Antes heredaba `DEFAULT_FILE_SEARCH_MODEL` porque el comparador pasaba
        un único `--model` a las dos estrategias. Eso ataba A a lo que B
        necesita —File Search es una capacidad de Gemini y ahí no cabe otro
        proveedor—, de modo que la política declarada en `chat_model_policy` no
        llegaba a ninguna llamada.

        El esfuerzo también viaja: sin él la petición salía con el valor por
        defecto del proveedor, así que declarar `max` no habría cambiado nada.
        """
        self._corpus = corpus
        self._units = {unit.unit_id: unit for unit in corpus.units}
        self._writer = writer
        self._model = model
        self._reasoning_effort = reasoning_effort
        self._fallback_models = fallback_models
        # Sin las páginas verbatim, cada cita se publica como la línea suelta
        # del anclaje, sin el contexto que permite comprobar de qué habla.
        self._verbatim_artifacts = verbatim_artifacts

    async def answer(self, question: str, *, request_id: str) -> StrategyAnswer:
        started = time.perf_counter()
        authority_intent = requested_judicial_authority(question)
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
            self._verbatim_artifacts,
        )
        writer_result = await self._writer.write(
            ChatWriterRequest(
                model=self._model,
                system_prompt=STRUCTURED_ANSWER_INSTRUCTIONS,
                user_prompt=structured_answer_prompt(question, bundle.context_json),
                evidence_context=bundle.context_json,
                response_schema=StructuredChatAnswerDraft.model_json_schema(),
                reasoning_effort=self._reasoning_effort,
                fallback_models=self._fallback_models,
            )
        )
        cost = _as_marginal_cost(writer_result)
        effort = str(self._reasoning_effort) if self._reasoning_effort else None
        drafted_claims = writer_result.draft.claims
        candidate_evidence_ids = tuple(
            dict.fromkeys(
                evidence_id for claim in drafted_claims for evidence_id in claim.evidence_ids
            )
        )
        unknown = tuple(
            evidence_id
            for evidence_id in candidate_evidence_ids
            if evidence_id not in bundle.sources_by_evidence_id
        )
        empty_claims = tuple(
            claim for claim in drafted_claims if not claim.text.strip() or not claim.evidence_ids
        )
        substantive = writer_result.draft.status in {"completa", "parcial"}
        # El gate léxico solo puede evaluarse si todos los IDs resuelven a una
        # fuente; con un ID desconocido la respuesta ya está descartada.
        irrelevant_positions = (
            frozenset()
            if unknown
            else frozenset(
                position
                for position, claim in enumerate(drafted_claims)
                if not claim_has_lexical_evidence(
                    claim.text,
                    [bundle.sources_by_evidence_id[e] for e in claim.evidence_ids],
                )
            )
        )
        if (
            unknown
            or empty_claims
            or (substantive and not candidate_evidence_ids)
            or (substantive and drafted_claims and len(irrelevant_positions) == len(drafted_claims))
        ):
            return _grounding_error(
                _grounding_reason(unknown, empty_claims, candidate_evidence_ids),
                cost=cost,
                model=writer_result.model_used,
                reasoning_effort=effort,
                started=started,
                diagnostics=_retrieval_diagnostics(
                    retrieval,
                    authority_intent=authority_intent,
                    authority_match="not_requested",
                    citation_candidates=len(candidate_evidence_ids),
                    failure_code="evidence_validation",
                ),
            )

        relevant_claims = tuple(
            claim
            for position, claim in enumerate(drafted_claims)
            if position not in irrelevant_positions
        )
        evidence_ids = tuple(
            dict.fromkeys(
                evidence_id for claim in relevant_claims for evidence_id in claim.evidence_ids
            )
        )
        sources = tuple(bundle.sources_by_evidence_id[evidence_id] for evidence_id in evidence_ids)
        source_index = {evidence_id: index for index, evidence_id in enumerate(evidence_ids, 1)}
        claims = tuple(
            StrategyClaim(
                text=claim.text.strip(),
                source_indexes=tuple(
                    source_index[evidence_id] for evidence_id in dict.fromkeys(claim.evidence_ids)
                ),
            )
            for claim in relevant_claims
        )
        direct_authority = authority_match(
            authority_intent, tuple(source.judgment_id for source in sources)
        )
        authority_limit = _authority_limit(authority_intent, direct_authority)
        relevance_limit = (
            f"Se retiró {len(irrelevant_positions)} afirmación sin respaldo literal suficiente."
            if irrelevant_positions
            else None
        )
        final_status = writer_result.draft.status
        if retrieval.behavior == "parcial" and final_status == "completa":
            final_status = "parcial"
        if (authority_limit or relevance_limit) and final_status == "completa":
            final_status = "parcial"
        return StrategyAnswer(
            strategy="current_structured",
            status=final_status,
            text=_claims_text(claims),
            sources=sources,
            limits=(
                *limits,
                *writer_result.draft.limits,
                *([relevance_limit] if relevance_limit else []),
                *([authority_limit] if authority_limit else []),
            ),
            cost=cost,
            model=writer_result.model_used,
            reasoning_effort=effort,
            latency_ms=round((time.perf_counter() - started) * 1000),
            claims=claims,
            diagnostics=_retrieval_diagnostics(
                retrieval,
                authority_intent=authority_intent,
                authority_match=direct_authority,
                citation_candidates=len(candidate_evidence_ids),
                citation_verified=len(sources),
            ),
        )


def _grounding_reason(
    unknown: tuple[str, ...],
    empty_claims: tuple[object, ...],
    candidate_evidence_ids: tuple[str, ...],
) -> str:
    if unknown:
        return f"El redactor devolvió evidencias desconocidas: {', '.join(unknown)}."
    if empty_claims:
        return "El redactor devolvió al menos una afirmación vacía o sin evidencia."
    if not candidate_evidence_ids:
        return "El redactor no vinculó ninguna evidencia a la respuesta sustantiva."
    return "Al menos una afirmación no guarda relación suficiente con sus extractos literales."


def _authority_limit(intent: JudicialAuthorityIntent | None, match: str) -> str | None:
    if intent is None or match != "missing":
        return None
    return f"Las citas verificadas no proceden directamente del {authority_label(intent)}."


def _claims_text(claims: tuple[StrategyClaim, ...]) -> str:
    """Compone la prosa pública solo desde afirmaciones verificadas."""
    return "\n".join(
        f"- {claim.text} " + "".join(f"[{index}]" for index in claim.source_indexes)
        for claim in claims
    )


def _as_marginal_cost(writer_result: ChatWriterResult) -> MarginalCost:
    """Traduce el importe del gateway, sin volver a calcularlo.

    Solo se rellena el desglose que el paquete no conoce: A no recupera
    documentos, así que su cuenta es cero, y el resto de campos de
    `MarginalCost` son etiquetas de alcance de este proyecto.

    Un importe indisponible cae en `unknown_failure_cost()`, que es lo que el
    proyecto ya usaba para eso: `MarginalCost` no sabe expresar `UNAVAILABLE`,
    y ese hueco es anterior a este cambio.
    """
    cost = writer_result.cost
    if cost.microusd is None or cost.amount_usd is None:
        return unknown_failure_cost()
    return MarginalCost(
        amount_usd=cost.amount_usd,
        cost_microusd=cost.microusd,
        measurement="ACTUAL" if cost.measurement is CostMeasurement.ACTUAL else "ESTIMATED",
        pricing_version=cost.pricing_version or PRICING_VERSION,
        input_tokens=writer_result.usage.input_tokens,
        output_tokens=writer_result.usage.output_tokens,
        retrieved_document_tokens=0,
    )


def _grounding_error(
    reason: str,
    *,
    cost: MarginalCost,
    model: str,
    reasoning_effort: str | None,
    started: float,
    diagnostics: dict[str, object],
) -> StrategyAnswer:
    return StrategyAnswer(
        strategy="current_structured",
        status="error",
        text="",
        sources=(),
        limits=(reason,),
        cost=cost,
        model=model,
        reasoning_effort=reasoning_effort,
        latency_ms=round((time.perf_counter() - started) * 1000),
        diagnostics=diagnostics,
    )


def _retrieval_diagnostics(
    retrieval: ChatRetrievalResult,
    *,
    authority_intent: JudicialAuthorityIntent | None,
    authority_match: str,
    citation_candidates: int = 0,
    citation_verified: int = 0,
    failure_code: str | None = None,
) -> dict[str, object]:
    return {
        "authority_intent": authority_intent,
        "authority_match": authority_match,
        "retrieval_filter": local_authority_filter(authority_intent),
        "retrieved_judgment_ids": list(dict.fromkeys(hit.judgment_id for hit in retrieval.hits)),
        "citation_candidates": citation_candidates,
        "citation_verified": citation_verified,
        "failure_code": failure_code,
        "error_name": None,
    }


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
