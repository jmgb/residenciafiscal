"""Lectura acotada del bundle JSON de jurisprudencia para el perfil Codex."""

from __future__ import annotations

import json
import math
import re
import unicodedata
from pathlib import Path
from typing import Any

_SAFE_JUDGMENT_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
_MAX_QUERY_CHARS = 500
_MAX_RESULTS = 6
_SEARCH_STOPWORDS = {
    "como",
    "con",
    "cual",
    "cuando",
    "del",
    "desde",
    "donde",
    "el",
    "ella",
    "en",
    "entre",
    "ese",
    "esta",
    "este",
    "hay",
    "las",
    "los",
    "para",
    "pero",
    "por",
    "que",
    "sin",
    "sobre",
    "sus",
    "tiene",
    "una",
    "uno",
}
_SEARCH_EXPANSIONS = {
    "probatorio": {"acreditar", "habil", "presumida", "probar", "prueba", "validez"},
    "certificado": {"certificacion", "rechazar", "prescindir"},
}


class CorpusRepository:
    """Expone operaciones jurídicas concretas, nunca acceso genérico a ficheros."""

    def __init__(self, bundle_path: Path) -> None:
        self.bundle_path = bundle_path.resolve()
        if not self.bundle_path.is_dir():
            raise ValueError("bundle directory does not exist")

    def search(self, query: str, *, limit: int = 6) -> dict[str, Any]:
        query = query.strip()
        if not 1 <= len(query) <= _MAX_QUERY_CHARS:
            raise ValueError("query must contain between 1 and 500 characters")
        if not 1 <= limit <= _MAX_RESULTS:
            raise ValueError("limit must be between 1 and 6")
        normalized_query = self._normalize(query)
        query_tokens = set(self._tokens(query))
        if not query_tokens:
            raise ValueError("query must contain at least one searchable token")
        tokens = query_tokens | {
            expanded for token in query_tokens for expanded in _SEARCH_EXPANSIONS.get(token, set())
        }
        corpus = self._read_json(Path("retrieval/rollout-106.corpus.json"))
        units = corpus.get("units") if isinstance(corpus, dict) else None
        if not isinstance(units, list):
            raise ValueError("invalid retrieval corpus")
        document_frequency = {
            token: sum(
                token in set(self._tokens(str(unit.get("search_text") or "")))
                for unit in units
                if isinstance(unit, dict)
            )
            for token in tokens
        }
        ranked: list[tuple[int, dict[str, Any]]] = []
        for unit in units:
            if not isinstance(unit, dict):
                continue
            score = self._score_unit(
                unit,
                tokens=tokens,
                normalized_query=normalized_query,
                document_frequency=document_frequency,
                document_count=len(units),
            )
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

    @staticmethod
    def _normalize(value: str) -> str:
        decomposed = unicodedata.normalize("NFKD", value.casefold())
        return "".join(
            character for character in decomposed if not unicodedata.combining(character)
        )

    @classmethod
    def _tokens(cls, value: str) -> list[str]:
        return [
            cls._lexeme(token)
            for token in re.findall(r"\w+", cls._normalize(value))
            if len(token) > 2 and token not in _SEARCH_STOPWORDS
        ]

    @staticmethod
    def _lexeme(token: str) -> str:
        if token.endswith("es") and len(token) > 5:
            return token[:-2]
        if token.endswith("s") and len(token) > 4:
            return token[:-1]
        return token

    @classmethod
    def _score_unit(
        cls,
        unit: dict[str, Any],
        *,
        tokens: set[str],
        normalized_query: str,
        document_frequency: dict[str, int],
        document_count: int,
    ) -> int:
        issue = cls._mapping(unit.get("issue"))
        holding = cls._mapping(unit.get("holding"))
        facets = cls._mapping(unit.get("facets"))
        fields = (
            (str(issue.get("question") or ""), 4, 1),
            (str(holding.get("conclusion") or ""), 7, 2),
            (json.dumps(facets, ensure_ascii=False), 2, 2),
            (str(unit.get("search_text") or ""), 1, 3),
        )
        score = 0.0
        for text, weight, frequency_cap in fields:
            field_tokens = cls._tokens(text)
            for token in tokens:
                frequency = min(field_tokens.count(token), frequency_cap)
                if not frequency:
                    continue
                inverse_frequency = (
                    math.log((document_count + 1) / (document_frequency.get(token, 0) + 1)) + 1
                )
                score += weight * frequency * inverse_frequency
        searchable = cls._normalize(str(unit.get("search_text") or ""))
        if normalized_query in searchable:
            score += 10
        judgment_id = str(unit.get("judgment_id") or "")
        if score and judgment_id.startswith("sts-"):
            score += 8
        year_match = re.search(r"-(\d{4})$", judgment_id)
        if score and year_match:
            score += max(0, int(year_match.group(1)) - 2017)
        return max(0, round(score * 100))
