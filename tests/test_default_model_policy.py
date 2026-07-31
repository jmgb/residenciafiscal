"""Contrato de la política LLM elegida por residenciafiscal."""

from config import DEFAULT_MODEL, GPT_5_MINI, REASONING_EFFORT, SUPPORTED_REASONING_EFFORTS


def test_luna_con_esfuerzo_maximo_es_la_politica_por_defecto() -> None:
    assert DEFAULT_MODEL == GPT_5_MINI == "gpt-5.6-luna"
    assert REASONING_EFFORT == "max"


def test_esfuerzos_admitidos_proceden_del_catalogo_del_gateway() -> None:
    assert SUPPORTED_REASONING_EFFORTS == (
        "none",
        "low",
        "medium",
        "high",
        "xhigh",
        "max",
    )
