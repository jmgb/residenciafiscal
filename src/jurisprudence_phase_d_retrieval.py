"""Recuperación estructurada y diversificada para el piloto de fase D."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from pydantic import Field

from jurisprudence_case_catalogs import (
    Identifier,
    IssueOutcome,
    JurisprudenceCaseModel,
)
from jurisprudence_case_retrieval_models import RetrievalUnit
from jurisprudence_case_source import SourceAnchor
from jurisprudence_query_analysis import QueryAnalysis, analyze_query
from jurisprudence_retrieval_corpus import rank_retrieval_units
from jurisprudence_retrieval_corpus_models import RetrievalCorpus
from jurisprudence_sample_evaluation_models import ResponseBehavior

HitRole = Literal["support", "contrast"]


class StructuredScore(JurisprudenceCaseModel):
    lexical: float = Field(ge=0)
    criterion_boost: float = Field(ge=0)
    evidence_boost: float = Field(ge=0)
    country_boost: float = Field(ge=0)
    period_boost: float = Field(ge=0)
    total: float = Field(ge=0)


class StructuredHit(JurisprudenceCaseModel):
    unit_id: Identifier
    judgment_id: Identifier
    role: HitRole
    score: StructuredScore
    source_anchors: tuple[SourceAnchor, ...] = Field(min_length=1)


class ChatRetrievalResult(JurisprudenceCaseModel):
    behavior: ResponseBehavior
    behavior_reasons: tuple[str, ...]
    missing_facts: tuple[str, ...]
    uncovered_facets: tuple[str, ...]
    hits: tuple[StructuredHit, ...]


def _score(
    unit: RetrievalUnit,
    lexical: float,
    analysis: QueryAnalysis,
) -> StructuredScore:
    criterion = 2.0 * len(set(unit.facets.criterion_ids) & set(analysis.criterion_ids))
    evidence = 1.25 * len(set(unit.facets.evidence_categories) & set(analysis.evidence_categories))
    country = 1.5 * len(set(unit.facets.countries) & set(analysis.countries))
    period = 1.0 * len(set(unit.facets.tax_years) & set(analysis.tax_years))
    if any(item.value == "CRIT_183_DIAS" for item in analysis.criterion_ids):
        period += 2.0 * len(unit.presence_events) + len(unit.presence_periods)
    return StructuredScore(
        lexical=lexical,
        criterion_boost=criterion,
        evidence_boost=evidence,
        country_boost=country,
        period_boost=period,
        total=round(lexical + criterion + evidence + country + period, 8),
    )


def _diversify(
    scored: Sequence[tuple[RetrievalUnit, StructuredScore]],
    limit: int,
) -> tuple[tuple[RetrievalUnit, StructuredScore], ...]:
    """Conserva la mejor unidad por sentencia e incluye conclusión contraria."""

    best_by_judgment: dict[str, tuple[RetrievalUnit, StructuredScore]] = {}
    for unit, score in scored:
        best_by_judgment.setdefault(unit.judgment_id, (unit, score))
    candidates = list(best_by_judgment.values())
    if not candidates:
        return ()
    selected = [candidates.pop(0)]
    first_side = retrieval_case_side(selected[0][0])
    contrasting = next(
        (item for item in candidates if retrieval_case_side(item[0]) != first_side),
        None,
    )
    if contrasting is not None and limit > 1:
        selected.append(contrasting)
        candidates.remove(contrasting)
    selected.extend(candidates[: max(0, limit - len(selected))])
    return tuple(selected[:limit])


def _outcome_side(outcome: IssueOutcome) -> str:
    if outcome == IssueOutcome.GANA_AEAT:
        return "aeat"
    if outcome == IssueOutcome.GANA_CONTRIBUYENTE:
        return "taxpayer"
    return "mixed"


def retrieval_case_side(unit: RetrievalUnit) -> str:
    """Distingue la conclusión residencial del mero vencedor procesal."""

    determination = unit.facets.residence_determination
    if determination is not None:
        if determination.spanish_residence.value == "RESIDENT_IN_SPAIN":
            return "resident_spain"
        if determination.spanish_residence.value in {
            "NON_RESIDENT_IN_SPAIN",
            "PARTIAL_YEAR_IN_SPAIN",
        }:
            return "resident_abroad"
        return "mixed"
    if unit.facets.issue_type.value == "TAX_RESIDENCE":
        return "mixed"
    return _outcome_side(unit.facets.outcome)


def retrieve_for_chat(
    corpus: RetrievalCorpus,
    query: str,
    *,
    limit: int = 5,
) -> ChatRetrievalResult:
    """Enruta la consulta y solo recupera fuentes cuando puede contestarse."""

    if limit < 1:
        raise ValueError("limit debe ser positivo")
    analysis = analyze_query(query, corpus)
    if analysis.behavior in {"preguntar", "abstenerse"}:
        return ChatRetrievalResult(
            behavior=analysis.behavior,
            behavior_reasons=analysis.behavior_reasons,
            missing_facts=analysis.missing_facts,
            uncovered_facets=analysis.uncovered_facets,
            hits=(),
        )

    lexical = {
        hit.unit_id: hit.score
        for hit in rank_retrieval_units(corpus, query, limit=len(corpus.units))
    }
    scored = tuple(
        sorted(
            ((unit, _score(unit, lexical[unit.unit_id], analysis)) for unit in corpus.units),
            key=lambda item: (
                -item[1].total,
                -len(item[0].evidence_findings),
                item[0].unit_id,
            ),
        )
    )
    selected = _diversify(scored, limit)
    first_side = retrieval_case_side(selected[0][0]) if selected else "mixed"
    hits = tuple(
        StructuredHit(
            unit_id=unit.unit_id,
            judgment_id=unit.judgment_id,
            role=(
                "contrast" if index > 0 and retrieval_case_side(unit) != first_side else "support"
            ),
            score=score,
            source_anchors=unit.source_anchors,
        )
        for index, (unit, score) in enumerate(selected)
    )
    return ChatRetrievalResult(
        behavior=analysis.behavior,
        behavior_reasons=analysis.behavior_reasons,
        missing_facts=analysis.missing_facts,
        uncovered_facets=analysis.uncovered_facets,
        hits=hits,
    )
