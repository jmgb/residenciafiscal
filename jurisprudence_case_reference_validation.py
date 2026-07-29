"""Validación de referencias internas del caso jurisprudencial v3."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jurisprudence_case_models import JurisprudenceCase


def _require_references(
    owner_id: str,
    field_name: str,
    referenced_ids: tuple[str, ...],
    available_ids: set[str],
) -> None:
    missing = set(referenced_ids) - available_ids
    if missing:
        raise ValueError(
            f"{owner_id}.{field_name} contiene referencias inexistentes: {sorted(missing)}"
        )


def validate_references(case: JurisprudenceCase) -> None:
    """Comprueba todas las relaciones internas del caso."""

    issue_ids = {issue.issue_id for issue in case.legal_issues}
    fact_ids = {fact.fact_id for fact in case.facts}
    evidence_ids = {evidence.evidence_id for evidence in case.evidence_findings}
    legal_rule_ids = {rule.legal_rule_id for rule in case.legal_rules}
    holding_ids = {holding.holding_id for holding in case.holdings}
    anchor_ids = {anchor.anchor_id for anchor in case.source_anchors}

    for issue in case.legal_issues:
        _require_references(issue.issue_id, "fact_ids", issue.fact_ids, fact_ids)
        _require_references(issue.issue_id, "evidence_ids", issue.evidence_ids, evidence_ids)
        _require_references(
            issue.issue_id,
            "legal_rule_ids",
            issue.legal_rule_ids,
            legal_rule_ids,
        )
        _require_references(issue.issue_id, "holding_id", (issue.holding_id,), holding_ids)
        _require_references(issue.issue_id, "anchor_ids", issue.anchor_ids, anchor_ids)

    for fact in case.facts:
        _require_references(fact.fact_id, "issue_ids", fact.issue_ids, issue_ids)
        _require_references(fact.fact_id, "anchor_ids", fact.anchor_ids, anchor_ids)

    for evidence in case.evidence_findings:
        _require_references(evidence.evidence_id, "fact_ids", evidence.fact_ids, fact_ids)
        _require_references(evidence.evidence_id, "issue_ids", evidence.issue_ids, issue_ids)
        _require_references(
            evidence.evidence_id,
            "anchor_ids",
            evidence.anchor_ids,
            anchor_ids,
        )

    for rule in case.legal_rules:
        _require_references(rule.legal_rule_id, "issue_ids", rule.issue_ids, issue_ids)
        _require_references(rule.legal_rule_id, "anchor_ids", rule.anchor_ids, anchor_ids)

    for holding in case.holdings:
        _require_references(holding.holding_id, "issue_id", (holding.issue_id,), issue_ids)
        _require_references(holding.holding_id, "anchor_ids", holding.anchor_ids, anchor_ids)

    for burden_step in case.burden_of_proof_steps:
        _require_references(
            burden_step.step_id,
            "issue_ids",
            burden_step.issue_ids,
            issue_ids,
        )
        _require_references(
            burden_step.step_id,
            "triggering_evidence_ids",
            burden_step.triggering_evidence_ids,
            evidence_ids,
        )
        _require_references(
            burden_step.step_id,
            "anchor_ids",
            burden_step.anchor_ids,
            anchor_ids,
        )

    for event in case.presence_events:
        _require_references(event.event_id, "fact_ids", event.fact_ids, fact_ids)
        _require_references(
            event.event_id,
            "evidence_ids",
            event.evidence_ids,
            evidence_ids,
        )
        _require_references(event.event_id, "issue_ids", event.issue_ids, issue_ids)
        _require_references(event.event_id, "anchor_ids", event.anchor_ids, anchor_ids)

    for period in case.presence_periods:
        _require_references(period.period_id, "fact_ids", period.fact_ids, fact_ids)
        _require_references(
            period.period_id,
            "evidence_ids",
            period.evidence_ids,
            evidence_ids,
        )
        _require_references(period.period_id, "issue_ids", period.issue_ids, issue_ids)
        _require_references(period.period_id, "anchor_ids", period.anchor_ids, anchor_ids)

    for treaty in case.treaty_analyses:
        _require_references(
            treaty.treaty_analysis_id,
            "domestic_law_issue_ids",
            treaty.domestic_law_issue_ids,
            issue_ids,
        )
        _require_references(
            treaty.treaty_analysis_id,
            "anchor_ids",
            treaty.anchor_ids,
            anchor_ids,
        )
        for treaty_step in treaty.steps:
            _require_references(
                treaty_step.step_id,
                "fact_ids",
                treaty_step.fact_ids,
                fact_ids,
            )
            _require_references(
                treaty_step.step_id,
                "evidence_ids",
                treaty_step.evidence_ids,
                evidence_ids,
            )
            _require_references(
                treaty_step.step_id,
                "anchor_ids",
                treaty_step.anchor_ids,
                anchor_ids,
            )
