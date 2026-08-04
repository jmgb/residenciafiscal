"""El contrato de A tiene que sobrevivir al modo estricto antes de pagar nada.

`structured-claims-v4` anida un objeto dentro de un array, que es justo la forma
que el modo estricto de la Responses API rechaza si falta `required` o
`additionalProperties` en la definición anidada. Comprobarlo aquí cuesta cero y
evita descubrir un `invalid_json_schema` con tráfico real.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from llm_gateway.providers.strict_schema import strict_json_schema  # noqa: E402

from chat_answer_contract import ChatAnswerDraft, StructuredChatAnswerDraft  # noqa: E402


def _objects(node: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(node, dict):
        if node.get("type") == "object" and "properties" in node:
            found.append(node)
        for value in node.values():
            found.extend(_objects(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_objects(item))
    return found


def test_el_contrato_de_a_se_cierra_entero_en_modo_estricto() -> None:
    schema = strict_json_schema(StructuredChatAnswerDraft)

    objects = _objects(schema)
    assert objects, "el esquema debe declarar al menos un objeto"
    for node in objects:
        assert node.get("additionalProperties") is False
        assert set(node.get("required", [])) == set(node["properties"])


def test_la_claim_anidada_declara_sus_dos_campos() -> None:
    schema = strict_json_schema(StructuredChatAnswerDraft)

    claim = schema["$defs"]["StructuredClaim"]

    assert set(claim["properties"]) == {"text", "evidence_ids"}
    assert claim["properties"]["evidence_ids"]["items"]["type"] == "string"


def test_el_contrato_de_b_conserva_su_forma_plana() -> None:
    schema = strict_json_schema(ChatAnswerDraft)

    assert set(schema["properties"]) == {"status", "answer", "limits"}
    assert "$defs" not in schema
