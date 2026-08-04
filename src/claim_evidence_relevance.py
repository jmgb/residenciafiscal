"""Gate léxico entre una afirmación y los extractos literales que la respaldan.

No mide verdad jurídica: descarta la afirmación que no comparte vocabulario
suficiente con sus propios extractos. Es el mismo umbral del runtime V1, y su
propósito es impedir que una claim se publique enlazada a una cita que no habla
de lo que la claim afirma.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence

from chat_strategy_models import StrategySource

_IGNORED = frozenset(
    {
        "administracion",
        "audiencia",
        "espana",
        "fiscal",
        "hecho",
        "judicial",
        "nacional",
        "resultado",
        "sala",
        "sentencia",
        "supremo",
        "tribunal",
        "valoracion",
    }
)
_TERM = re.compile(r"[a-z0-9]{4,}")


def _terms(value: str) -> set[str]:
    decomposed = unicodedata.normalize("NFKD", value.lower())
    folded = "".join(char for char in decomposed if not unicodedata.combining(char))
    return {term for term in _TERM.findall(folded) if term not in _IGNORED}


def claim_has_lexical_evidence(claim: str, sources: Sequence[StrategySource]) -> bool:
    claim_terms = _terms(claim)
    if len(claim_terms) < 2:
        return False
    evidence_terms = _terms(" ".join(source.quote for source in sources))
    overlap = len(claim_terms & evidence_terms)
    return overlap >= 2 and overlap / len(claim_terms) >= 0.2
