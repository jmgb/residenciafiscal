from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


class FakeOperations:
    def get(self, operation: Any) -> Any:
        return SimpleNamespace(
            name=operation.name,
            done=True,
            error=None,
            response=SimpleNamespace(document_name=f"documents/{operation.name}"),
        )


class FakeFileSearchStores:
    def __init__(self) -> None:
        self.uploads: list[dict[str, Any]] = []
        self.deleted: list[tuple[str, dict[str, bool]]] = []
        self.created: list[dict[str, str]] = []

    def create(self, *, config: dict[str, str]) -> Any:
        self.created.append(config)
        return SimpleNamespace(name="fileSearchStores/f0")

    def upload_to_file_search_store(self, **kwargs: Any) -> Any:
        self.uploads.append(kwargs)
        return SimpleNamespace(name=f"upload-{len(self.uploads)}", done=False)

    def delete(self, *, name: str, config: dict[str, bool]) -> None:
        self.deleted.append((name, config))


class FakeGoogleClient:
    def __init__(self) -> None:
        self.file_search_stores = FakeFileSearchStores()
        self.operations = FakeOperations()


class FailingSecondUploadFileSearchStores(FakeFileSearchStores):
    def upload_to_file_search_store(self, **kwargs: Any) -> Any:
        if len(self.uploads) == 1:
            raise RuntimeError("upload failed")
        return super().upload_to_file_search_store(**kwargs)


def _write_manifest(root: Path, count: int = 5) -> Path:
    documents = []
    for index in range(count):
        source = root / f"sentencias/SAN_{index}.pdf"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(f"pdf-{index}".encode())
        documents.append(
            {
                "judgment_id": f"san-{index}",
                "source_file": f"sentencias/SAN_{index}.pdf",
                "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "proposal_path": f"proposals/{index}.json",
                "evaluation_path": f"evaluations/{index}.json",
            }
        )
    manifest = root / "sample.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "residenciafiscal-jurisprudence-sample/1",
                "sample_id": "sample-5",
                "expected_documents": count,
                "documents": documents,
            }
        ),
        encoding="utf-8",
    )
    return manifest


def test_prepara_store_con_exactamente_cinco_pdf_y_metadatos(tmp_path: Path) -> None:
    from gemini_file_search_store import prepare_sample_store
    from google_genai_file_search import GoogleGenAIFileSearchGateway

    client = FakeGoogleClient()
    receipt = prepare_sample_store(
        gateway=GoogleGenAIFileSearchGateway(client),
        manifest_path=_write_manifest(tmp_path),
        project_root=tmp_path,
    )

    assert receipt.store_name == "fileSearchStores/f0"
    assert len(receipt.documents) == 5
    assert all(document.status == "ACTIVE" for document in receipt.documents)
    assert client.file_search_stores.created == [
        {
            "display_name": "residenciafiscal-f0-sample-5",
            "embedding_model": "models/gemini-embedding-2",
        }
    ]
    assert [item["config"]["display_name"] for item in client.file_search_stores.uploads] == [
        f"SAN_{index}.pdf" for index in range(5)
    ]
    first_metadata = client.file_search_stores.uploads[0]["config"]["custom_metadata"]
    assert first_metadata == [
        {"key": "judgment_id", "string_value": "san-0"},
        {"key": "authority", "string_value": "audiencia_nacional"},
        {
            "key": "source_sha256",
            "string_value": hashlib.sha256(b"pdf-0").hexdigest(),
        },
    ]


def test_rechaza_manifiesto_que_no_tiene_cinco_pdf(tmp_path: Path) -> None:
    from gemini_file_search_store import prepare_sample_store
    from google_genai_file_search import GoogleGenAIFileSearchGateway

    with pytest.raises(ValueError, match="exactamente cinco"):
        prepare_sample_store(
            gateway=GoogleGenAIFileSearchGateway(FakeGoogleClient()),
            manifest_path=_write_manifest(tmp_path, count=4),
            project_root=tmp_path,
        )


def test_rechaza_pdf_cuyo_hash_no_coincide_antes_de_crear_store(tmp_path: Path) -> None:
    from gemini_file_search_store import prepare_sample_store
    from google_genai_file_search import GoogleGenAIFileSearchGateway

    manifest = _write_manifest(tmp_path)
    (tmp_path / "sentencias/SAN_0.pdf").write_bytes(b"altered")
    client = FakeGoogleClient()

    with pytest.raises(ValueError, match="source_sha256"):
        prepare_sample_store(
            gateway=GoogleGenAIFileSearchGateway(client),
            manifest_path=manifest,
            project_root=tmp_path,
        )
    assert client.file_search_stores.uploads == []


