"""Puerto de persistencia del chat y adaptador RPC de Supabase.

La ruta HTTP depende del protocolo, no de una tabla. El adaptador solo llama a
las RPC públicas de ciclo de vida ya existentes; nunca usa SELECT/INSERT directo
contra el schema privado.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any, Protocol

import aiohttp

from chat_strategy_models import ComparisonReport


class SupabaseRpcClient(Protocol):
    async def rpc(self, function_name: str, parameters: dict[str, Any]) -> Any: ...


class SupabaseRpcError(RuntimeError):
    """Error técnico sin conservar el cuerpo potencialmente sensible de Supabase."""

    def __init__(self, operation: str, status: int) -> None:
        super().__init__(f"RPC {operation} devolvió HTTP {status}")
        self.operation = operation
        self.status = status


class AiohttpSupabaseRpcClient:
    """Cliente mínimo para PostgREST RPC con una credencial server-side."""

    def __init__(self, url: str, key: str, *, timeout_seconds: float = 10.0) -> None:
        if not url or not key:
            raise ValueError("faltan credenciales de Supabase")
        self._rpc_url = f"{url.rstrip('/')}/rest/v1/rpc"
        self._key = key
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    async def rpc(self, function_name: str, parameters: dict[str, Any]) -> Any:
        async with aiohttp.ClientSession(timeout=self._timeout) as session:
            async with session.post(
                f"{self._rpc_url}/{function_name}",
                headers={
                    "apikey": self._key,
                    "authorization": f"Bearer {self._key}",
                    "content-type": "application/json",
                },
                json=parameters,
            ) as response:
                if response.status >= 400:
                    raise SupabaseRpcError(function_name, response.status)
                if response.status == 204:
                    return None
                return await response.json()


@dataclass(frozen=True)
class ChatExperimentContext:
    experiment_version: str
    deployed_commit: str
    comparison_schema_version: str
    structured_corpus_version: str
    structured_prompt_version: str
    file_search_store: str
    file_search_prompt_version: str

    def as_payload(self) -> dict[str, str]:
        return asdict(self)


class SupabaseChatRepository:
    """Implementa el ciclo create → complete/fail mediante RPC únicamente."""

    def __init__(self, client: SupabaseRpcClient, experiment: ChatExperimentContext) -> None:
        self._client = client
        self._experiment = experiment

    async def record(
        self,
        *,
        request_id: str,
        conversation_id: str,
        user_message_id: str,
        country_path: str,
        question: str,
    ) -> str:
        result = await self._client.rpc(
            "create_chat_request",
            {
                "p_request_id": request_id,
                "p_conversation_id": conversation_id,
                "p_user_message_id": user_message_id,
                "p_country_path": country_path,
                "p_question": question,
                "p_experiment": self._experiment.as_payload(),
            },
        )
        if not isinstance(result, Mapping) or not isinstance(result.get("request_id"), str):
            raise SupabaseRpcError("create_chat_request", 502)
        return result["request_id"]

    async def complete(self, *, request_id: str, report: ComparisonReport) -> None:
        actual_costs = [answer.cost.cost_microusd for answer in report.answers]
        measured_costs = [value for value in actual_costs if value is not None]
        actual_complete = all(
            answer.cost.measurement == "ACTUAL" and answer.cost.cost_microusd is not None
            for answer in report.answers
        )
        actual_microusd = sum(measured_costs)
        answers = [
            {
                "strategy": answer.strategy,
                "status": answer.status,
                "content": answer.text,
                "model": answer.model,
                "reasoning_effort": answer.reasoning_effort,
                "latency_ms": answer.latency_ms,
                "limits": list(answer.limits),
                "sources": [source.model_dump(mode="json") for source in answer.sources],
                "claims": [claim.model_dump(mode="json") for claim in answer.claims],
                "diagnostics": answer.diagnostics,
                "cost_microusd": answer.cost.cost_microusd,
                "cost_measurement": answer.cost.measurement,
                "pricing_version": answer.cost.pricing_version,
                "input_tokens": answer.cost.input_tokens,
                "output_tokens": answer.cost.output_tokens,
                "retrieved_document_tokens": answer.cost.retrieved_document_tokens,
            }
            for answer in report.answers
        ]
        result = await self._client.rpc(
            "complete_chat_request",
            {
                "p_request_id": request_id,
                "p_actual_microusd": actual_microusd,
                "p_actual_complete": actual_complete,
                "p_answers": answers,
            },
        )
        if result not in (True, None):
            raise SupabaseRpcError("complete_chat_request", 502)

    async def fail(self, *, request_id: str, status: str, failure_code: str) -> None:
        if status not in {"failed", "timed_out"}:
            raise ValueError("estado terminal inválido")
        result = await self._client.rpc(
            "fail_chat_request",
            {
                "p_request_id": request_id,
                "p_status": status,
                "p_failure_code": failure_code,
            },
        )
        if result not in (True, None):
            raise SupabaseRpcError("fail_chat_request", 502)


def get_production_chat_repository() -> SupabaseChatRepository | None:
    """Crea el adaptador solo cuando se han inyectado las credenciales del host."""
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_CHAT_RUNTIME_KEY", "").strip()
    if not url or not key:
        return None
    experiment = ChatExperimentContext(
        experiment_version=os.getenv("CHAT_EXPERIMENT_VERSION", "chat-alfredo/1"),
        deployed_commit=os.getenv("CHAT_DEPLOYED_COMMIT", "unknown"),
        comparison_schema_version="residenciafiscal-chat-comparison/1",
        structured_corpus_version=os.getenv(
            "CHAT_STRUCTURED_CORPUS_VERSION", "residenciafiscal-case/3"
        ),
        structured_prompt_version=os.getenv(
            "CHAT_STRUCTURED_PROMPT_VERSION", "structured-claims-v4"
        ),
        file_search_store=os.getenv("CHAT_FILE_SEARCH_STORE_NAME", "unknown"),
        file_search_prompt_version=os.getenv(
            "CHAT_FILE_SEARCH_PROMPT_VERSION", "file-search-authority-v8"
        ),
    )
    return SupabaseChatRepository(AiohttpSupabaseRpcClient(url, key), experiment)
