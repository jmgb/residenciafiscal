"""Serialización acotada de unidades recuperadas y anclajes verificables."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass

from chat_strategy_models import StrategySource
from jurisprudence_case_catalogs import AnchorPurpose
from jurisprudence_case_retrieval_models import RetrievalUnit
from jurisprudence_case_source import SourceAnchor, SourceFragment
from jurisprudence_phase_d_retrieval import ChatRetrievalResult

EVIDENCE_PER_UNIT = 2
_PURPOSE_WEIGHT = {
    AnchorPurpose.HOLDING: 6,
    AnchorPurpose.REASONING: 5,
    AnchorPurpose.EVIDENCE: 4,
    AnchorPurpose.BURDEN_OF_PROOF: 4,
    AnchorPurpose.TREATY: 4,
    AnchorPurpose.LEGAL_RULE: 3,
    AnchorPurpose.FACT: 2,
}
_STOPWORDS = {
    "como",
    "cual",
    "cuando",
    "donde",
    "españa",
    "fiscal",
    "hacienda",
    "para",
    "porque",
    "que",
    "residencia",
    "tiene",
    "una",
}


@dataclass(frozen=True)
class StructuredEvidenceBundle:
    context_json: str
    sources_by_evidence_id: dict[str, StrategySource]


def _unit_payload(unit: RetrievalUnit, role: str) -> dict[str, object]:
    return {
        "unit_id": unit.unit_id,
        "judgment_id": unit.judgment_id,
        "role": role,
        "issue": {
            "question": unit.issue.question,
            "type": unit.issue.issue_type.value,
            "criteria": [item.value for item in unit.issue.criterion_ids],
        },
        "holding": {
            "outcome": unit.holding.outcome.value,
            "conclusion": unit.holding.conclusion,
            "decisive_reasoning": unit.holding.decisive_reasoning,
            "residence_determination": (
                unit.holding.residence_determination.model_dump(mode="json")
                if unit.holding.residence_determination
                else None
            ),
        },
        "facts": [
            {
                "category": item.category.value,
                "description": item.description,
                "country": item.country,
                "status": item.procedural_status.value,
            }
            for item in unit.facts
        ],
        "evidence_findings": [
            {
                "party": item.offered_by.value,
                "category": item.category.value,
                "description": item.description,
                "purpose": item.probative_purpose,
                "assessment": item.assessment.value,
                "assessment_reason": item.assessment_reason,
                "role": item.role.value,
                "foreign_document": (
                    item.foreign_document.model_dump(mode="json") if item.foreign_document else None
                ),
            }
            for item in unit.evidence_findings
        ],
        "legal_rules": [
            {
                "type": item.rule_type.value,
                "citation": item.citation,
                "proposition": item.proposition,
            }
            for item in unit.legal_rules
        ],
        "burden_of_proof": [
            {
                "fact_to_prove": item.fact_to_prove,
                "initial_bearer": item.initial_bearer.value,
                "shifts_to": item.shifts_to.value if item.shifts_to else None,
                "response_required": item.response_required,
                "conclusion": item.conclusion,
            }
            for item in unit.burden_of_proof_steps
        ],
        "presence_periods": [
            {
                "classification": item.classification.value,
                "country": item.country,
                "start_date": (item.start_date.isoformat() if item.start_date else None),
                "end_date": item.end_date.isoformat() if item.end_date else None,
                "day_count": item.day_count,
                "calculation_method": item.calculation_method,
            }
            for item in unit.presence_periods
        ],
        "treaty_analyses": [
            {
                "countries": list(item.countries),
                "citation": item.treaty_citation,
                "dual_residence_established": item.dual_residence_established,
                "result_country": item.result_country,
                "steps": [
                    {
                        "criterion": step.criterion.value,
                        "applied": step.applied,
                        "conclusion": step.conclusion,
                    }
                    for step in item.steps
                ],
            }
            for item in unit.treaty_analyses
        ],
    }


def _terms(text: str) -> set[str]:
    decomposed = unicodedata.normalize("NFD", text.casefold())
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return {token for token in re.findall(r"[a-z0-9]{3,}", plain) if token not in _STOPWORDS}


def _selected_fragments(
    unit: RetrievalUnit,
    query_terms: set[str],
) -> list[tuple[SourceAnchor, SourceFragment]]:
    candidates: list[tuple[int, int, SourceAnchor, SourceFragment]] = []
    order = 0
    for anchor in unit.source_anchors:
        for fragment in anchor.fragments:
            overlap = len(query_terms & _terms(fragment.verbatim_text))
            score = overlap * 10 + _PURPOSE_WEIGHT[anchor.purpose]
            candidates.append((-score, order, anchor, fragment))
            order += 1
    candidates.sort(key=lambda item: (item[0], item[1]))
    return [
        (anchor, fragment) for _score, _order, anchor, fragment in candidates[:EVIDENCE_PER_UNIT]
    ]


def build_structured_evidence_bundle(
    retrieval: ChatRetrievalResult,
    units_by_id: dict[str, RetrievalUnit],
    query: str,
) -> StructuredEvidenceBundle:
    units: list[dict[str, object]] = []
    evidence: list[dict[str, object]] = []
    sources: dict[str, StrategySource] = {}
    evidence_number = 1
    query_terms = _terms(query)

    for hit in retrieval.hits:
        unit = units_by_id[hit.unit_id]
        units.append(_unit_payload(unit, hit.role))
        for anchor, fragment in _selected_fragments(unit, query_terms):
            evidence_id = f"E{evidence_number}"
            evidence_number += 1
            evidence.append(
                {
                    "evidence_id": evidence_id,
                    "unit_id": unit.unit_id,
                    "judgment_id": unit.judgment_id,
                    "role": hit.role,
                    "anchor_id": anchor.anchor_id,
                    "purpose": anchor.purpose.value,
                    "page": fragment.page_index,
                    "printed_page": fragment.printed_page,
                    "quote": fragment.verbatim_text,
                }
            )
            sources[evidence_id] = StrategySource(
                strategy="current_structured",
                judgment_id=unit.judgment_id,
                page=fragment.page_index,
                source_sha256=anchor.source_sha256,
                quote=fragment.verbatim_text,
                verification="EXACT",
            )

    context = json.dumps(
        {"units": units, "evidence": evidence},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return StructuredEvidenceBundle(
        context_json=context,
        sources_by_evidence_id=sources,
    )
