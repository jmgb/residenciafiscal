"""Compatibilidad entre catálogos heredados y contrato v3."""


def test_los_catalogos_compartidos_con_v2_permanecen_sincronizados() -> None:
    from jurisprudence_case_catalog_compatibility import (
        validate_legacy_catalog_compatibility,
    )

    validate_legacy_catalog_compatibility()
