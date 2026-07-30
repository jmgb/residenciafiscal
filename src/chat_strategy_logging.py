"""Observabilidad JSONL del comparador sin contenido de usuario o modelo."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import Field

from chat_strategy_models import MarginalCost, StrategyId
from jurisprudence_case_catalogs import JurisprudenceCaseModel, NonEmptyText


class StrategyLogRecord(JurisprudenceCaseModel):
    request_id: NonEmptyText
    strategy: StrategyId
    status: NonEmptyText
    cost: MarginalCost
    model: NonEmptyText
    latency_ms: int = Field(ge=0)

    def as_log_payload(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "strategy": self.strategy,
            "status": self.status,
            "cost_microusd": self.cost.cost_microusd,
            "cost_measurement": self.cost.measurement,
            "pricing_version": self.cost.pricing_version,
            "model": self.model,
            "input_tokens": self.cost.input_tokens,
            "retrieved_document_tokens": self.cost.retrieved_document_tokens,
            "output_tokens": self.cost.output_tokens,
            "latency_ms": self.latency_ms,
        }


def append_strategy_log(destination: Path, record: StrategyLogRecord) -> None:
    """Añade una línea completa; el contrato del modelo impide campos de texto."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(
        record.as_log_payload(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    with destination.open("a", encoding="utf-8") as stream:
        stream.write(f"{serialized}\n")
