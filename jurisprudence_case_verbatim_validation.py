"""Validación del caso v3 contra sus fuentes y corpus verbatim."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jurisprudence_case_artifact import load_jurisprudence_case
from jurisprudence_case_models import JurisprudenceCase
from jurisprudence_case_source import AnalysisInputKind
from okf_provenance import sha256_file
from verbatim_artifact import load_verbatim_corpus
from verbatim_models import VerbatimCorpus


@dataclass(frozen=True)
class CaseVerbatimValidationResult:
    judgment_id: str
    anchor_count: int
    fragment_count: int


@dataclass(frozen=True)
class CaseArtifactValidationResult:
    judgment_id: str
    anchor_count: int
    fragment_count: int
    input_artifact_count: int
    case_sha256: str
    verbatim_sha256: str


def validate_case_against_verbatim(
    case: JurisprudenceCase,
    verbatim: VerbatimCorpus,
) -> CaseVerbatimValidationResult:
    """Exige identidad documental y slices literales para todos los anclajes."""

    judgment = case.judgment
    expected_metadata = (
        (judgment.judgment_id, verbatim.document_id, "judgment_id"),
        (judgment.source_file, verbatim.source_file, "source_file"),
        (judgment.source_sha256, verbatim.source_sha256, "source_sha256"),
        (judgment.page_count, verbatim.page_count, "page_count"),
        (
            (judgment.extractor.name, judgment.extractor.version),
            (verbatim.extractor.name, verbatim.extractor.version),
            "extractor",
        ),
    )
    for actual, expected, field_name in expected_metadata:
        if actual != expected:
            raise ValueError(f"{field_name} del caso no coincide con el verbatim")

    pages = {page.page_index: page for page in verbatim.pages}
    fragment_count = 0
    for anchor in case.source_anchors:
        for fragment in anchor.fragments:
            fragment_count += 1
            page = pages.get(fragment.page_index)
            if page is None:
                raise ValueError(f"{anchor.anchor_id}: página inexistente")
            if fragment.printed_page != page.printed_page:
                raise ValueError(f"{anchor.anchor_id}: printed_page no coincide")
            extracted = page.raw_page_text[fragment.start_offset : fragment.end_offset]
            if extracted != fragment.verbatim_text:
                raise ValueError(f"{anchor.anchor_id}: el slice verbatim no coincide")

    return CaseVerbatimValidationResult(
        judgment_id=judgment.judgment_id,
        anchor_count=len(case.source_anchors),
        fragment_count=fragment_count,
    )


def _resolve_input(project_root: Path, source_path: str) -> Path:
    resolved_root = project_root.resolve()
    resolved_path = (resolved_root / source_path).resolve()
    if not resolved_path.is_relative_to(resolved_root):
        raise ValueError("input_artifacts contiene una ruta fuera de project_root")
    if not resolved_path.is_file():
        raise ValueError(f"input_artifacts no existe: {source_path}")
    return resolved_path


def validate_case_artifact(
    case_path: Path,
    *,
    verbatim_path: Path,
    project_root: Path,
) -> CaseArtifactValidationResult:
    """Valida el caso persistido, sus entradas y todos sus anclajes literales."""

    case = load_jurisprudence_case(case_path.read_bytes())
    verbatim = load_verbatim_corpus(verbatim_path.read_bytes())
    matched_verbatim = False
    for artifact in case.judgment.analysis_provenance.input_artifacts:
        input_path = _resolve_input(project_root, artifact.source_path)
        if sha256_file(input_path) != artifact.sha256:
            raise ValueError(f"input_artifacts hash no coincide: {artifact.source_path}")
        if artifact.kind == AnalysisInputKind.VERBATIM:
            matched_verbatim = input_path == verbatim_path.resolve()
    if not matched_verbatim:
        raise ValueError("input_artifacts no identifica el verbatim validado")

    literal_result = validate_case_against_verbatim(case, verbatim)
    return CaseArtifactValidationResult(
        judgment_id=literal_result.judgment_id,
        anchor_count=literal_result.anchor_count,
        fragment_count=literal_result.fragment_count,
        input_artifact_count=len(case.judgment.analysis_provenance.input_artifacts),
        case_sha256=sha256_file(case_path),
        verbatim_sha256=sha256_file(verbatim_path),
    )
