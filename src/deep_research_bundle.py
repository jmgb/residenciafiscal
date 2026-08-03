"""Construcción y verificación del bundle C1 para el worker de investigación."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from llm_gateway.models import CATALOG_VERSION, lookup_model

from deep_research_contracts import DeepResearchBundleManifest
from deep_research_policy import DEEP_RESEARCH_MODEL
from deep_research_verifier import load_model_pricing, validate_verbatim_integrity
from jurisprudence_rollout import load_rollout_manifest
from okf_provenance import sha256_file

BUNDLE_MANIFEST_NAME = "MANIFEST.json"
BUNDLE_SCHEMA_VERSION = "residenciafiscal-deep-research-bundle/2"
MODEL_PRICING_NAME = "metadata/model-pricing.json"
CORPUS_PATH = Path("knowledge/jurisprudencia-v3/retrieval/rollout-106.corpus.json")
ARTIFACT_ROOT = Path("knowledge/jurisprudencia-v3")
ALLOWED_ARCHIVE_PREFIXES = (
    "cases/",
    "verbatim/",
    "retrieval/",
    "jurisdicciones/",
    "metadata/",
)


def _safe_project_file(
    project_root: Path,
    relative_path: str,
    *,
    required_root: Path | None = None,
) -> Path:
    portable = PurePosixPath(relative_path)
    if portable.is_absolute() or ".." in portable.parts or "\\" in relative_path:
        raise ValueError(f"ruta no portable en el manifiesto: {relative_path}")
    candidate = (project_root / Path(*portable.parts)).resolve()
    root = project_root.resolve()
    if not candidate.is_relative_to(root):
        raise ValueError(f"ruta fuera del proyecto: {relative_path}")
    if required_root is not None and not candidate.is_relative_to(
        (project_root / required_root).resolve()
    ):
        raise ValueError(f"ruta fuera de la allowlist: {relative_path}")
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    return candidate


def _artifact_file(project_root: Path, relative_path: Path) -> Path:
    return _safe_project_file(project_root, relative_path.as_posix(), required_root=ARTIFACT_ROOT)


def _validate_verbatim_binding(path: Path, judgment_id: str, source_sha256: str) -> None:
    try:
        document = json.loads(path.read_text("utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"verbatim inválido: {judgment_id}") from exc
    validate_verbatim_integrity(document)
    if (
        not isinstance(document, dict)
        or document.get("document_id") != judgment_id
        or document.get("source_sha256") != source_sha256
    ):
        raise ValueError(f"verbatim no vinculado a la fuente canónica: {judgment_id}")


def _canonical_sources(
    project_root: Path,
    rollout_manifest_path: Path,
) -> list[tuple[str, Path]]:
    manifest = load_rollout_manifest(rollout_manifest_path)
    if (
        rollout_manifest_path.resolve()
        != (project_root / "sentencias/jurisprudence_v3_rollout_106.json").resolve()
    ):
        raise ValueError("el bundle exige el manifiesto de rollout canónico")

    sources: list[tuple[str, Path]] = [
        (
            "metadata/rollout-manifest.json",
            _safe_project_file(
                project_root,
                "sentencias/jurisprudence_v3_rollout_106.json",
                required_root=Path("sentencias"),
            ),
        ),
        ("retrieval/rollout-106.corpus.json", _artifact_file(project_root, CORPUS_PATH)),
    ]
    seen_archive_paths = {archive_path for archive_path, _ in sources}
    for document in manifest.documents:
        source = _safe_project_file(
            project_root,
            document.source_file,
            required_root=Path("sentencias"),
        )
        if source.suffix.lower() != ".pdf":
            raise ValueError(f"la fuente no es PDF: {document.source_file}")
        if sha256_file(source) != document.source_sha256:
            raise ValueError(f"hash de PDF no coincide: {document.judgment_id}")

        artifact_paths = (
            (
                f"cases/{document.judgment_id}.case.json",
                ARTIFACT_ROOT / "cases" / f"{document.judgment_id}.case.json",
            ),
            (
                f"verbatim/{document.judgment_id}.pages.json",
                ARTIFACT_ROOT / "verbatim" / f"{document.judgment_id}.pages.json",
            ),
            (
                f"retrieval/{document.judgment_id}.issues.json",
                ARTIFACT_ROOT / "retrieval" / f"{document.judgment_id}.issues.json",
            ),
            (
                f"jurisdicciones/{document.judgment_id}.roles.json",
                ARTIFACT_ROOT / "jurisdicciones" / f"{document.judgment_id}.roles.json",
            ),
        )
        for archive_path, relative_path in artifact_paths:
            if archive_path in seen_archive_paths:
                raise ValueError(f"ruta duplicada en el bundle: {archive_path}")
            source_path = (
                source
                if relative_path == Path(document.source_file)
                else _artifact_file(project_root, relative_path)
            )
            if archive_path.startswith("verbatim/"):
                _validate_verbatim_binding(
                    source_path, document.judgment_id, document.source_sha256
                )
            sources.append((archive_path, source_path))
            seen_archive_paths.add(archive_path)

    return sources


def _render_manifest(manifest: DeepResearchBundleManifest) -> bytes:
    return (
        json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")


def _render_model_pricing() -> bytes:
    model = lookup_model(DEEP_RESEARCH_MODEL)
    if model is None:
        raise ValueError(f"modelo ausente del catálogo compartido: {DEEP_RESEARCH_MODEL}")
    return (
        json.dumps(
            {
                "schema_version": "residenciafiscal-model-pricing/1",
                "catalog_version": CATALOG_VERSION,
                "model": DEEP_RESEARCH_MODEL,
                "input_usd_per_mtok": str(model.input_usd_per_mtok),
                "output_usd_per_mtok": str(model.output_usd_per_mtok),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def build_deep_research_bundle(
    *,
    project_root: Path,
    rollout_manifest_path: Path,
    output_path: Path,
) -> dict[str, object]:
    """Crea un ZIP determinista y no sobrescribe snapshots existentes."""

    project_root = project_root.resolve()
    rollout_manifest_path = rollout_manifest_path.resolve()
    if output_path.exists():
        raise FileExistsError(output_path)
    rollout_manifest = load_rollout_manifest(rollout_manifest_path)
    sources = _canonical_sources(project_root, rollout_manifest_path)
    file_hashes = {archive_path: sha256_file(source_path) for archive_path, source_path in sources}
    generated_files = {MODEL_PRICING_NAME: _render_model_pricing()}
    file_hashes.update(
        {
            archive_path: hashlib.sha256(payload).hexdigest()
            for archive_path, payload in generated_files.items()
        }
    )
    source_manifest_relative = rollout_manifest_path.relative_to(project_root).as_posix()
    manifest = DeepResearchBundleManifest(
        schema_version=BUNDLE_SCHEMA_VERSION,
        bundle_id="rollout-106/2",
        source_manifest_path=source_manifest_relative,
        source_manifest_sha256=sha256_file(rollout_manifest_path),
        files=dict(sorted(file_hashes.items())),
        scope={
            "documents": len(rollout_manifest.documents),
            "cases": sum(path.startswith("cases/") for path in file_hashes),
            "verbatim": sum(path.startswith("verbatim/") for path in file_hashes),
            "retrieval_indexes": sum(path.startswith("retrieval/") for path in file_hashes),
            "jurisdiction_indexes": sum(path.startswith("jurisdicciones/") for path in file_hashes),
            "format": "json-only",
            "pricing_version": CATALOG_VERSION,
        },
    )
    manifest_bytes = _render_manifest(manifest)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    created_output = False
    try:
        with output_path.open("xb") as raw_output:
            created_output = True
            with zipfile.ZipFile(
                raw_output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
            ) as archive:
                archive.writestr(_zip_info(BUNDLE_MANIFEST_NAME), manifest_bytes)
                for archive_path, source_path in sorted(sources):
                    archive.writestr(_zip_info(archive_path), source_path.read_bytes())
                for archive_path, payload in sorted(generated_files.items()):
                    archive.writestr(_zip_info(archive_path), payload)
    except Exception:
        if created_output:
            output_path.unlink(missing_ok=True)
        raise
    return manifest.model_dump(mode="json")


def _validate_archive_path(path: str) -> None:
    portable = PurePosixPath(path)
    if (
        portable.is_absolute()
        or ".." in portable.parts
        or "\\" in path
        or not path.startswith(ALLOWED_ARCHIVE_PREFIXES)
    ):
        raise ValueError(f"ruta no permitida en el bundle: {path}")


def _validate_archived_verbatim_bindings(archive: zipfile.ZipFile) -> None:
    try:
        rollout = json.loads(archive.read("metadata/rollout-manifest.json"))
    except (KeyError, json.JSONDecodeError) as exc:
        raise ValueError("rollout manifest inválido en el bundle") from exc
    documents = rollout.get("documents") if isinstance(rollout, dict) else None
    if not isinstance(documents, list):
        raise ValueError("rollout manifest inválido en el bundle")
    expected_verbatim: set[str] = set()
    for entry in documents:
        if not isinstance(entry, dict):
            raise ValueError("rollout manifest inválido en el bundle")
        judgment_id = entry.get("judgment_id")
        source_sha256 = entry.get("source_sha256")
        if not isinstance(judgment_id, str) or not isinstance(source_sha256, str):
            raise ValueError("rollout manifest inválido en el bundle")
        name = f"verbatim/{judgment_id}.pages.json"
        expected_verbatim.add(name)
        try:
            verbatim = json.loads(archive.read(name))
        except (KeyError, json.JSONDecodeError) as exc:
            raise ValueError(f"verbatim inválido en el bundle: {judgment_id}") from exc
        validate_verbatim_integrity(verbatim)
        if (
            verbatim.get("document_id") != judgment_id
            or verbatim.get("source_sha256") != source_sha256
        ):
            raise ValueError(f"verbatim no vinculado al rollout: {judgment_id}")
    actual_verbatim = {
        name
        for name in archive.namelist()
        if name.startswith("verbatim/") and name.endswith(".json")
    }
    if actual_verbatim != expected_verbatim:
        raise ValueError("el conjunto verbatim no coincide con el rollout")


def _validate_archived_pricing(archive: zipfile.ZipFile) -> None:
    with tempfile.TemporaryDirectory(prefix="deep-research-pricing-") as directory:
        root = Path(directory)
        pricing_path = root / MODEL_PRICING_NAME
        pricing_path.parent.mkdir(parents=True)
        try:
            pricing_path.write_bytes(archive.read(MODEL_PRICING_NAME))
        except KeyError as exc:
            raise ValueError("falta pricing versionado en el bundle") from exc
        load_model_pricing(root, DEEP_RESEARCH_MODEL)


def verify_deep_research_bundle(bundle_path: Path) -> dict[str, object]:
    """Comprueba allowlist, entradas exactas y hashes de un snapshot."""

    with zipfile.ZipFile(bundle_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("el bundle contiene entradas duplicadas")
        if BUNDLE_MANIFEST_NAME not in names:
            raise ValueError("falta MANIFEST.json")
        manifest = DeepResearchBundleManifest.model_validate_json(
            archive.read(BUNDLE_MANIFEST_NAME)
        )
        expected_names = {BUNDLE_MANIFEST_NAME, *manifest.files}
        if set(names) != expected_names:
            raise ValueError("las entradas del bundle no coinciden con MANIFEST.json")
        for info in archive.infolist():
            mode = info.external_attr >> 16
            if mode and (stat.S_ISDIR(mode) or stat.S_ISLNK(mode)):
                raise ValueError(f"entrada no regular en el bundle: {info.filename}")
        for relative_path, expected_sha256 in manifest.files.items():
            _validate_archive_path(relative_path)
            actual_sha256 = hashlib.sha256(archive.read(relative_path)).hexdigest()
            if actual_sha256 != expected_sha256:
                raise ValueError(f"hash no coincide: {relative_path}")
        _validate_archived_verbatim_bindings(archive)
        _validate_archived_pricing(archive)
        return manifest.model_dump(mode="json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--project-root", type=Path, default=Path("."))
    build.add_argument(
        "--rollout-manifest",
        type=Path,
        default=Path("sentencias/jurisprudence_v3_rollout_106.json"),
    )
    build.add_argument(
        "--output",
        type=Path,
        default=Path("output/deep-research/rollout-106-v2.bundle.zip"),
    )
    verify = subparsers.add_parser("verify")
    verify.add_argument("bundle", type=Path)
    arguments = parser.parse_args(argv)
    if arguments.command == "build":
        result = build_deep_research_bundle(
            project_root=arguments.project_root,
            rollout_manifest_path=arguments.rollout_manifest,
            output_path=arguments.output,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    result = verify_deep_research_bundle(arguments.bundle)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
