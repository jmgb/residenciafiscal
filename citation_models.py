"""Contratos de datos del verificador de citas."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class EvidenceStatus(StrEnum):
    """Dónde se ha localizado la evidencia, sin afirmar fidelidad literal."""

    FOUND_DECLARED_PAGE = "found_declared_page"
    FOUND_ADJACENT_PAGE = "found_adjacent_page"
    FOUND_OTHER_PAGE = "found_other_page"
    PARTIAL_FRAGMENTS = "partial_fragments"
    NOT_FOUND = "not_found"
    EXTRACTION_DEFECT = "extraction_defect"


class LiteralFidelity(StrEnum):
    """Grado de identidad entre la cita generada y el texto del PDF."""

    EXACT = "exact"
    EXACT_WITH_ELLIPSIS = "exact_with_ellipsis"
    FUZZY_CANDIDATE = "fuzzy_candidate"
    PARTIAL = "partial"
    UNVERIFIED = "unverified"


@dataclass(frozen=True)
class ExtractedPage:
    """Texto de una página con sus dos sistemas de numeración."""

    pdf_page_index: int
    printed_page_label: str | None
    text: str


@dataclass(frozen=True)
class FragmentMatch:
    """Mejor coincidencia encontrada para un fragmento de la cita."""

    fragment: str
    score: float
    pdf_page_index: int | None
    printed_page_label: str | None
    exact: bool
    matched: bool


@dataclass(frozen=True)
class CitationVerification:
    """Resultado completo y serializable de verificar una cita."""

    evidence_status: EvidenceStatus
    literal_fidelity: LiteralFidelity
    score: float
    declared_pdf_page_index: int | None
    declared_page_valid: bool
    matched_pdf_page_indexes: tuple[int, ...]
    matched_printed_page_labels: tuple[str, ...]
    matched_fragment_count: int
    total_fragment_count: int
    fragment_matches: tuple[FragmentMatch, ...]

    @property
    def evidence_found(self) -> bool:
        """Indica si se localizaron todos los fragmentos por encima del umbral."""

        return self.evidence_status in {
            EvidenceStatus.FOUND_DECLARED_PAGE,
            EvidenceStatus.FOUND_ADJACENT_PAGE,
            EvidenceStatus.FOUND_OTHER_PAGE,
        }
