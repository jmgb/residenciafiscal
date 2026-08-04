"""Orquestador local F0: dos respuestas independientes para una pregunta."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Protocol

from chat_error_names import safe_error_name
from chat_strategy_costs import unknown_failure_cost
from chat_strategy_logging import StrategyLogRecord, append_strategy_log
from chat_strategy_models import (
    PUBLIC_STRATEGY_ERROR_LIMIT,
    ComparisonReport,
    StrategyAnswer,
    StrategyId,
)


class ChatStrategy(Protocol):
    async def answer(self, question: str, *, request_id: str) -> StrategyAnswer: ...


def _error_answer(strategy: StrategyId, error: Exception) -> StrategyAnswer:
    return StrategyAnswer(
        strategy=strategy,
        status="error",
        text="",
        sources=(),
        limits=(PUBLIC_STRATEGY_ERROR_LIMIT,),
        cost=unknown_failure_cost(),
        model="unavailable",
        diagnostics={
            "failure_code": "exception",
            "error_name": safe_error_name(error),
        },
        latency_ms=0,
    )


async def _run_isolated(
    strategy_id: StrategyId,
    strategy: ChatStrategy,
    question: str,
    request_id: str,
) -> StrategyAnswer:
    try:
        answer = await strategy.answer(question, request_id=request_id)
    except Exception as error:
        return _error_answer(strategy_id, error)
    if answer.strategy != strategy_id:
        return _error_answer(strategy_id, ValueError("strategy devuelta no coincide"))
    return answer


async def compare_strategies(
    *,
    question: str,
    structured: ChatStrategy | None,
    file_search: ChatStrategy | None,
    output_path: Path,
    log_path: Path,
    request_id: str,
) -> ComparisonReport:
    """Ejecuta A y B en paralelo y conserva siempre el orden público A → B."""

    tasks = []
    if structured is not None:
        tasks.append(_run_isolated("current_structured", structured, question, request_id))
    if file_search is not None:
        tasks.append(_run_isolated("gemini_file_search", file_search, question, request_id))
    if not tasks:
        raise ValueError("no hay estrategias activas")
    answers = tuple(await asyncio.gather(*tasks))
    report = ComparisonReport(request_id=request_id, answers=answers)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            report.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    for answer in answers:
        append_strategy_log(
            log_path,
            StrategyLogRecord(
                request_id=request_id,
                strategy=answer.strategy,
                status=answer.status,
                cost=answer.cost,
                model=answer.model,
                latency_ms=answer.latency_ms,
            ),
        )
    return report
