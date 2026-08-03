"""Contratos C0 para investigación profunda sin cadena de pensamiento."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from jurisprudence_case_catalogs import (
    Identifier,
    JurisprudenceCaseModel,
    NonEmptyText,
    Sha256,
)

DeepResearchStage = Literal[
    "searching",
    "reading",
    "verifying",
    "completed",
    "cancelled",
    "error",
]
DeepResearchAnswerStatus = Literal["completa", "parcial", "pregunta", "abstención", "error"]
CostMeasurement = Literal["ACTUAL", "ESTIMATED", "UNAVAILABLE"]


class DeepResearchLimits(JurisprudenceCaseModel):
    """Presupuesto máximo de una ejecución C, antes de iniciar el agente."""

    timeout_ms: Annotated[int, Field(ge=1_000, le=900_000)] = 180_000
    max_turns: Annotated[int, Field(ge=1, le=32)] = 12
    max_tool_calls: Annotated[int, Field(ge=1, le=200)] = 80
    max_documents: Annotated[int, Field(ge=1, le=106)] = 12
    max_pages: Annotated[int, Field(ge=1, le=1_200)] = 120
    max_cost_microusd: Annotated[int, Field(ge=1, le=2_000_000)] = 200_000


class DeepResearchJob(JurisprudenceCaseModel):
    """Trabajo asíncrono autenticado que apunta a un bundle inmutable."""

    schema_version: Literal["residenciafiscal-deep-research-job/1"]
    job_id: Identifier
    request_id: NonEmptyText
    bundle_id: NonEmptyText
    question: Annotated[str, Field(min_length=1, max_length=2_000)]
    limits: DeepResearchLimits = Field(default_factory=DeepResearchLimits)


class DeepResearchProgress(JurisprudenceCaseModel):
    """Estado seguro para UX; no contiene razonamiento interno del agente."""

    schema_version: Literal["residenciafiscal-deep-research-progress/1"]
    job_id: Identifier
    stage: DeepResearchStage
    tool_calls: Annotated[int, Field(ge=0)] = 0
    documents_read: Annotated[int, Field(ge=0)] = 0
    pages_read: Annotated[int, Field(ge=0)] = 0


class DeepResearchEvidence(JurisprudenceCaseModel):
    """Cita que debe haber pasado el verificador determinista."""

    judgment_id: Identifier
    page: Annotated[int, Field(gt=0)]
    source_sha256: Sha256
    quote: NonEmptyText
    verification: Literal["EXACT"]


class DeepResearchClaim(JurisprudenceCaseModel):
    """Afirmación con referencias 1-based a la lista de evidencias."""

    text: NonEmptyText
    evidence_indexes: Annotated[tuple[int, ...], Field(min_length=1)]


class DeepResearchOutput(JurisprudenceCaseModel):
    """Salida estructurada de C; deliberadamente no tiene campo de razonamiento."""

    schema_version: Literal["residenciafiscal-deep-research-output/1"]
    job_id: Identifier
    request_id: NonEmptyText
    status: DeepResearchAnswerStatus
    text: str
    limits: tuple[str, ...]
    claims: tuple[DeepResearchClaim, ...]
    evidence: tuple[DeepResearchEvidence, ...]
    cost_microusd: Annotated[int, Field(ge=0)] | None = None
    cost_measurement: CostMeasurement = "UNAVAILABLE"
    model: NonEmptyText = "unavailable"
    latency_ms: Annotated[int, Field(ge=0)] = 0

    @model_validator(mode="after")
    def validate_claim_references(self) -> DeepResearchOutput:
        evidence_count = len(self.evidence)
        if any(
            index < 1 or index > evidence_count
            for claim in self.claims
            for index in claim.evidence_indexes
        ):
            raise ValueError("claims contiene referencias fuera de la lista evidence")
        return self


class DeepResearchBundleManifest(JurisprudenceCaseModel):
    """Manifiesto reproducible de los archivos que puede leer el worker."""

    schema_version: Literal["residenciafiscal-deep-research-bundle/1"]
    bundle_id: NonEmptyText
    source_manifest_path: NonEmptyText
    source_manifest_sha256: Sha256
    files: dict[NonEmptyText, Sha256]
    scope: dict[NonEmptyText, Annotated[int, Field(ge=0)]]
