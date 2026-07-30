from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any


def _annotation(
    *,
    quote: str,
    page_number: int = 1,
    source_sha256: str = "a" * 64,
) -> Any:
    return SimpleNamespace(
        type="file_citation",
        file_name="SAN_1210_2023.pdf",
        source=quote,
        page_number=page_number,
        custom_metadata=[
            SimpleNamespace(key="judgment_id", string_value="san-1210-2023"),
            SimpleNamespace(key="source_sha256", string_value=source_sha256),
        ],
    )


def _interaction(answer: dict[str, Any], annotations: list[Any]) -> Any:
    content = SimpleNamespace(
        type="text",
        text=json.dumps(answer, ensure_ascii=False),
        annotations=annotations,
    )
    return SimpleNamespace(
        id="interaction-1",
        model="gemini-3.6-flash",
        status="completed",
        output_text=json.dumps(answer, ensure_ascii=False),
        steps=[SimpleNamespace(type="model_output", content=[content])],
        usage=SimpleNamespace(
            total_input_tokens=120,
            total_output_tokens=25,
            total_thought_tokens=5,
            input_tokens_by_modality=[
                SimpleNamespace(modality="text", tokens=70),
                SimpleNamespace(modality="document", tokens=50),
            ],
            total_cached_tokens=0,
            total_tool_use_tokens=0,
        ),
    )


class FakeInteractions:
    def __init__(self, response: Any) -> None:
        self.response = response
        self.requests: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.requests.append(kwargs)
        return self.response


class FakeGoogleClient:
    def __init__(self, response: Any) -> None:
        self.interactions = FakeInteractions(response)


def _write_verbatim(path: Path, text: str, source_sha256: str = "a" * 64) -> None:
    from verbatim_hashing import sha256_canonical_pages, sha256_utf8

    page = {
        "page_index": 1,
        "printed_page": "1",
        "raw_page_text": text,
        "text_sha256": sha256_utf8(text),
        "extraction_status": "TEXT_EXTRACTED",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "residenciafiscal-verbatim/1",
                "document_id": "san-1210-2023",
                "source_file": "sentencias/SAN_1210_2023.pdf",
                "source_sha256": source_sha256,
                "extractor": {"name": "pypdf", "version": "1"},
                "page_count": 1,
                "pages_sha256": sha256_canonical_pages([page]),
                "status": "COMPLETE",
                "pages": [page],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_respuesta_file_search_solo_publica_cita_literal_verificada(tmp_path: Path) -> None:
    from gemini_file_search_answer import GeminiFileSearchResponder
    from google_genai_file_search import GoogleGenAIFileSearchGateway

    quote = "La residencia fiscal se determina atendiendo a los hechos acreditados."
    artifact = tmp_path / "san-1210-2023.pages.json"
    _write_verbatim(artifact, f"Encabezado\n{quote}\nPie")
    response = _interaction(
        {
            "status": "completa",
            "answer": "La Sala atendió a los hechos acreditados.",
            "limits": [],
        },
        [_annotation(quote=quote)],
    )
    client = FakeGoogleClient(response)
    responder = GeminiFileSearchResponder(
        gateway=GoogleGenAIFileSearchGateway(client),
        store_name="fileSearchStores/f0",
        verbatim_artifacts={"san-1210-2023": artifact},
    )

    result = responder.answer("¿Qué hechos valoró la Sala?", request_id="req-1")

    assert result.strategy == "gemini_file_search"
    assert result.status == "completa"
    assert result.text == "La Sala atendió a los hechos acreditados."
    assert result.sources[0].quote == quote
    assert result.sources[0].page == 1
    assert result.sources[0].verification == "EXACT"
    assert result.model == "gemini-3.5-flash-lite"
    assert result.cost.input_tokens == 70
    assert result.cost.retrieved_document_tokens == 50
    assert result.cost.output_tokens == 30
    request = client.interactions.requests[0]
    assert request["model"] == "gemini-3.5-flash-lite"
    assert request["store"] is False
    assert request["tools"] == [
        {
            "type": "file_search",
            "file_search_store_names": ["fileSearchStores/f0"],
        }
    ]
    assert request["response_format"]["mime_type"] == "application/json"


def test_descarta_cita_no_literal_y_degrada_respuesta_a_parcial(tmp_path: Path) -> None:
    from gemini_file_search_answer import GeminiFileSearchResponder
    from google_genai_file_search import GoogleGenAIFileSearchGateway

    artifact = tmp_path / "san-1210-2023.pages.json"
    _write_verbatim(artifact, "Texto auténtico de la sentencia.")
    response = _interaction(
        {
            "status": "completa",
            "answer": "Afirmación que dependía de una cita.",
            "limits": [],
        },
        [_annotation(quote="Texto inventado por el proveedor.")],
    )
    responder = GeminiFileSearchResponder(
        gateway=GoogleGenAIFileSearchGateway(FakeGoogleClient(response)),
        store_name="fileSearchStores/f0",
        verbatim_artifacts={"san-1210-2023": artifact},
    )

    result = responder.answer("Pregunta", request_id="req-2")

    assert result.status == "parcial"
    assert result.sources == ()
    assert "citas no verificables" in result.limits[0]


def test_permite_promocion_manual_explicita_a_gemini_36_flash(tmp_path: Path) -> None:
    from gemini_file_search_answer import GeminiFileSearchResponder
    from google_genai_file_search import GoogleGenAIFileSearchGateway

    response = _interaction(
        {"status": "abstención", "answer": "", "limits": ["Sin cobertura."]},
        [],
    )
    client = FakeGoogleClient(response)
    responder = GeminiFileSearchResponder(
        gateway=GoogleGenAIFileSearchGateway(client),
        store_name="fileSearchStores/f0",
        verbatim_artifacts={},
        model="gemini-3.6-flash",
    )

    result = responder.answer("Pregunta", request_id="req-promotion")

    assert result.model == "gemini-3.6-flash"
    assert client.interactions.requests[0]["model"] == "gemini-3.6-flash"
