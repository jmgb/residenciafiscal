#!/usr/bin/env python3
"""Servidor MCP stdio con tres herramientas de lectura del corpus cerrado."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from deep_research_corpus import CorpusRepository

_TOOLS = [
    {
        "name": "search_corpus",
        "description": "Busca cuestiones relevantes en el índice JSON y devuelve candidatos acotados.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["query"],
            "properties": {
                "query": {"type": "string", "minLength": 3, "maxLength": 500},
                "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 8},
            },
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "read_case",
        "description": "Lee el caso JSON estructurado de una sentencia candidata.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["judgment_id"],
            "properties": {"judgment_id": {"type": "string", "pattern": "^[a-z0-9-]+$"}},
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "read_verbatim_page",
        "description": "Lee raw_page_text y hash canónicos de una página para citar literalmente.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["judgment_id", "page"],
            "properties": {
                "judgment_id": {"type": "string", "pattern": "^[a-z0-9-]+$"},
                "page": {"type": "integer", "minimum": 1},
            },
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    },
]


def dispatch_tool(repository: CorpusRepository, name: str, arguments: object) -> dict[str, Any]:
    if not isinstance(arguments, dict):
        raise ValueError("tool arguments must be an object")
    if name == "search_corpus":
        return repository.search(arguments.get("query", ""), limit=arguments.get("limit", 8))
    if name == "read_case":
        return repository.read_case(arguments.get("judgment_id", ""))
    if name == "read_verbatim_page":
        return repository.read_verbatim_page(
            arguments.get("judgment_id", ""), arguments.get("page", 0)
        )
    raise ValueError("unsupported corpus tool")


def _result(request_id: object, result: object) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _handle(repository: CorpusRepository, request: dict[str, Any]) -> dict[str, Any] | None:
    request_id = request.get("id")
    method = request.get("method")
    if method == "initialize":
        version = (request.get("params") or {}).get("protocolVersion", "2025-06-18")
        return _result(
            request_id,
            {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "residenciafiscal-corpus", "version": "2.0.0"},
            },
        )
    if method == "ping":
        return _result(request_id, {})
    if method == "tools/list":
        return _result(request_id, {"tools": _TOOLS})
    if method == "tools/call":
        params = request.get("params") or {}
        try:
            value = dispatch_tool(repository, params.get("name", ""), params.get("arguments", {}))
            text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            return _result(
                request_id,
                {"content": [{"type": "text", "text": text}], "structuredContent": value},
            )
        except (TypeError, ValueError) as exc:
            return _result(
                request_id,
                {"content": [{"type": "text", "text": str(exc)}], "isError": True},
            )
    if isinstance(method, str) and method.startswith("notifications/"):
        return None
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": "Method not found"},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    arguments = parser.parse_args()
    repository = CorpusRepository(arguments.bundle)
    for line in sys.stdin:
        try:
            request = json.loads(line)
            response = _handle(repository, request)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32600, "message": str(exc)},
            }
        if response is not None:
            print(json.dumps(response, ensure_ascii=False, separators=(",", ":")), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
