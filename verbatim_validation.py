"""Validación de un artefacto verbatim contra su PDF y extractor."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path

from okf_provenance import sha256_file
from verbatim_artifact import load_verbatim_corpus
from verbatim_extraction import ReaderFactory, extract_verbatim_corpus
from verbatim_models import VerbatimCorpusStatus


@dataclass(frozen=True)
class VerbatimValidationResult:
    document_id: str
    page_count: int
    status: VerbatimCorpusStatus
    source_sha256: str
    pages_sha256: str
    artifact_sha256: str


def _resolve_source(project_root: Path, source_file: str) -> Path:
    resolved_root = project_root.resolve()
    source_path = (resolved_root / source_file).resolve()
    if not source_path.is_relative_to(resolved_root):
        raise ValueError("source_file sale de project_root")
    if not source_path.is_file():
        raise ValueError(f"source_file no existe: {source_file}")
    return source_path


def validate_verbatim_artifact(
    artifact_path: Path,
    *,
    project_root: Path,
    reader_factory: ReaderFactory | None = None,
    extractor_version: str | None = None,
) -> VerbatimValidationResult:
    """Revalida hashes y reproduce la extracción completa desde el PDF."""

    corpus = load_verbatim_corpus(artifact_path.read_bytes())
    source_path = _resolve_source(project_root, corpus.source_file)
    if sha256_file(source_path) != corpus.source_sha256:
        raise ValueError("source_sha256 no coincide con el PDF actual")

    expected_extractor_version = extractor_version or version("pypdf")
    if corpus.extractor.name != "pypdf" or corpus.extractor.version != expected_extractor_version:
        raise ValueError("extractor no coincide con la versión de validación")

    if reader_factory is None:
        regenerated = extract_verbatim_corpus(
            source_path,
            document_id=corpus.document_id,
            source_file=corpus.source_file,
            extractor_version=expected_extractor_version,
        )
    else:
        regenerated = extract_verbatim_corpus(
            source_path,
            document_id=corpus.document_id,
            source_file=corpus.source_file,
            reader_factory=reader_factory,
            extractor_version=expected_extractor_version,
        )
    if regenerated != corpus:
        raise ValueError("la reextracción no reproduce el corpus verbatim")

    return VerbatimValidationResult(
        document_id=corpus.document_id,
        page_count=corpus.page_count,
        status=corpus.status,
        source_sha256=corpus.source_sha256,
        pages_sha256=corpus.pages_sha256,
        artifact_sha256=sha256_file(artifact_path),
    )
