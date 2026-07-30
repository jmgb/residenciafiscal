from __future__ import annotations

import json
from pathlib import Path


def test_f02_dev_set_es_pequeno_representativo_y_derivado_del_banco() -> None:
    source_path = Path("knowledge/jurisprudencia-v3/evaluations/chat-question-pilot-5.bank.json")
    dev_path = Path("docs/experiments/CHAT_STRATEGY_F02_DEV_SET.json")
    source = json.loads(source_path.read_bytes())
    dev = json.loads(dev_path.read_bytes())
    source_by_id = {item["question_id"]: item for item in source["questions"]}

    assert dev["schema_version"] == "residenciafiscal-chat-f02-dev-set/1"
    assert dev["source_resource"] == str(source_path)
    assert 5 <= len(dev["questions"]) <= 10
    assert len({item["question_id"] for item in dev["questions"]}) == len(dev["questions"])
    assert {item["dimension"] for item in dev["questions"]} == {
        "general",
        "caso_particular_incompleto",
        "prueba_concreta",
        "convenio",
        "familia",
        "cobertura_insuficiente",
        "contraste",
        "fuentes",
    }
    assert {item["expected_behavior"] for item in dev["questions"]} == {
        "responder",
        "parcial",
        "preguntar",
        "abstenerse",
    }
    for item in dev["questions"]:
        source_item = source_by_id[item["question_id"]]
        assert item["question"] == source_item["question"]
        assert item["expected_behavior"] == source_item["behavior"]
