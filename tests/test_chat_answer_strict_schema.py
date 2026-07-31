"""El esquema que envía A tiene que ser aceptable en modo estricto.

La suite del chat usa dobles de proveedor, que aceptan cualquier esquema. Eso
dejó pasar un contrato que Gemini admitía y la Responses API de OpenAI rechaza
entero con `invalid_json_schema`, de modo que el día que la política del chat
apuntase a Luna todas las respuestas de A habrían fallado con los tests en
verde. Este módulo cierra ese hueco sin red y sin coste: reimplementa las dos
reglas del modo estricto y las aplica al esquema real.

Se exige siempre, no solo cuando el modelo declarado sea de OpenAI. El modo
estricto es el subconjunto portable —lo que pasa ahí pasa en los demás
proveedores—, y A debe poder ejecutarse sobre el modelo que declare
`chat_model_policy` sin que cambiar esa línea rompa la estrategia.
"""

from __future__ import annotations

from typing import Any

import pytest

from chat_answer_contract import StructuredChatAnswerDraft


def _objetos(schema: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Todos los subesquemas de tipo objeto, con una ruta para el mensaje."""
    encontrados: list[tuple[str, dict[str, Any]]] = []

    def recorrer(nodo: Any, ruta: str) -> None:
        if isinstance(nodo, dict):
            if nodo.get("type") == "object" or "properties" in nodo:
                encontrados.append((ruta or "raíz", nodo))
            for clave, valor in nodo.items():
                recorrer(valor, f"{ruta}.{clave}" if ruta else clave)
        elif isinstance(nodo, list):
            for indice, valor in enumerate(nodo):
                recorrer(valor, f"{ruta}[{indice}]")

    recorrer(schema, "")
    return encontrados


@pytest.fixture
def schema() -> dict[str, Any]:
    return StructuredChatAnswerDraft.model_json_schema()


def test_todas_las_propiedades_estan_en_required(schema: dict[str, Any]) -> None:
    """La regla que rompía el contrato: `limits` tenía valor por defecto.

    Pydantic omite de `required` cualquier campo con valor por defecto, y el
    modo estricto rechaza el esquema completo si falta uno solo.
    """
    for ruta, objeto in _objetos(schema):
        propiedades = set(objeto.get("properties", {}))
        if not propiedades:
            continue
        faltan = sorted(propiedades - set(objeto.get("required", [])))

        assert faltan == [], (
            f"en {ruta} faltan en `required`: {faltan}. El modo estricto las exige "
            "todas; un campo con valor por defecto en Pydantic no llega a `required`"
        )


def test_ningun_objeto_admite_propiedades_extra(schema: dict[str, Any]) -> None:
    """La otra regla del modo estricto, que hoy se cumple sola por `extra=forbid`."""
    for ruta, objeto in _objetos(schema):
        if not objeto.get("properties"):
            continue

        assert objeto.get("additionalProperties") is False, (
            f"en {ruta} falta `additionalProperties: false`"
        )


def test_el_prompt_pide_los_campos_que_el_esquema_exige() -> None:
    """Exigir en el esquema lo que no se pide en las instrucciones es una trampa.

    El modelo no ve el porqué del contrato: si el esquema obliga a emitir un
    campo que el prompt nunca menciona, el fallo aparece en producción y se
    atribuye al modelo.
    """
    from chat_answer_prompt import STRUCTURED_ANSWER_INSTRUCTIONS

    obligatorios = set(StructuredChatAnswerDraft.model_json_schema()["required"])
    sin_mencionar = sorted(
        campo
        for campo in obligatorios
        if campo not in STRUCTURED_ANSWER_INSTRUCTIONS and campo not in {"status", "answer"}
    )

    assert sin_mencionar == [], (
        f"el esquema exige {sin_mencionar} pero las instrucciones no los piden"
    )
