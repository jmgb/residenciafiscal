"""Migra la procedencia del corpus solo si el nuevo extractor conserva cada página."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from collections.abc import Sequence
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from export_jurisprudence_sample import export_jurisprudence_document
from jurisprudence_case_derivative_artifacts import write_case_derivative
from jurisprudence_case_verbatim_validation import validate_case_artifact
from jurisprudence_retrieval_corpus import build_retrieval_corpus, render_retrieval_corpus
from jurisprudence_rollout import load_rollout_manifest, load_rollout_state, write_rollout_state
from jurisprudence_rollout_completion import _validate_artifact_hashes, finalize_rollout
from jurisprudence_rollout_models import RolloutExecutionStatus, RolloutManifest
from jurisprudence_sample_manifest import JurisprudenceSampleDocument, load_sample_manifest
from jurisprudence_sample_quality import build_sample_quality_report, render_sample_quality_report
from okf_provenance import sha256_file
from verbatim_artifact import load_verbatim_corpus
from verbatim_extraction import extract_verbatim_corpus

OUTPUT = Path("knowledge/jurisprudencia-v3")
MANIFEST = Path("sentencias/jurisprudence_v3_rollout_106.json")
SAMPLE = Path("sentencias/jurisprudence_v3_sample_5.json")
STATE = Path("output/jurisprudence-v3-rollout-state.json")
_HASH_FIELDS = ("case_sha256", "retrieval_sha256", "markdown_sha256", "verbatim_sha256")


@dataclass(frozen=True)
class MigrationResult:
    document_count: int
    page_count: int
    changed_file_count: int


def _render(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _copy_input(root: Path, stage: Path, relative: Path) -> None:
    source = (root / relative).resolve()
    if not source.is_relative_to(root) or not source.is_file():
        raise ValueError(f"entrada inexistente o fuera de project_root: {relative}")
    destination = stage / relative
    if not destination.resolve().is_relative_to(stage):
        raise ValueError(f"destino fuera de staging: {relative}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def _validate_manifest_inputs(root: Path, manifest: RolloutManifest) -> None:
    for document in manifest.documents:
        for field, resource in (
            ("source_sha256", document.source_file),
            ("proposal_sha256", document.proposal_path),
            ("evaluation_sha256", document.evaluation_path),
        ):
            source = (root / resource).resolve()
            if not source.is_relative_to(root) or not source.is_file():
                raise ValueError(f"entrada inexistente o fuera de project_root: {resource}")
            expected = getattr(document, field)
            if expected is not None and sha256_file(source) != expected:
                raise ValueError(f"{document.judgment_id}: {field} no coincide con el manifiesto")


def _compare_pages(root: Path, documents: tuple[JurisprudenceSampleDocument, ...]) -> int:
    page_count = 0
    for document in documents:
        artifact = root / OUTPUT / f"verbatim/{document.judgment_id}.pages.json"
        previous = load_verbatim_corpus(artifact.read_bytes())
        validate_case_artifact(
            root / OUTPUT / f"cases/{document.judgment_id}.case.json",
            verbatim_path=artifact,
            project_root=root,
        )
        current = extract_verbatim_corpus(
            root / document.source_file,
            document_id=document.judgment_id,
            source_file=document.source_file,
        )
        if previous.extractor.name != current.extractor.name:
            raise ValueError(f"{document.judgment_id}: cambia el nombre del extractor")
        if previous.page_count != current.page_count:
            raise ValueError(f"{document.judgment_id}: cambia el número de páginas")
        for old, new in zip(previous.pages, current.pages, strict=True):
            if old != new:
                raise ValueError(f"{document.judgment_id}: cambia la página {new.page_index}")
        if previous.model_copy(update={"extractor": current.extractor}) != current:
            raise ValueError(
                f"{document.judgment_id}: cambia la identidad o el estado del verbatim"
            )
        page_count += current.page_count
    return page_count


def _compare_case(previous: dict, current: dict) -> None:
    expected = deepcopy(previous)
    expected["judgment"]["extractor"] = current["judgment"]["extractor"]
    new_inputs = current["judgment"]["analysis_provenance"]["input_artifacts"]
    new_hash = next(item["sha256"] for item in new_inputs if item["kind"] == "VERBATIM")
    for item in expected["judgment"]["analysis_provenance"]["input_artifacts"]:
        if item["kind"] == "VERBATIM":
            item["sha256"] = new_hash
    if expected != current:
        raise ValueError(f"{current['judgment']['judgment_id']}: cambia el contenido jurídico")


def _compare_retrieval(previous: dict, current: dict) -> None:
    expected = deepcopy(previous)
    if "source" in expected:
        expected["source"]["case_sha256"] = current["source"]["case_sha256"]
    else:
        if len(expected["sources"]) != len(current["sources"]):
            raise ValueError("cambia el índice de recuperación: fuentes diferentes")
        for old, new in zip(expected["sources"], current["sources"], strict=True):
            old["index_sha256"] = new["index_sha256"]
    if expected != current:
        raise ValueError("cambia el índice de recuperación: solo se admiten nuevos hashes")


def _refresh_sample(stage: Path, records: dict[str, dict[str, object]]) -> None:
    sample = load_sample_manifest(stage / SAMPLE)
    path = stage / OUTPUT / "sample-build.json"
    build = json.loads(path.read_bytes())
    ids = {document.judgment_id for document in sample.documents}
    if (
        build["manifest_sha256"] != sha256_file(stage / SAMPLE)
        or build["sample_id"] != sample.sample_id
        or {item["judgment_id"] for item in build["documents"]} != ids
    ):
        raise ValueError("sample-build no corresponde a su manifiesto")
    for item in build["documents"]:
        item.update(records[item["judgment_id"]])
    write_case_derivative(_render(build), path)
    corpus = build_retrieval_corpus(
        tuple(stage / OUTPUT / f"retrieval/{d.judgment_id}.issues.json" for d in sample.documents),
        sample_id=sample.sample_id,
        project_root=stage,
    )
    quality = build_sample_quality_report(
        tuple(stage / OUTPUT / f"cases/{d.judgment_id}.case.json" for d in sample.documents),
        sample_id=sample.sample_id,
        project_root=stage,
    )
    write_case_derivative(render_retrieval_corpus(corpus), stage / OUTPUT / "retrieval/corpus.json")
    write_case_derivative(
        render_sample_quality_report(quality), stage / OUTPUT / "reports/sample-5.quality.json"
    )


def _publish(root: Path, stage: Path, before: dict[Path, bytes]) -> int:
    candidates = {
        p.relative_to(stage): p.read_bytes() for p in (stage / OUTPUT).rglob("*") if p.is_file()
    }
    candidates[STATE] = (stage / STATE).read_bytes()
    for relative in before.keys() | candidates.keys():
        destination = root / relative
        current = destination.read_bytes() if destination.exists() else None
        if current != before.get(relative):
            raise ValueError(f"el archivo cambió durante la migración: {relative}")
    changed = {p: data for p, data in candidates.items() if data != before.get(p)}
    published: list[Path] = []
    try:
        for relative, data in changed.items():
            write_case_derivative(data.decode("utf-8"), root / relative)
            published.append(relative)
    except BaseException:
        for relative in reversed(published):
            if relative in before:
                write_case_derivative(before[relative].decode("utf-8"), root / relative)
            else:
                (root / relative).unlink()
        raise
    return len(changed)


def _regenerate_documents(
    root: Path,
    stage: Path,
    documents: tuple[JurisprudenceSampleDocument, ...],
    before: dict[Path, bytes],
) -> dict[str, dict[str, object]]:
    records = {}
    for document in documents:
        proposal = json.loads((root / document.proposal_path).read_bytes())
        for resource in (document.source_file, document.proposal_path, document.evaluation_path):
            _copy_input(root, stage, Path(resource))
        for item in proposal["judgment"]["analysis_provenance"]["input_artifacts"]:
            _copy_input(root, stage, Path(item["source_path"]))
        records[document.judgment_id] = export_jurisprudence_document(
            document,
            output_root=stage / OUTPUT,
            project_root=stage,
        )
        relative = OUTPUT / f"cases/{document.judgment_id}.case.json"
        _compare_case(json.loads(before[relative]), json.loads((stage / relative).read_bytes()))
        relative = OUTPUT / f"retrieval/{document.judgment_id}.issues.json"
        _compare_retrieval(
            json.loads(before[relative]), json.loads((stage / relative).read_bytes())
        )
    return records


def migrate_pypdf(*, project_root: Path, check_only: bool = False) -> MigrationResult:
    """Compara todo el lote, regenera en staging y publica tras validar las fuentes."""
    root = project_root.resolve()
    manifest = load_rollout_manifest(root / MANIFEST)
    state = load_rollout_state(root / STATE)
    if (
        state.manifest_sha256 != sha256_file(root / MANIFEST)
        or tuple((d.judgment_id, d.batch_id, d.risk) for d in state.documents)
        != tuple((d.judgment_id, d.batch_id, d.risk) for d in manifest.documents)
        or any(d.execution_status != RolloutExecutionStatus.BUILD_PASSED for d in state.documents)
    ):
        raise ValueError("el estado no corresponde a un rollout completamente compilado")
    _validate_artifact_hashes(state, root / OUTPUT)
    _validate_manifest_inputs(root, manifest)
    documents = tuple(
        JurisprudenceSampleDocument.model_validate(
            d.model_dump(include=set(JurisprudenceSampleDocument.model_fields))
        )
        for d in manifest.documents
    )
    before = {
        p.relative_to(root): p.read_bytes() for p in (root / OUTPUT).rglob("*") if p.is_file()
    }
    before[STATE] = (root / STATE).read_bytes()
    page_count = _compare_pages(root, documents)
    if check_only:
        return MigrationResult(len(documents), page_count, 0)
    with tempfile.TemporaryDirectory(prefix="pypdf-migration-") as directory:
        stage = Path(directory).resolve()
        shutil.copytree(root / OUTPUT, stage / OUTPUT)
        for relative in (MANIFEST, SAMPLE, STATE):
            _copy_input(root, stage, relative)
        records = _regenerate_documents(root, stage, documents, before)
        state = state.model_copy(
            update={
                "documents": tuple(
                    d.model_copy(update={key: records[d.judgment_id][key] for key in _HASH_FIELDS})
                    for d in state.documents
                )
            }
        )
        write_rollout_state(state, stage / STATE)
        finalize_rollout(
            manifest_path=stage / MANIFEST,
            state_path=stage / STATE,
            output_root=stage / OUTPUT,
            project_root=stage,
        )
        _refresh_sample(stage, records)
        for name in ("corpus.json", f"rollout-{len(documents)}.corpus.json"):
            relative = OUTPUT / "retrieval" / name
            _compare_retrieval(
                json.loads(before[relative]), json.loads((stage / relative).read_bytes())
            )
        _validate_manifest_inputs(stage, manifest)
        _validate_manifest_inputs(root, manifest)
        for document in documents:
            validate_case_artifact(
                root / OUTPUT / f"cases/{document.judgment_id}.case.json",
                verbatim_path=root / OUTPUT / f"verbatim/{document.judgment_id}.pages.json",
                project_root=root,
            )
        changed = _publish(root, stage, before)
    return MigrationResult(len(documents), page_count, changed)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--check", action="store_true", help="Compara páginas sin publicar artefactos."
    )
    args = parser.parse_args(argv)
    result = migrate_pypdf(project_root=args.project_root, check_only=args.check)
    print(_render({**result.__dict__, "validation": "passed", "check_only": args.check}), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
