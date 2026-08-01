"""Construcción y serialización de unidades recuperables por cuestión."""

from __future__ import annotations

import json

from jurisprudence_case_models import JurisprudenceCase
from jurisprudence_case_retrieval_models import (
    RetrievalFacets,
    RetrievalIndex,
    RetrievalJudgment,
    RetrievalSource,
    RetrievalUnit,
)


def _anchor_ids_for_unit(unit_parts: tuple[object, ...]) -> set[str]:
    anchor_ids: set[str] = set()
    for item in unit_parts:
        anchor_ids.update(getattr(item, "anchor_ids", ()))
        for step in getattr(item, "steps", ()):
            anchor_ids.update(step.anchor_ids)
    return anchor_ids


def _search_text(unit: RetrievalUnit) -> str:
    lines = [
        unit.issue.question,
        unit.issue.issue_type,
        *unit.issue.criterion_ids,
        *(item.description for item in unit.facts),
    ]
    for evidence in unit.evidence_findings:
        lines.extend(
            (
                evidence.subtype,
                evidence.description,
                evidence.probative_purpose,
                evidence.assessment,
                evidence.assessment_reason or "",
            )
        )
    for rule in unit.legal_rules:
        lines.extend((rule.citation, rule.proposition))
    lines.extend(
        (
            unit.holding.conclusion,
            unit.holding.decisive_reasoning,
            *unit.holding.consequences,
        )
    )
    if unit.holding.residence_determination is not None:
        determination = unit.holding.residence_determination
        lines.extend(
            (
                determination.spanish_residence,
                determination.other_country or "",
                *(str(year) for year in determination.tax_years),
            )
        )
    for step in unit.burden_of_proof_steps:
        lines.extend((step.fact_to_prove, step.conclusion))
    for anchor in unit.source_anchors:
        lines.extend(fragment.verbatim_text for fragment in anchor.fragments)
    return "\n".join(str(line) for line in lines if str(line).strip())


def _build_unit(case: JurisprudenceCase, issue_index: int) -> RetrievalUnit:
    issue = case.legal_issues[issue_index]
    facts_by_id = {item.fact_id: item for item in case.facts}
    evidence_by_id = {item.evidence_id: item for item in case.evidence_findings}
    rules_by_id = {item.legal_rule_id: item for item in case.legal_rules}
    holdings_by_id = {item.holding_id: item for item in case.holdings}
    facts = tuple(facts_by_id[item_id] for item_id in issue.fact_ids)
    evidence = tuple(evidence_by_id[item_id] for item_id in issue.evidence_ids)
    rules = tuple(rules_by_id[item_id] for item_id in issue.legal_rule_ids)
    holding = holdings_by_id[issue.holding_id]
    burden = tuple(item for item in case.burden_of_proof_steps if issue.issue_id in item.issue_ids)
    events = tuple(item for item in case.presence_events if issue.issue_id in item.issue_ids)
    periods = tuple(item for item in case.presence_periods if issue.issue_id in item.issue_ids)
    treaties = tuple(
        item for item in case.treaty_analyses if issue.issue_id in item.domestic_law_issue_ids
    )
    parts = (issue, holding, *facts, *evidence, *rules, *burden, *events, *periods, *treaties)
    anchor_ids = _anchor_ids_for_unit(parts)
    anchors = tuple(anchor for anchor in case.source_anchors if anchor.anchor_id in anchor_ids)
    facets = RetrievalFacets(
        issue_type=issue.issue_type,
        criterion_ids=issue.criterion_ids,
        countries=case.judgment.countries,
        tax_years=case.judgment.tax_years,
        evidence_categories=tuple(dict.fromkeys(item.category for item in evidence)),
        evidence_parties=tuple(dict.fromkeys(item.offered_by for item in evidence)),
        outcome=holding.outcome,
        residence_determination=holding.residence_determination,
        has_treaty=bool(treaties),
        technical_review=issue.review.technical,
        legal_review=issue.review.legal,
    )
    unit = RetrievalUnit(
        unit_id=f"{case.judgment.judgment_id}-{issue.issue_id}",
        judgment_id=case.judgment.judgment_id,
        issue=issue,
        holding=holding,
        facts=facts,
        evidence_findings=evidence,
        legal_rules=rules,
        burden_of_proof_steps=burden,
        presence_events=events,
        presence_periods=periods,
        treaty_analyses=treaties,
        source_anchors=anchors,
        facets=facets,
        search_text="pending",
    )
    return unit.model_copy(update={"search_text": _search_text(unit)})


def build_retrieval_index(
    case: JurisprudenceCase,
    *,
    case_resource: str,
    case_sha256: str,
) -> RetrievalIndex:
    """Proyecta el agregado en una unidad autocontenida por cuestión."""

    judgment = case.judgment
    return RetrievalIndex(
        schema_version="residenciafiscal-retrieval/1",
        source=RetrievalSource(
            case_resource=case_resource,
            case_sha256=case_sha256,
            source_sha256=judgment.source_sha256,
        ),
        judgment=RetrievalJudgment(
            judgment_id=judgment.judgment_id,
            roj=judgment.roj,
            ecli=judgment.ecli,
            court=judgment.court,
            chamber=judgment.chamber,
            decision_date=judgment.decision_date,
            tax_years=judgment.tax_years,
            countries=judgment.countries,
            is_tax_residence_case=judgment.is_tax_residence_case,
        ),
        units=tuple(_build_unit(case, index) for index in range(len(case.legal_issues))),
    )


def render_retrieval_index(index: RetrievalIndex) -> str:
    """Serializa el índice de forma determinista."""

    return (
        json.dumps(
            index.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def load_retrieval_index(serialized: str | bytes) -> RetrievalIndex:
    """Valida un índice desde JSON."""

    return RetrievalIndex.model_validate_json(serialized)
