"""Comprobaciones de compatibilidad entre los contratos v2 y v3."""

from __future__ import annotations

from config import (
    VALID_CATEGORIAS_PRUEBA,
    VALID_CRITERIOS,
    VALID_TIEBREAKER_PASOS,
)


def validate_legacy_catalog_compatibility() -> None:
    """Falla si un catálogo compartido cambia solo en una versión del contrato."""
    from jurisprudence_case_catalogs import (
        CriterionId,
        EvidenceCategory,
        TieBreakerCriterion,
    )

    pairs = (
        ("criterios", set(CriterionId), VALID_CRITERIOS),
        ("categorías de prueba", set(EvidenceCategory), VALID_CATEGORIAS_PRUEBA),
        ("criterios de desempate CDI", set(TieBreakerCriterion), VALID_TIEBREAKER_PASOS),
    )
    mismatches = [
        name for name, current, legacy in pairs if {item.value for item in current} != legacy
    ]
    if mismatches:
        joined = ", ".join(mismatches)
        raise RuntimeError(f"Catálogos v2/v3 divergentes: {joined}")
