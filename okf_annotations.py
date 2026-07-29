"""Sidecars de revisión que nunca modifican el texto de la sentencia."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from citation_models import ExtractedPage
from config import VALID_CRITERIOS, VALID_RESULTADO_FINAL
from okf_models import OkfEvidence, OkfJudgment

AnnotationStatus = Literal["proposed", "approved"]
_ALLOWED_CORRECTIONS = {"criterio_atacado", "resultado_final"}
_LEGAL_TEXT_FIELDS = {
    "analysis_quote",
    "source_excerpt_verbatim",
    "texto",
    "pdf",
    "resumen_criterios",
    "razonamiento_residencia",
}


class AnnotationCorrection(BaseModel):
    """Corrección auditable limitada a metadatos derivados."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    target_id: str
    field: str
    source_value: str
    replacement: str
    rationale: str
    status: AnnotationStatus
    reviewed_by: str | None = None
    reviewed_at: str | None = None

    @model_validator(mode="after")
    def validate_correction(self) -> Self:
        if self.field in _LEGAL_TEXT_FIELDS or self.field not in _ALLOWED_CORRECTIONS:
            raise ValueError(
                f"No se puede corregir el campo {self.field}: el texto legal es inmutable"
            )
        catalog = VALID_CRITERIOS if self.field == "criterio_atacado" else VALID_RESULTADO_FINAL
        if self.replacement not in catalog:
            raise ValueError(f"{self.field}: reemplazo no canónico {self.replacement}")
        if self.status == "approved" and (not self.reviewed_by or not self.reviewed_at):
            raise ValueError("Una corrección aprobada exige reviewed_by y reviewed_at")
        return self


class SourceAnchor(BaseModel):
    """Fragmento jurídico copiado literalmente de una página física del PDF."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    pdf_page_index: int = Field(gt=0)
    source_excerpt_verbatim: str = Field(min_length=1)


class LegalIssue(BaseModel):
    """Resultado separado por cuestión jurídica, con apoyo trazable."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    question: str
    decision: str
    status: AnnotationStatus
    support_citation_ids: tuple[str, ...] = ()
    source_anchors: tuple[SourceAnchor, ...] = ()
    rationale: str
    reviewed_by: str | None = None
    reviewed_at: str | None = None

    @model_validator(mode="after")
    def validate_issue(self) -> Self:
        if self.decision not in VALID_RESULTADO_FINAL:
            raise ValueError(f"resultado no canónico: {self.decision}")
        if self.status == "approved" and (not self.reviewed_by or not self.reviewed_at):
            raise ValueError("Una cuestión aprobada exige reviewed_by y reviewed_at")
        return self


class JudgmentAnnotations(BaseModel):
    """Contrato versionado del sidecar asociado a una sentencia."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    source_file: str
    corrections: tuple[AnnotationCorrection, ...] = ()
    issues: tuple[LegalIssue, ...] = ()

    @model_validator(mode="after")
    def validate_ids(self) -> Self:
        issue_ids = tuple(issue.id for issue in self.issues)
        if len(issue_ids) != len(set(issue_ids)):
            raise ValueError("Las cuestiones contienen IDs duplicados")
        return self


def load_annotations(path: Path, source_file: str) -> JudgmentAnnotations:
    """Carga el sidecar si existe y comprueba que pertenece al PDF esperado."""

    if not path.is_file():
        return JudgmentAnnotations(schema_version=1, source_file=source_file)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    annotations = JudgmentAnnotations.model_validate(raw)
    if annotations.source_file != source_file:
        raise ValueError(f"Sidecar de {annotations.source_file}, pero se esperaba {source_file}")
    return annotations


def validate_annotation_references(
    judgment: OkfJudgment,
    annotations: JudgmentAnnotations,
) -> None:
    """Impide que un sidecar apunte a IDs ausentes del perfil normalizado."""

    citation_ids = {citation.id for citation in judgment.citas}
    evidence_ids = {
        evidence.id for evidence in (*judgment.pruebas_aeat, *judgment.pruebas_contribuyente)
    }
    for issue in annotations.issues:
        unknown = set(issue.support_citation_ids) - citation_ids
        if unknown:
            raise ValueError(f"Cuestión {issue.id}: citas inexistentes {sorted(unknown)}")
    for correction in annotations.corrections:
        valid_target = correction.target_id == "sentencia" or correction.target_id in evidence_ids
        if not valid_target:
            raise ValueError(f"Corrección: target_id inexistente {correction.target_id}")


def validate_source_anchors(
    annotations: JudgmentAnnotations,
    pages: tuple[str | ExtractedPage, ...],
) -> None:
    """Exige que cada anclaje sea una subcadena byte-for-byte del texto extraído."""

    for issue in annotations.issues:
        for anchor in issue.source_anchors:
            if anchor.pdf_page_index > len(pages):
                raise ValueError(f"Cuestión {issue.id}: página {anchor.pdf_page_index} inexistente")
            page = pages[anchor.pdf_page_index - 1]
            page_text = page.text if isinstance(page, ExtractedPage) else page
            if anchor.source_excerpt_verbatim not in page_text:
                raise ValueError(
                    f"Cuestión {issue.id}: el anclaje de página "
                    f"{anchor.pdf_page_index} no es literal"
                )


def _correct_evidence(
    evidence: OkfEvidence,
    corrections: tuple[AnnotationCorrection, ...],
) -> OkfEvidence:
    corrected = evidence
    for correction in corrections:
        if correction.target_id != evidence.id or correction.field != "criterio_atacado":
            continue
        if corrected.criterio_atacado != correction.source_value:
            raise ValueError(f"{evidence.id}: source_value no coincide")
        if correction.replacement not in VALID_CRITERIOS:
            raise ValueError(f"criterio no canónico: {correction.replacement}")
        corrected = corrected.model_copy(update={"criterio_atacado": correction.replacement})
    return corrected


def apply_approved_corrections(
    judgment: OkfJudgment,
    annotations: JudgmentAnnotations,
) -> OkfJudgment:
    """Aplica solo metadatos aprobados y conserva siempre los valores fuente."""

    approved = tuple(
        correction for correction in annotations.corrections if correction.status == "approved"
    )
    result = judgment
    for correction in approved:
        if correction.field != "resultado_final":
            continue
        if correction.target_id != "sentencia" or result.resultado_final != correction.source_value:
            raise ValueError("resultado_final: target_id o source_value no coincide")
        result = result.model_copy(update={"resultado_final": correction.replacement})
    return result.model_copy(
        update={
            "pruebas_aeat": tuple(
                _correct_evidence(evidence, approved) for evidence in result.pruebas_aeat
            ),
            "pruebas_contribuyente": tuple(
                _correct_evidence(evidence, approved) for evidence in result.pruebas_contribuyente
            ),
        }
    )
