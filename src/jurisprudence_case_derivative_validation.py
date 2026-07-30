"""Gate común del perfil OKF y el índice de recuperación B4."""

from __future__ import annotations

from dataclasses import dataclass

import yaml

from jurisprudence_case_models import JurisprudenceCase
from jurisprudence_case_retrieval_models import RetrievalIndex
from verbatim_hashing import sha256_utf8


@dataclass(frozen=True)
class DerivativeValidationResult:
    judgment_id: str
    legal_issue_count: int
    retrieval_unit_count: int
    literal_anchor_count: int
    literal_fragment_count: int
    markdown_sha256: str
    retrieval_sha256: str


def validate_case_derivatives(
    case: JurisprudenceCase,
    *,
    case_sha256: str,
    markdown: str,
    retrieval: RetrievalIndex,
    serialized_retrieval: str,
) -> DerivativeValidationResult:
    """Comprueba correspondencia uno a uno y presencia literal en la vista."""

    frontmatter_parts = markdown.split("---", 2)
    if len(frontmatter_parts) != 3:
        raise ValueError("el perfil no contiene frontmatter YAML")
    frontmatter = yaml.safe_load(frontmatter_parts[1])
    expected_frontmatter = {
        "schema_version": "residenciafiscal-okf/3",
        "case_schema_version": case.schema_version,
        "case_sha256": case_sha256,
        "source_sha256": case.judgment.source_sha256,
    }
    for field_name, expected in expected_frontmatter.items():
        if frontmatter.get(field_name) != expected:
            raise ValueError(f"frontmatter.{field_name} no coincide")

    expected_issue_ids = tuple(item.issue_id for item in case.legal_issues)
    unit_issue_ids = tuple(item.issue.issue_id for item in retrieval.units)
    if unit_issue_ids != expected_issue_ids:
        raise ValueError("las unidades no corresponden uno a uno con las cuestiones")
    if retrieval.source.case_sha256 != case_sha256:
        raise ValueError("retrieval.source.case_sha256 no coincide")

    expected_anchor_ids = {item.anchor_id for item in case.source_anchors}
    retrieval_anchor_ids = {
        anchor.anchor_id for unit in retrieval.units for anchor in unit.source_anchors
    }
    if retrieval_anchor_ids != expected_anchor_ids:
        raise ValueError("el índice no cubre todos los anclajes del caso")
    fragment_count = 0
    for anchor in case.source_anchors:
        if f"`{anchor.anchor_id}`" not in markdown:
            raise ValueError(f"el perfil omite el anclaje {anchor.anchor_id}")
        for fragment in anchor.fragments:
            fragment_count += 1
            if fragment.verbatim_text not in markdown:
                raise ValueError(f"el perfil altera el fragmento de {anchor.anchor_id}")

    return DerivativeValidationResult(
        judgment_id=case.judgment.judgment_id,
        legal_issue_count=len(case.legal_issues),
        retrieval_unit_count=len(retrieval.units),
        literal_anchor_count=len(case.source_anchors),
        literal_fragment_count=fragment_count,
        markdown_sha256=sha256_utf8(markdown),
        retrieval_sha256=sha256_utf8(serialized_retrieval),
    )
