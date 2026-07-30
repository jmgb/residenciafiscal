from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from chat_strategy_models import (
    ComparisonReport,
    MarginalCost,
    StrategyAnswer,
    StrategySource,
)


def _cost() -> MarginalCost:
    return MarginalCost(
        amount_usd=Decimal("0.000001"),
        cost_microusd=1,
        measurement="ACTUAL",
        pricing_version="test",
        input_tokens=1,
        output_tokens=1,
        retrieved_document_tokens=0,
    )


def _answer(
    strategy: str,
    *,
    text: str,
    status: str = "completa",
    with_source: bool = True,
) -> StrategyAnswer:
    sources = (
        StrategySource(
            strategy=strategy,
            judgment_id="san-test-2026",
            page=3,
            source_sha256="a" * 64,
            quote="Fragmento literal de la sentencia.",
            verification="EXACT",
        ),
    )
    return StrategyAnswer(
        strategy=strategy,
        status=status,
        text=text,
        sources=sources if with_source else (),
        limits=(),
        cost=_cost(),
        model="test-model",
        latency_ms=12,
    )


def _report(*, ungrounded_b: bool = False) -> ComparisonReport:
    return ComparisonReport(
        request_id="request-secret",
        answers=(
            _answer("current_structured", text="Respuesta estructurada. "),
            _answer(
                "gemini_file_search",
                text="Respuesta File Search.",
                status="parcial" if ungrounded_b else "completa",
                with_source=not ungrounded_b,
            ),
        ),
    )


def _forbidden_keys(value: Any) -> set[str]:
    forbidden = {
        "artifact_path",
        "artifact_sha256",
        "cost",
        "expected_behavior",
        "latency_ms",
        "model",
        "request_id",
        "source_sha256",
        "strategy",
    }
    found: set[str] = set()
    if isinstance(value, dict):
        found.update(forbidden & value.keys())
        for child in value.values():
            found.update(_forbidden_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_forbidden_keys(child))
    return found


def test_paquete_ciego_elimina_identidad_coste_y_metadatos_del_proveedor() -> None:
    from chat_blind_review import ArtifactProvenance, build_blind_review_package

    dev_set = {
        "questions": [
            {
                "question_id": "Q1",
                "question": "¿Qué criterio se aplica?",
                "expected_behavior": "responder",
            },
            {
                "question_id": "Q2",
                "question": "¿Qué prueba se valoró?",
                "expected_behavior": "preguntar",
            },
        ]
    }
    package, key = build_blind_review_package(
        dev_set=dev_set,
        comparisons={"Q1": _report(), "Q2": _report()},
        intents={"Q1": "GENERAL_LEGAL_RULE", "Q2": "EVIDENCE_REQUIREMENTS"},
        x_strategies={
            "Q1": "current_structured",
            "Q2": "gemini_file_search",
        },
        provenance={
            "Q1": ArtifactProvenance(path="output/q1.json", sha256="b" * 64),
            "Q2": ArtifactProvenance(path="output/q2.json", sha256="c" * 64),
        },
        rubric_version="residenciafiscal-chat-f03-rubric/1",
        rubric_sha256="1" * 64,
        dev_set_sha256="2" * 64,
    )

    payload = package.model_dump(mode="json")
    assert _forbidden_keys(payload) == set()
    assert payload["questions"][0]["responses"][0]["label"] == "X"
    assert payload["questions"][0]["responses"][0]["text"] == ("Respuesta estructurada. ")
    assert payload["questions"][1]["responses"][0]["text"] == ("Respuesta File Search.")
    assert payload["questions"][0]["responses"][0]["sources"] == [
        {
            "judgment_id": "san-test-2026",
            "page": 3,
            "quote": "Fragmento literal de la sentencia.",
            "verification": "EXACT",
        }
    ]
    assert key.questions[0].x_strategy == "current_structured"
    assert key.questions[1].x_strategy == "gemini_file_search"
    assert key.questions[0].artifact_sha256 == "b" * 64
    assert payload["rubric_sha256"] == "1" * 64
    assert payload["dev_set_sha256"] == "2" * 64


