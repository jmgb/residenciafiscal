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
    """Extensión de A para resolver anclajes opacos del corpus local.

    `limits` se redeclara sin valor por defecto, y `evidence_ids` tampoco lo
    tiene. La razón es jurídica, no técnica: un `limits` ausente se convertía en
    tupla vacía, y eso hace indistinguible «el modelo no encontró salvedades» de
    «el modelo no se pronunció». Es el mismo error que el proyecto persigue en
    el coste —ausencia contada como cero— aplicado a las salvedades de una
    respuesta jurídica, donde pesa más: una respuesta sin límites declarados se
    lee como una respuesta sin reservas.

    Hubo además un motivo de compatibilidad, y ya no aplica: el modo estricto de
    la Responses API exige `required` completo, y un campo con valor por defecto
    hacía que OpenAI rechazase el esquema entero. Desde la v0.7.0 el paquete
    normaliza el esquema antes de enviarlo, así que esa parte es historia. Lo
    que queda es la garantía de dominio, que ningún proveedor da por nosotros.

    El prompt de A pide explícitamente ambos campos: exigirlos en el esquema
    sin pedirlos en las instrucciones sería trasladar al modelo un requisito
    que nadie le comunicó.

    La clase base no cambia. La estrategia B la usa contra File Search, que
    queda fuera del paquete por diseño; endurecerla convertiría en fallo lo que
    hoy es una respuesta válida, en un camino que alimenta artefactos de
    revisión ya generados.
    """

    limits: tuple[str, ...]
    evidence_ids: tuple[str, ...]

    @field_validator("evidence_ids")
    @classmethod
    def validate_evidence_ids(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        for value in values:
            if not value.startswith("E") or not value[1:].isdigit():
                raise ValueError("evidence_ids exige identificadores E<n>")
        return values
