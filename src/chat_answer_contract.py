"""Contrato semántico común de las dos respuestas experimentales."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator

from jurisprudence_case_catalogs import JurisprudenceCaseModel

DraftStatus = Literal["completa", "parcial", "pregunta", "abstención"]


class ChatAnswerDraft(JurisprudenceCaseModel):
    """Prosa y límites del modelo, separados de las fuentes verificadas."""

    status: DraftStatus
    answer: str
    limits: tuple[str, ...] = Field(default_factory=tuple)


class StructuredChatAnswerDraft(ChatAnswerDraft):
    """Extensión de A para resolver anclajes opacos del corpus local."""

    evidence_ids: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("evidence_ids")
    @classmethod
    def validate_evidence_ids(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        for value in values:
            if not value.startswith("E") or not value[1:].isdigit():
                raise ValueError("evidence_ids exige identificadores E<n>")
        return values