def test_paquete_aplica_gate_actual_a_respuesta_legacy_sin_fuentes() -> None:
    from chat_blind_review import ArtifactProvenance, build_blind_review_package

    package, _key = build_blind_review_package(
        dev_set={
            "questions": [
                {
                    "question_id": "Q1",
                    "question": "¿Hay casos opuestos?",
                    "expected_behavior": "responder",
                }
            ]
        },
        comparisons={"Q1": _report(ungrounded_b=True)},
        intents={"Q1": "COMPARATIVE_CASES"},
        x_strategies={"Q1": "gemini_file_search"},
        provenance={"Q1": ArtifactProvenance(path="output/q1.json", sha256="d" * 64)},
        rubric_version="residenciafiscal-chat-f03-rubric/1",
        rubric_sha256="1" * 64,
        dev_set_sha256="2" * 64,
    )

    response_x = package.questions[0].responses[0]
    assert response_x.status == "error"
    assert response_x.text == ""
    assert response_x.sources == ()
    assert "retirada" in response_x.limits[0]


def test_paquete_rechaza_orden_x_desequilibrado() -> None:
    from chat_blind_review import ArtifactProvenance, build_blind_review_package

    with pytest.raises(ValueError, match="equilibr"):
        build_blind_review_package(
            dev_set={
                "questions": [
                    {"question_id": "Q1", "question": "Pregunta 1"},
                    {"question_id": "Q2", "question": "Pregunta 2"},
                ]
            },
            comparisons={"Q1": _report(), "Q2": _report()},
            intents={"Q1": "GENERAL_LEGAL_RULE", "Q2": "GENERAL_LEGAL_RULE"},
            x_strategies={
                "Q1": "current_structured",
                "Q2": "current_structured",
            },
            provenance={
                "Q1": ArtifactProvenance(path="output/q1.json", sha256="e" * 64),
                "Q2": ArtifactProvenance(path="output/q2.json", sha256="f" * 64),
            },
            rubric_version="residenciafiscal-chat-f03-rubric/1",
            rubric_sha256="1" * 64,
            dev_set_sha256="2" * 64,
        )


