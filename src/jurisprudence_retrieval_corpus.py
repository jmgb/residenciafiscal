"""Corpus agregado y baseline léxico determinista para jurisprudencia v3."""

from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from jurisprudence_case_retrieval import load_retrieval_index
from jurisprudence_case_retrieval_models import RetrievalUnit
from jurisprudence_retrieval_corpus_models import (
    RetrievalCorpus,
    RetrievalCorpusSource,
)
from okf_provenance import sha256_file

_TOKEN = re.compile(r"[a-z0-9]+")
_JUDGMENT_IDENTIFIER = re.compile(r"\b(san|sts)\s*[- ]?\s*(\d+)\s*[/_-]\s*(\d{4})\b", re.I)
_STOPWORDS = {
    "a",
    "al",
    "como",
    "con",
    "de",
    "del",
    "el",
    "en",
    "es",
    "la",
    "las",
    "lo",
    "los",
    "me",
    "mi",
    "para",
    "por",
    "que",
    "se",
    "si",
    "su",
    "un",
    "una",
    "y",
}
_EXPANSIONS = {
    "hacienda": ("aeat", "administracion"),
    "demostrar": ("prueba", "indicios", "acreditar"),
    "pruebas": ("prueba", "evidencia", "indicios"),
    "dias": ("presencia", "permanencia", "desplazamientos"),
    "familia": ("conyuge", "hijos", "familiar"),
    "vivienda": ("domicilio", "inmueble", "ocupacion"),
    "ingresos": ("rentas", "economicos", "actividad"),
    "extranjero": ("exterior", "fiscal", "certificado"),
    "certificado": ("documentacion", "fiscal", "extranjera"),
    "sancion": ("culpabilidad", "infraccion"),
}


@dataclass(frozen=True)
class RetrievalHit:
    unit_id: str
    judgment_id: str
    score: float


def _relative_resource(path: Path, project_root: Path) -> str:
    resolved = path.resolve()
    root = project_root.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"índice fuera de project_root: {path}")
    return resolved.relative_to(root).as_posix()


def build_retrieval_corpus(
    index_paths: tuple[Path, ...],
    *,
    sample_id: str,
    project_root: Path,
) -> RetrievalCorpus:
    """Valida y agrega índices por sentencia en el orden recibido."""

    sources: list[RetrievalCorpusSource] = []
    units: list[RetrievalUnit] = []
    for path in index_paths:
        index = load_retrieval_index(path.read_bytes())
        sources.append(
            RetrievalCorpusSource(
                judgment_id=index.judgment.judgment_id,
                index_resource=_relative_resource(path, project_root),
                index_sha256=sha256_file(path),
            )
        )
        if index.judgment.is_tax_residence_case:
            units.extend(index.units)
    return RetrievalCorpus(
        schema_version="residenciafiscal-retrieval-corpus/1",
        sample_id=sample_id,
        sources=tuple(sources),
        units=tuple(units),
    )


def render_retrieval_corpus(corpus: RetrievalCorpus) -> str:
    return (
        json.dumps(
            corpus.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def load_retrieval_corpus(serialized: str | bytes) -> RetrievalCorpus:
    return RetrievalCorpus.model_validate_json(serialized)


def _tokens(text: str, *, expand: bool = False) -> tuple[str, ...]:
    folded = unicodedata.normalize("NFKD", text.lower())
    normalized = "".join(char for char in folded if not unicodedata.combining(char))
    tokens = [item for item in _TOKEN.findall(normalized) if item not in _STOPWORDS]
    if expand:
        tokens.extend(synonym for token in tuple(tokens) for synonym in _EXPANSIONS.get(token, ()))
    return tuple(tokens)


def _judgment_identifiers(text: str) -> frozenset[str]:
    """Normaliza referencias como ``SAN 2132/2025`` al identificador interno."""

    return frozenset(
        f"{court.lower()}-{number}-{year}"
        for court, number, year in _JUDGMENT_IDENTIFIER.findall(text)
    )


def rank_retrieval_units(
    corpus: RetrievalCorpus,
    query: str,
    *,
    limit: int = 12,
) -> tuple[RetrievalHit, ...]:
    """Ordena unidades con BM25 y coincidencia explícita de identificador."""

    if limit < 1:
        raise ValueError("limit debe ser positivo")
    documents = tuple(
        Counter(_tokens(f"{unit.judgment_id}\n{unit.search_text}")) for unit in corpus.units
    )
    document_frequency = Counter(token for document in documents for token in document.keys())
    query_counts = Counter(_tokens(query, expand=True))
    total = len(documents)
    if total == 0:
        return ()
    document_lengths = tuple(sum(document.values()) for document in documents)
    average_document_length = sum(document_lengths) / total
    query_identifiers = _judgment_identifiers(query)
    k1 = 1.2
    b = 0.75
    hits = []
    for unit, document, document_length in zip(
        corpus.units, documents, document_lengths, strict=True
    ):
        score = sum(
            query_frequency
            * math.log(
                1
                + (total - document_frequency.get(token, 0) + 0.5)
                / (document_frequency.get(token, 0) + 0.5)
            )
            * (
                document.get(token, 0)
                * (k1 + 1)
                / (
                    document.get(token, 0)
                    + k1 * (1 - b + b * document_length / max(average_document_length, 1))
                )
            )
            for token, query_frequency in query_counts.items()
            if document.get(token, 0)
        )
        if unit.judgment_id in query_identifiers:
            score += 100.0
        hits.append(
            RetrievalHit(
                unit_id=unit.unit_id,
                judgment_id=unit.judgment_id,
                score=round(score, 8),
            )
        )
    return tuple(sorted(hits, key=lambda item: (-item.score, item.unit_id))[:limit])