def test_elimina_store_de_forma_explicita() -> None:
    from google_genai_file_search import GoogleGenAIFileSearchGateway

    client = FakeGoogleClient()
    GoogleGenAIFileSearchGateway(client).delete_store("fileSearchStores/f0")

    assert client.file_search_stores.deleted == [("fileSearchStores/f0", {"force": True})]


def test_elimina_store_incompleto_si_falla_una_subida(tmp_path: Path) -> None:
    from gemini_file_search_store import prepare_sample_store
    from google_genai_file_search import GoogleGenAIFileSearchGateway

    client = FakeGoogleClient()
    client.file_search_stores = FailingSecondUploadFileSearchStores()

    with pytest.raises(RuntimeError, match="upload failed"):
        prepare_sample_store(
            gateway=GoogleGenAIFileSearchGateway(client),
            manifest_path=_write_manifest(tmp_path),
            project_root=tmp_path,
        )

    assert client.file_search_stores.deleted == [("fileSearchStores/f0", {"force": True})]


def test_prepara_store_reanudable_con_las_106_del_rollout() -> None:
    from gemini_file_search_store import prepare_file_search_store
    from google_genai_file_search import GoogleGenAIFileSearchGateway

    project_root = Path(__file__).resolve().parents[1]
    manifest = project_root / "sentencias/jurisprudence_v3_rollout_106.json"
    client = FakeGoogleClient()
    checkpoints: list[Any] = []

    receipt = prepare_file_search_store(
        gateway=GoogleGenAIFileSearchGateway(client, poll_interval_seconds=0),
        manifest_path=manifest,
        project_root=project_root,
        checkpoint=checkpoints.append,
    )

    assert receipt.status == "ACTIVE"
    assert receipt.expected_documents == 106
    assert len(receipt.documents) == 106
    assert len(client.file_search_stores.uploads) == 106
    assert len(checkpoints) == 108  # store creado + cada PDF + cierre ACTIVE
    assert client.file_search_stores.created[0]["display_name"] == (
        "residenciafiscal-rollout-106-authority-v2"
    )


def test_reanuda_desde_el_ultimo_pdf_confirmado_sin_borrar_el_store(
    tmp_path: Path,
) -> None:
    from gemini_file_search_store import prepare_file_search_store
    from google_genai_file_search import GoogleGenAIFileSearchGateway

    manifest = _write_manifest(tmp_path)
    first_client = FakeGoogleClient()
    first_client.file_search_stores = FailingSecondUploadFileSearchStores()
    checkpoints: list[Any] = []

    with pytest.raises(RuntimeError, match="upload failed"):
        prepare_file_search_store(
            gateway=GoogleGenAIFileSearchGateway(
                first_client,
                poll_interval_seconds=0,
            ),
            manifest_path=manifest,
            project_root=tmp_path,
            checkpoint=checkpoints.append,
        )

    partial = checkpoints[-1]
    assert partial.status == "PREPARING"
    assert len(partial.documents) == 1
    assert first_client.file_search_stores.deleted == []

    second_client = FakeGoogleClient()
    completed = prepare_file_search_store(
        gateway=GoogleGenAIFileSearchGateway(second_client, poll_interval_seconds=0),
        manifest_path=manifest,
        project_root=tmp_path,
        existing_state=partial,
    )

    assert completed.status == "ACTIVE"
    assert len(completed.documents) == 5
    assert len(second_client.file_search_stores.uploads) == 4
    assert second_client.file_search_stores.created == []


def test_rechaza_checkpoint_con_hash_de_documento_alterado(tmp_path: Path) -> None:
    from gemini_file_search_store import prepare_file_search_store
    from google_genai_file_search import GoogleGenAIFileSearchGateway

    manifest = _write_manifest(tmp_path)
    first_client = FakeGoogleClient()
    first_client.file_search_stores = FailingSecondUploadFileSearchStores()
    checkpoints: list[Any] = []

    with pytest.raises(RuntimeError, match="upload failed"):
        prepare_file_search_store(
            gateway=GoogleGenAIFileSearchGateway(first_client, poll_interval_seconds=0),
            manifest_path=manifest,
            project_root=tmp_path,
            checkpoint=checkpoints.append,
        )

    partial = checkpoints[-1]
    altered_document = partial.documents[0].model_copy(update={"source_sha256": "0" * 64})
    altered = partial.model_copy(update={"documents": (altered_document,)})

    with pytest.raises(ValueError, match="documentos del checkpoint"):
        prepare_file_search_store(
            gateway=GoogleGenAIFileSearchGateway(FakeGoogleClient(), poll_interval_seconds=0),
            manifest_path=manifest,
            project_root=tmp_path,
            existing_state=altered,
        )
