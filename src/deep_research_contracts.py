"""Contratos C0 para investigación profunda sin cadena de pensamiento."""

from __future__ import annotations

from typing import Annotated, Literal, Self

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
PilotResponseBehavior = Literal["responder", "parcial", "preguntar", "abstenerse"]


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

    schema_version: Literal[
        "residenciafiscal-deep-research-output/1",
        "residenciafiscal-deep-research-output/2",
    ]
    job_id: Identifier
    request_id: NonEmptyText
    status: DeepResearchAnswerStatus
    text: str
    limits: tuple[str, ...]
    claims: tuple[DeepResearchClaim, ...]
    evidence: tuple[DeepResearchEvidence, ...]
    cost_microusd: Annotated[int, Field(ge=0)] | None = None
    cost_measurement: CostMeasurement = "UNAVAILABLE"
    pricing_version: NonEmptyText | None = None
    model: NonEmptyText = "unavailable"
    reasoning_effort: Literal["high"] | None = None
    latency_ms: Annotated[int, Field(ge=0)] = 0

    @model_validator(mode="after")
    def validate_claim_references(self) -> DeepResearchOutput:
        if self.schema_version.endswith("/2") and self.reasoning_effort != "high":
            raise ValueError("la salida v2 exige reasoning_effort high")
        if self.schema_version.endswith("/2") and self.pricing_version is None:
            raise ValueError("la salida v2 exige pricing_version")
        evidence_count = len(self.evidence)
        if any(
            index < 1 or index > evidence_count
            for claim in self.claims
            for index in claim.evidence_indexes
        ):
            raise ValueError("claims contiene referencias fuera de la lista evidence")
        if self.status in {"completa", "parcial"} and (not self.claims or not self.evidence):
            raise ValueError("una respuesta sustantiva exige claims y evidence")
        referenced_indexes = {index for claim in self.claims for index in claim.evidence_indexes}
        if referenced_indexes != set(range(1, evidence_count + 1)):
            raise ValueError("toda evidence debe estar referenciada por un claim")
        if self.cost_measurement == "UNAVAILABLE" and self.cost_microusd is not None:
            raise ValueError("un coste no disponible no puede tener importe")
        if self.cost_measurement != "UNAVAILABLE" and self.cost_microusd is None:
            raise ValueError("un coste medido exige importe")
        return self


class DeepResearchBundleManifest(JurisprudenceCaseModel):
    """Manifiesto reproducible de los archivos que puede leer el worker."""

    schema_version: Literal["residenciafiscal-deep-research-bundle/2"]
    bundle_id: NonEmptyText
    source_manifest_path: NonEmptyText
    source_manifest_sha256: Sha256
    files: dict[NonEmptyText, Sha256]
    scope: dict[NonEmptyText, Annotated[int, Field(ge=0)] | NonEmptyText]


class DeepResearchPilotQuestion(JurisprudenceCaseModel):
    """Pregunta de evaluación que nunca se envía con su anotación al agente."""

    question_id: NonEmptyText
    dimension: NonEmptyText
    expected_behavior: PilotResponseBehavior
    question: NonEmptyText


class DeepResearchPilotSpec(JurisprudenceCaseModel):
    """Lock de preguntas C2 y de los recursos que las separan del holdout."""

    schema_version: Literal["residenciafiscal-deep-research-pilot/1"]
    pilot_id: Identifier
    source_resource: NonEmptyText
    source_sha256: Sha256
    holdout_resource: NonEmptyText
    holdout_sha256: Sha256
    question_ids: Annotated[tuple[NonEmptyText, ...], Field(min_length=1, max_length=20)]

    @model_validator(mode="after")
    def validate_question_ids(self) -> Self:
        if len(self.question_ids) != len(set(self.question_ids)):
            raise ValueError("question_ids contiene duplicados")
        return self


class DeepResearchPilotPlan(JurisprudenceCaseModel):
    """Plan materializado antes de permitir cualquier llamada a Codex."""

    schema_version: Literal["residenciafiscal-deep-research-plan/1"]
    pilot_id: Identifier
    source_resource: NonEmptyText
    source_sha256: Sha256
    holdout_resource: NonEmptyText
    holdout_sha256: Sha256
    bundle_id: NonEmptyText
    bundle_sha256: Sha256
    questions: Annotated[tuple[DeepResearchPilotQuestion, ...], Field(min_length=1, max_length=20)]
    jobs: Annotated[tuple[DeepResearchJob, ...], Field(min_length=1, max_length=20)]

    @model_validator(mode="after")
    def validate_jobs(self) -> Self:
        if len(self.questions) != len(self.jobs):
            raise ValueError("questions y jobs deben tener la misma longitud")
        if tuple(question.question for question in self.questions) != tuple(
            job.question for job in self.jobs
        ):
            raise ValueError("jobs no conserva el orden ni el texto de questions")
        return self
