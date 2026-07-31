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
    tiene, por dos razones que apuntan al mismo sitio.

    La primera es de contrato. Un `limits` ausente se convertía en tupla vacía,
    y eso hace indistinguible «el modelo no encontró salvedades» de «el modelo
    no se pronunció». Es el mismo error que el proyecto persigue en el coste
    —ausencia contada como cero— aplicado a las salvedades de una respuesta
    jurídica, donde importa más: una respuesta sin límites declarados se lee
    como una respuesta sin reservas.

    La segunda es de proveedor. El modo estricto de la Responses API exige que
    `required` contenga **todas** las propiedades, así que un campo con valor
    por defecto hace que OpenAI rechace el esquema entero con
    `invalid_json_schema`. Gemini lo aceptaba, de modo que el contrato solo era
    portable por accidente. `tests/test_chat_answer_strict_schema.py` lo
    comprueba sin red y sin coste.

    El prompt de A pide explícitamente ambos campos: exigirlos en el esquema
    sin pedirlos en las instrucciones sería trasladar al modelo un requisito
    que nadie le comunicó.

    La clase base no cambia. La estrategia B la usa contra File Search, que no
    impone modo estricto y queda fuera del paquete por diseño; endurecerla
    convertiría en fallo lo que hoy es una respuesta válida, en un camino que
    alimenta artefactos de revisión ya generados.
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
