"""Intención de órgano judicial en la pregunta y su comprobación en las citas.

Port literal del contrato vigente del runtime V1. Una pregunta que nombra un
tribunal concreto no puede responderse con doctrina de otro: la coincidencia se
declara sobre el `judgment_id` de las citas verificadas, no sobre lo que el
modelo afirme haber usado.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Literal

JudicialAuthorityIntent = Literal["tribunal_supremo", "audiencia_nacional"]
JudicialAuthorityMatch = Literal["direct", "missing", "not_requested"]

_SUPREME = re.compile(r"\b(tribunal supremo|supremo|sts)\b")
_NATIONAL_COURT = re.compile(r"\b(audiencia nacional|san)\b")
_JUDGMENT_IDENTIFIER = re.compile(r"\b(san|sts)\s*[- ]?\s*(\d+)\s*[/_-]\s*(\d{4})\b", re.I)


def extract_judgment_identifiers(text: str) -> tuple[str, ...]:
    """Normaliza referencias como ``SAN 2132/2025`` al identificador interno.

    Vive aquí, junto a la intención de órgano, porque es la otra lectura de la
    pregunta que decide qué se recupera. No transporta corpus ni candidatos, así
    que no cruza la frontera entre estrategias.
    """
    return tuple(
        dict.fromkeys(
            f"{court.lower()}-{number}-{year}"
            for court, number, year in _JUDGMENT_IDENTIFIER.findall(text)
        )
    )


def _fold(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def requested_judicial_authority(query: str) -> JudicialAuthorityIntent | None:
    """Devuelve el órgano pedido solo si la pregunta nombra uno y no los dos."""
    text = _fold(query)
    supreme = bool(_SUPREME.search(text))
    national_court = bool(_NATIONAL_COURT.search(text))
    if supreme == national_court:
        return None
    return "tribunal_supremo" if supreme else "audiencia_nacional"


def judgment_authority(judgment_id: str) -> JudicialAuthorityIntent | Literal["other"]:
    normalized = judgment_id.lower()
    if normalized.startswith("sts-"):
        return "tribunal_supremo"
    if normalized.startswith("san-"):
        return "audiencia_nacional"
    return "other"


def authority_metadata_filter(intent: JudicialAuthorityIntent | None) -> str | None:
    return f'authority="{intent}"' if intent else None


def local_authority_filter(intent: JudicialAuthorityIntent | None) -> str | None:
    return f'local_authority="{intent}"' if intent else None


def authority_match(
    intent: JudicialAuthorityIntent | None, judgment_ids: tuple[str, ...]
) -> JudicialAuthorityMatch:
    if intent is None:
        return "not_requested"
    return "direct" if any(judgment_authority(id_) == intent for id_ in judgment_ids) else "missing"


def authority_label(intent: JudicialAuthorityIntent) -> str:
    return "Tribunal Supremo" if intent == "tribunal_supremo" else "Audiencia Nacional"
