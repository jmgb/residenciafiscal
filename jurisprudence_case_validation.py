"""Invariantes relacionales del agregado jurisprudencial v3."""

from __future__ import annotations

from typing import TYPE_CHECKING

from jurisprudence_case_reference_validation import validate_references

if TYPE_CHECKING:
    from jurisprudence_case_models import JurisprudenceCase


def _require_unique(collection_name: str, item_ids: tuple[str, ...]) -> None:
    duplicates = sorted({item_id for item_id in item_ids if item_ids.count(item_id) > 1})
    if duplicates:
        raise ValueError(f"{collection_name} contiene IDs duplicados: {duplicates}")


def validate_unique_ids(case: JurisprudenceCase) -> None:
    """Rechaza IDs duplicados dentro de cada espacio de nombres."""

    _require_unique("legal_issues", tuple(item.issue_id for item in case.legal_issues))
    _require_unique("facts", tuple(item.fact_id for item in case.facts))
    _require_unique(
        "evidence_findings",
        tuple(item.evidence_id for item in case.evidence_findings),
    )
    _require_unique("legal_rules", tuple(item.legal_rule_id for item in case.legal_rules))
    _require_unique("holdings", tuple(item.holding_id for item in case.holdings))
    _require_unique(
        "burden_of_proof_steps",
        tuple(item.step_id for item in case.burden_of_proof_steps),
    )
    _require_unique(
        "source_anchors",
        tuple(item.anchor_id for item in case.source_anchors),
    )
    _require_unique(
        "presence_events",
        tuple(item.event_id for item in case.presence_events),
    )
    _require_unique(
        "presence_periods",
        tuple(item.period_id for item in case.presence_periods),
    )
    _require_unique(
        "treaty_analyses",
        tuple(item.treaty_analysis_id for item in case.treaty_analyses),
    )


def validate_holding_ownership(case: JurisprudenceCase) -> None:
    """Exige una relación uno a uno entre cuestión y holding."""

    holdings_by_id = {holding.holding_id: holding for holding in case.holdings}
    referenced_holding_ids = {issue.holding_id for issue in case.legal_issues}
    orphan_holding_ids = set(holdings_by_id) - referenced_holding_ids
    if orphan_holding_ids:
        raise ValueError(f"holdings huérfanos: {sorted(orphan_holding_ids)}")
    for issue in case.legal_issues:
        holding = holdings_by_id[issue.holding_id]
        if holding.issue_id != issue.issue_id:
            raise ValueError(f"{holding.holding_id} no pertenece a la cuestión {issue.issue_id}")


def validate_reciprocal_issue_relations(case: JurisprudenceCase) -> None:
    """Evita que las facetas de una cuestión diverjan de sus elementos."""

    relations = (
        (
            "facts",
            {
                (issue.issue_id, item_id)
                for issue in case.legal_issues
                for item_id in issue.fact_ids
            },
            {(issue_id, item.fact_id) for item in case.facts for issue_id in item.issue_ids},
        ),
        (
            "evidence_findings",
            {
                (issue.issue_id, item_id)
                for issue in case.legal_issues
                for item_id in issue.evidence_ids
            },
            {
                (issue_id, item.evidence_id)
                for item in case.evidence_findings
                for issue_id in item.issue_ids
            },
        ),
        (
            "legal_rules",
            {
                (issue.issue_id, item_id)
                for issue in case.legal_issues
                for item_id in issue.legal_rule_ids
            },
            {
                (issue_id, item.legal_rule_id)
                for item in case.legal_rules
                for issue_id in item.issue_ids
            },
        ),
    )
    for collection_name, issue_side, item_side in relations:
        if issue_side != item_side:
            differences = sorted(issue_side ^ item_side)
            raise ValueError(
                f"{collection_name} contiene una relación con cuestión no recíproca: {differences}"
            )


def validate_anchor_source(case: JurisprudenceCase) -> None:
    """Liga cada anclaje al PDF y a una página física existente."""

    for anchor in case.source_anchors:
        if anchor.source_sha256 != case.judgment.source_sha256:
            raise ValueError(
                f"{anchor.anchor_id}.source_sha256 no coincide con judgment.source_sha256"
            )
        for fragment in anchor.fragments:
            if fragment.page_index > case.judgment.page_count:
                raise ValueError(f"{anchor.anchor_id}.page_index excede judgment.page_count")


def validate_burden_sequence(case: JurisprudenceCase) -> None:
    """Exige una secuencia procesal contigua desde uno."""

    sequences = sorted(step.sequence for step in case.burden_of_proof_steps)
    if sequences != list(range(1, len(sequences) + 1)):
        raise ValueError("burden_of_proof_steps debe tener una secuencia contigua desde 1")


def validate_jurisprudence_case(case: JurisprudenceCase) -> None:
    """Ejecuta todos los invariantes relacionales del agregado."""

    validate_unique_ids(case)
    validate_references(case)
    validate_holding_ownership(case)
    validate_reciprocal_issue_relations(case)
    validate_anchor_source(case)
    validate_burden_sequence(case)
