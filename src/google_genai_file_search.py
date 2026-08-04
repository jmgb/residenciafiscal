"""Adaptador mínimo del SDK Google Gen AI para Gemini File Search."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any


class GoogleGenAIFileSearchGateway:
    """Aísla el SDK de Google del contrato jurídico y del comparador."""

    def __init__(
        self,
        client: Any,
        *,
        operation_timeout_seconds: float = 600,
        poll_interval_seconds: float = 1,
    ) -> None:
        self._client = client
        self._operation_timeout_seconds = operation_timeout_seconds
        self._poll_interval_seconds = poll_interval_seconds

    def create_store(self, display_name: str) -> str:
        store = self._client.file_search_stores.create(
            config={
                "display_name": display_name,
                "embedding_model": "models/gemini-embedding-2",
            }
        )
        return str(store.name)

    def upload_pdf(
        self,
        *,
        store_name: str,
        source: Path,
        judgment_id: str,
        source_sha256: str,
    ) -> str:
        authority = (
            "tribunal_supremo"
            if judgment_id.startswith("sts-")
            else "audiencia_nacional"
            if judgment_id.startswith("san-")
            else "other"
        )
        operation = self._client.file_search_stores.upload_to_file_search_store(
            file_search_store_name=store_name,
            file=source,
            config={
                "display_name": source.name,
                "mime_type": "application/pdf",
                "custom_metadata": [
                    {"key": "judgment_id", "string_value": judgment_id},
                    {"key": "authority", "string_value": authority},
                    {"key": "source_sha256", "string_value": source_sha256},
                ],
            },
        )
        completed = self._wait_for_operation(operation)
        response = getattr(completed, "response", None)
        document_name = getattr(response, "document_name", None)
        return str(document_name or completed.name)

    def delete_store(self, store_name: str) -> None:
        self._client.file_search_stores.delete(name=store_name, config={"force": True})

    def query(
        self,
        *,
        model: str,
        store_name: str,
        prompt: str,
        response_schema: dict[str, Any],
        metadata_filter: str | None = None,
    ) -> Any:
        file_search_tool: dict[str, Any] = {
            "type": "file_search",
            "file_search_store_names": [store_name],
        }
        if metadata_filter:
            file_search_tool["metadata_filter"] = metadata_filter
        return self._client.interactions.create(
            model=model,
            input=prompt,
            tools=[file_search_tool],
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": response_schema,
            },
            store=False,
        )

    def _wait_for_operation(self, operation: Any) -> Any:
        deadline = time.monotonic() + self._operation_timeout_seconds
        current = operation
        while not getattr(current, "done", False):
            if time.monotonic() >= deadline:
                raise TimeoutError(f"operación File Search agotó el timeout: {current.name}")
            if self._poll_interval_seconds:
                time.sleep(self._poll_interval_seconds)
            current = self._client.operations.get(current)
        error = getattr(current, "error", None)
        if error:
            raise RuntimeError(f"operación File Search fallida: {error}")
        return current


def create_google_genai_gateway(api_key: str) -> GoogleGenAIFileSearchGateway:
    """Construye el cliente real solo en comandos explícitamente facturables."""

    from google import genai

    return GoogleGenAIFileSearchGateway(genai.Client(api_key=api_key))
