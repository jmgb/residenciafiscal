"""Construcción y verificación del bundle C1 para el worker de investigación."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import zipfile
from pathlib import Path, PurePosixPath

from deep_research_contracts import DeepResearchBundleManifest
from jurisprudence_rollout import load_rollout_manifest
from okf_provenance import sha256_file

BUNDLE_MANIFEST_NAME = "MANIFEST.json"
BUNDLE_SCHEMA_VERSION = "residenciafiscal-deep-research-bundle/1"
CORPUS_PATH = Path("knowledge/jurisprudencia-v3/retrieval/rollout-106.corpus.json")
ARTIFACT_ROOT = Path("knowledge/jurisprudencia-v3")
ALLOWED_ARCHIVE_PREFIXES = (
    "cases/",
    "verbatim/",
    "retrieval/",
    "jurisdicciones/",
    "pdf/",
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
            (f"pdf/{document.judgment_id}.pdf", Path(document.source_file)),
        )
        for archive_path, relative_path in artifact_paths:
            if archive_path in seen_archive_paths:
                raise ValueError(f"ruta duplicada en el bundle: {archive_path}")
            source_path = (
                source
                if relative_path == Path(document.source_file)
                else _artifact_file(project_root, relative_path)
            )
            sources.append((archive_path, source_path))
            seen_archive_paths.add(archive_path)

    return sources


def _render_manifest(manifest: DeepResearchBundleManifest) -> bytes:
    return (
        json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
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
    source_manifest_relative = rollout_manifest_path.relative_to(project_root).as_posix()
    manifest = DeepResearchBundleManifest(
        schema_version=BUNDLE_SCHEMA_VERSION,
        bundle_id="rollout-106/1",
        source_manifest_path=source_manifest_relative,
        source_manifest_sha256=sha256_file(rollout_manifest_path),
        files=dict(sorted(file_hashes.items())),
        scope={
            "documents": len(rollout_manifest.documents),
            "cases": sum(path.startswith("cases/") for path in file_hashes),
            "verbatim": sum(path.startswith("verbatim/") for path in file_hashes),
            "retrieval_indexes": sum(path.startswith("retrieval/") for path in file_hashes),
            "jurisdiction_indexes": sum(path.startswith("jurisdicciones/") for path in file_hashes),
            "pdf": sum(path.startswith("pdf/") for path in file_hashes),
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
        default=Path("output/deep-research/rollout-106.bundle.zip"),
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