def test_generador_valida_hash_y_escribe_paquete_formulario_y_clave(
    tmp_path: Path,
) -> None:
    from chat_blind_review import generate_blind_review_artifacts, main

    dev_path = tmp_path / "dev.json"
    artifact_path = tmp_path / "comparison.json"
    manifest_path = tmp_path / "manifest.json"
    rubric_path = tmp_path / "rubric.md"
    package_json = tmp_path / "blind.json"
    package_markdown = tmp_path / "blind.md"
    form_markdown = tmp_path / "form.md"
    reveal_key = tmp_path / "key.json"

    dev_path.write_text(
        json.dumps(
            {
                "questions": [
                    {"question_id": "Q1", "question": "Pregunta 1"},
                    {"question_id": "Q2", "question": "Pregunta 2"},
                ]
            }
        )
    )
    artifact_path.write_text(_report().model_dump_json())
    artifact_sha256 = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    rubric_path.write_text("# Rúbrica")
    rubric_sha256 = hashlib.sha256(rubric_path.read_bytes()).hexdigest()
    dev_set_sha256 = hashlib.sha256(dev_path.read_bytes()).hexdigest()
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "residenciafiscal-chat-f03-build/1",
                "rubric_version": "residenciafiscal-chat-f03-rubric/1",
                "rubric_path": str(rubric_path.relative_to(tmp_path)),
                "rubric_sha256": rubric_sha256,
                "dev_set_path": str(dev_path.relative_to(tmp_path)),
                "dev_set_sha256": dev_set_sha256,
                "items": [
                    {
                        "question_id": "Q1",
                        "intent": "GENERAL_LEGAL_RULE",
                        "artifact_path": str(artifact_path.relative_to(tmp_path)),
                        "artifact_sha256": artifact_sha256,
                        "x_strategy": "current_structured",
                    },
                    {
                        "question_id": "Q2",
                        "intent": "GENERAL_LEGAL_RULE",
                        "artifact_path": str(artifact_path.relative_to(tmp_path)),
                        "artifact_sha256": artifact_sha256,
                        "x_strategy": "gemini_file_search",
                    },
                ],
            }
        )
    )

    assert (
        main(
            [
                "--project-root",
                str(tmp_path),
                "--manifest",
                str(manifest_path),
                "--package-json",
                str(package_json),
                "--package-markdown",
                str(package_markdown),
                "--review-form",
                str(form_markdown),
                "--reveal-key",
                str(reveal_key),
            ]
        )
        == 0
    )
    first_outputs = {
        path.name: path.read_bytes()
        for path in (package_json, package_markdown, form_markdown, reveal_key)
    }
    generate_blind_review_artifacts(
        project_root=tmp_path,
        manifest_path=manifest_path,
        package_json_path=package_json,
        package_markdown_path=package_markdown,
        review_form_path=form_markdown,
        reveal_key_path=reveal_key,
    )

    assert first_outputs == {
        path.name: path.read_bytes()
        for path in (package_json, package_markdown, form_markdown, reveal_key)
    }
    blind_payload = json.loads(package_json.read_bytes())
    assert _forbidden_keys(blind_payload) == set()
    assert "Respuesta X" in package_markdown.read_text()
    assert "Respuesta Y" in package_markdown.read_text()
    assert not any(line.endswith(" ") for line in package_markdown.read_text().splitlines())
    assert "current_structured" not in package_markdown.read_text()
    assert "Puntuaciones (0, 1, 2 o N/A)" in form_markdown.read_text()
    assert "[ ] pasa [ ] falla [ ] N/A" in form_markdown.read_text()
    assert "No abrir la clave" in form_markdown.read_text()
    assert "(CHAT_STRATEGY_F03_LEGAL_REVIEW_PROTOCOL.md)" in form_markdown.read_text()
    assert "## Declaración inicial del revisor jurídico" in form_markdown.read_text()
    assert "## Declaración de cierre" in form_markdown.read_text()
    assert "He completado las 4 respuestas y las 2 parejas." in form_markdown.read_text()
    assert "CHAT_STRATEGY_F03_BUILD.json" in form_markdown.read_text()
    assert "(CHAT_STRATEGY_F03_RUBRIC.md)" in form_markdown.read_text()
    assert "(CHAT_STRATEGY_F03_BLIND_REVIEW.md)" in form_markdown.read_text()
    assert "Copiar esta plantilla" in form_markdown.read_text()
    assert "CHAT_STRATEGY_F03_REVIEW_COMPLETED.md" in form_markdown.read_text()

    rubric_path.write_text("# Rúbrica alterada")
    with pytest.raises(ValueError, match="SHA-256.*rúbrica"):
        generate_blind_review_artifacts(
            project_root=tmp_path,
            manifest_path=manifest_path,
            package_json_path=package_json,
            package_markdown_path=package_markdown,
            review_form_path=form_markdown,
            reveal_key_path=reveal_key,
        )
    rubric_path.write_text("# Rúbrica")

    manifest = json.loads(manifest_path.read_bytes())
    manifest["schema_version"] = "otro-contrato"
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="schema_version"):
        generate_blind_review_artifacts(
            project_root=tmp_path,
            manifest_path=manifest_path,
            package_json_path=package_json,
            package_markdown_path=package_markdown,
            review_form_path=form_markdown,
            reveal_key_path=reveal_key,
        )

    manifest["schema_version"] = "residenciafiscal-chat-f03-build/1"
    manifest["items"][0]["artifact_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="SHA-256"):
        generate_blind_review_artifacts(
            project_root=tmp_path,
            manifest_path=manifest_path,
            package_json_path=package_json,
            package_markdown_path=package_markdown,
            review_form_path=form_markdown,
            reveal_key_path=reveal_key,
        )
