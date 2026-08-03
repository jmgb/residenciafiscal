"""Lectura acotada del bundle JSON de jurisprudencia para el perfil Codex."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_SAFE_JUDGMENT_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
_MAX_QUERY_CHARS = 500
_MAX_RESULTS = 20


class CorpusRepository:
    """Expone operaciones jurídicas concretas, nunca acceso genérico a ficheros."""

    def __init__(self, bundle_path: Path) -> None:
        self.bundle_path = bundle_path.resolve()
        if not self.bundle_path.is_dir():
            raise ValueError("bundle directory does not exist")

    def search(self, query: str, *, limit: int = 8) -> dict[str, Any]:
        query = query.strip()
        if not 1 <= len(query) <= _MAX_QUERY_CHARS:
            raise ValueError("query must contain between 1 and 500 characters")
        if not 1 <= limit <= _MAX_RESULTS:
            raise ValueError("limit must be between 1 and 20")
        normalized_query = query.casefold()
        tokens = {token for token in re.findall(r"\w+", normalized_query) if len(token) > 2}
        if not tokens:
            raise ValueError("query must contain at least one searchable token")
        corpus = self._read_json(Path("retrieval/rollout-106.corpus.json"))
        units = corpus.get("units") if isinstance(corpus, dict) else None
        if not isinstance(units, list):
            raise ValueError("invalid retrieval corpus")
        ranked: list[tuple[int, dict[str, Any]]] = []
        for unit in units:
            if not isinstance(unit, dict):
                continue
            searchable = str(unit.get("search_text") or "").casefold()
            score = sum(searchable.count(token) for token in tokens)
            if normalized_query in searchable:
                score += 10
            if score:
                ranked.append((score, self._search_result(unit, score)))
        ranked.sort(key=lambda item: (-item[0], item[1]["judgment_id"], item[1]["issue_id"]))
        return {"query": query, "results": [item for _, item in ranked[:limit]]}

    def read_case(self, judgment_id: str) -> dict[str, Any]:
        return self._read_json(Path("cases") / f"{self._judgment_id(judgment_id)}.case.json")

    def read_verbatim_page(self, judgment_id: str, page: int) -> dict[str, Any]:
        judgment_id = self._judgment_id(judgment_id)
        if not isinstance(page, int) or isinstance(page, bool) or page < 1:
            raise ValueError("page must be a positive integer")
        document = self._read_json(Path("verbatim") / f"{judgment_id}.pages.json")
        pages = document.get("pages")
        if not isinstance(pages, list):
            raise ValueError("invalid verbatim document")
        match = next(
            (item for item in pages if isinstance(item, dict) and item.get("page_index") == page),
            None,
        )
        if match is None or not isinstance(match.get("raw_page_text"), str):
            raise ValueError("page not found")
        return {
            "judgment_id": judgment_id,
            "page": page,
            "printed_page": match.get("printed_page"),
            "source_sha256": document.get("source_sha256"),
            "raw_page_text": match["raw_page_text"],
        }

    def _read_json(self, relative_path: Path) -> dict[str, Any]:
        target = (self.bundle_path / relative_path).resolve()
        if not target.is_relative_to(self.bundle_path) or target.suffix != ".json":
            raise ValueError("path outside JSON corpus")
        try:
            value = json.loads(target.read_text("utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"unreadable corpus resource: {relative_path.as_posix()}") from exc
        if not isinstance(value, dict):
            raise ValueError("corpus resource must be a JSON object")
        return value

    @staticmethod
    def _judgment_id(value: str) -> str:
        if not isinstance(value, str) or not _SAFE_JUDGMENT_ID.fullmatch(value):
            raise ValueError("invalid judgment_id")
        return value

    @staticmethod
    def _search_result(unit: dict[str, Any], score: int) -> dict[str, Any]:
        issue = CorpusRepository._mapping(unit.get("issue"))
        holding = CorpusRepository._mapping(unit.get("holding"))
        facets = CorpusRepository._mapping(unit.get("facets"))
        return {
            "judgment_id": str(unit.get("judgment_id") or ""),
            "issue_id": str(issue.get("issue_id") or ""),
            "question": issue.get("question"),
            "conclusion": holding.get("conclusion"),
            "tax_years": facets.get("tax_years") or [],
            "countries": facets.get("countries") or [],
            "score": score,
        }

    @staticmethod
    def _mapping(value: object) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}
