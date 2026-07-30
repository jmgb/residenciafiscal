"""Render determinista de la recuperación estructurada vigente para F0."""

from __future__ import annotations

import time

from chat_strategy_costs import zero_marginal_cost
from chat_strategy_models import StrategyAnswer, StrategySource
from jurisprudence_case_retrieval_models import RetrievalUnit
from jurisprudence_phase_d_retrieval import retrieve_for_chat
from jurisprudence_retrieval_corpus_models import RetrievalCorpus


class CurrentStructuredStrategy:
    """Convierte hits auditables en una respuesta local sin llamadas de pago."""

    def __init__(self, corpus: RetrievalCorpus) -> None:
        self._corpus = corpus
        self._units = {unit.unit_id: unit for unit in corpus.units}

    def answer(self, question: str, *, request_id: str) -> StrategyAnswer:
        started = time.perf_counter()
        retrieval = retrieve_for_chat(self._corpus, question, limit=5)
        units = tuple(self._units[hit.unit_id] for hit in retrieval.hits)
        status = {
            "responder": "completa",
            "parcial": "parcial",
            "preguntar": "pregunta",
            "abstenerse": "abstención",
        }[retrieval.behavior]
        text = _render_text(status, units, retrieval.behavior_reasons)
        sources = tuple(
            StrategySource(
                strategy="current_structured",
                judgment_id=unit.judgment_id,
                page=fragment.page_index,
                source_sha256=anchor.source_sha256,
                quote=fragment.verbatim_text,
                verification="EXACT",
            )
            for unit in units
            for anchor in unit.source_anchors
            for fragment in anchor.fragments
        )
        limits = (*retrieval.missing_facts, *retrieval.uncovered_facets)
        return StrategyAnswer(
            strategy="current_structured",
            status=status,
            text=text,
            sources=tuple(dict.fromkeys(sources)),
            limits=limits,
            cost=zero_marginal_cost(),
            model="deterministic-structured-v3",
            latency_ms=round((time.perf_counter() - started) * 1000),
        )


def _render_text(
    status: str,
    units: tuple[RetrievalUnit, ...],
    reasons: tuple[str, ...],
) -> str:
    if status in {"pregunta", "abstención"}:
        return " ".join(reasons)
    paragraphs = []
    for unit in units:
        holding = unit.holding
        paragraphs.append(f"{unit.judgment_id}: {holding.conclusion} {holding.decisive_reasoning}")
    return "\n\n".join(paragraphs)
