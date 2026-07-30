"""Validación de hashes y cardinalidad del manifiesto OKF."""

from __future__ import annotations

import json
from pathlib import Path

from okf_provenance import sha256_file


def _validate_hashed_resources(
    *,
    bundle_dir: Path,
    manifest_path: Path,
    resources: object,
    label: str,
    hash_error: str,
    issues: list[str],
) -> None:
    if not isinstance(resources, list):
        issues.append(f"{manifest_path}: {label} debe ser una lista")
        return
    for resource in resources:
        if not isinstance(resource, dict):
            issues.append(f"{manifest_path}: {label} contiene un elemento inválido")
            continue
        resource_path = bundle_dir / str(resource.get("path", ""))
        if not resource_path.is_file():
            issues.append(f"{manifest_path}: {label} inexistente {resource_path}")
        elif sha256_file(resource_path) != resource.get("sha256"):
            issues.append(f"{manifest_path}: {hash_error}")


def _validate_analysis_records(
    bundle_dir: Path,
    manifest_path: Path,
    manifest: dict[str, object],
    issues: list[str],
) -> None:
    schema_version = manifest.get("schema_version")
    if schema_version == "residenciafiscal-okf-manifest/2":
        record = manifest.get("analysis_record")
        resources = [record] if isinstance(record, dict) else record
    elif schema_version == "residenciafiscal-okf-manifest/3":
        resources = manifest.get("analysis_records")
    else:
        issues.append(f"{manifest_path}: schema_version no soportada")
        return
    _validate_hashed_resources(
        bundle_dir=bundle_dir,
        manifest_path=manifest_path,
        resources=resources,
        label="registro de análisis",
        hash_error="hash del registro de análisis no coincide",
        issues=issues,
    )


def _validate_annotation_sources(
    bundle_dir: Path,
    manifest_path: Path,
    manifest: dict[str, object],
    issues: list[str],
) -> None:
    if manifest.get("schema_version") == "residenciafiscal-okf-manifest/2":
        source = manifest.get("annotations_source")
        if source is None:
            return
        resources = [source] if isinstance(source, dict) else source
    else:
        resources = manifest.get("annotations_sources")
    _validate_hashed_resources(
        bundle_dir=bundle_dir,
        manifest_path=manifest_path,
        resources=resources,
        label="anotaciones",
        hash_error="hash de anotaciones no coincide",
        issues=issues,
    )


def validate_manifest(
    bundle_dir: Path,
    concept_count: int,
    issues: list[str],
) -> None:
    """Comprueba el manifiesto y sus recursos locales o enlazados."""

    manifest_path = bundle_dir / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        issues.append(f"{manifest_path}: {exc}")
        return
    if manifest.get("okf_version") != "0.2":
        issues.append(f"{manifest_path}: okf_version debe ser 0.2")
    documents = manifest.get("documents")
    if not isinstance(documents, list):
        issues.append(f"{manifest_path}: documents debe ser una lista")
        return
    scope = manifest.get("scope")
    declared_count = scope.get("documents") if isinstance(scope, dict) else None
    if declared_count != len(documents) or declared_count != concept_count:
        issues.append(f"{manifest_path}: cardinalidad incoherente")
    _validate_analysis_records(bundle_dir, manifest_path, manifest, issues)
    _validate_annotation_sources(bundle_dir, manifest_path, manifest, issues)
    for document in documents:
        if not isinstance(document, dict):
            issues.append(f"{manifest_path}: documento inválido")
            continue
        document_path = bundle_dir / str(document.get("path", ""))
        if not document_path.is_file():
            issues.append(f"{manifest_path}: documento inexistente {document_path}")
        elif sha256_file(document_path) != document.get("sha256"):
            issues.append(f"{manifest_path}: hash de documento no coincide")
        report = document.get("verification_report")
        if not isinstance(report, dict):
            issues.append(f"{manifest_path}: informe de verificación inválido")
            continue
        report_path = bundle_dir / str(report.get("path", ""))
        if not report_path.is_file():
            issues.append(f"{manifest_path}: informe de verificación inexistente")
        elif sha256_file(report_path) != report.get("sha256"):
            issues.append(f"{manifest_path}: hash del informe de verificación no coincide")
