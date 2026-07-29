"""Validación estructural y de procedencia de bundles OKF jurisprudenciales."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import cast

import yaml

_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
_REQUIRED_SECTIONS = {
    "# Cuestión jurídica",
    "# Pruebas valoradas",
    "# Razonamiento y ratio decidendi",
    "# Fallo",
    "# Citas literales verificadas",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _parse_frontmatter(path: Path) -> tuple[dict[str, object], str]:
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        raise ValueError("frontmatter ausente")
    _, raw_frontmatter, body = content.split("---", 2)
    parsed = yaml.safe_load(raw_frontmatter)
    if not isinstance(parsed, dict):
        raise ValueError("frontmatter YAML no es un objeto")
    return cast(dict[str, object], parsed), body


def _validate_links(path: Path, body: str, issues: list[str]) -> None:
    for target in _LINK_RE.findall(body):
        if "://" in target or target.startswith("#"):
            continue
        resolved = (path.parent / target).resolve()
        if resolved.is_dir():
            resolved = resolved / "index.md"
        if not resolved.exists():
            issues.append(f"{path}: enlace roto {target}")


def _validate_concept(path: Path, issues: list[str]) -> None:
    try:
        frontmatter, body = _parse_frontmatter(path)
    except (ValueError, yaml.YAMLError) as exc:
        issues.append(f"{path}: {exc}")
        return
    concept_type = frontmatter.get("type")
    if not isinstance(concept_type, str) or not concept_type.strip():
        issues.append(f"{path}: type ausente")
    for section in sorted(_REQUIRED_SECTIONS):
        if section not in body:
            issues.append(f"{path}: sección ausente {section}")
    resource = frontmatter.get("resource")
    if isinstance(resource, str) and "://" not in resource:
        resolved_resource = (path.parent / resource).resolve()
        if not resolved_resource.is_file():
            issues.append(f"{path}: resource inexistente {resource}")
        elif _sha256(resolved_resource) != frontmatter.get("source_sha256"):
            issues.append(f"{path}: source_sha256 no coincide")
    _validate_links(path, body, issues)


def _validate_indexes(bundle_dir: Path, issues: list[str]) -> None:
    root_index = bundle_dir / "index.md"
    try:
        frontmatter, body = _parse_frontmatter(root_index)
    except (ValueError, yaml.YAMLError) as exc:
        issues.append(f"{root_index}: {exc}")
    else:
        if frontmatter != {"okf_version": "0.2"}:
            issues.append(f"{root_index}: okf_version debe ser 0.2")
        _validate_links(root_index, body, issues)

    for index_path in bundle_dir.rglob("index.md"):
        if index_path == root_index:
            continue
        body = index_path.read_text(encoding="utf-8")
        if body.startswith("---\n"):
            issues.append(f"{index_path}: un índice no raíz no lleva frontmatter")
        _validate_links(index_path, body, issues)


def _validate_manifest(bundle_dir: Path, issues: list[str]) -> None:
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
    if manifest.get("scope", {}).get("documents") != len(documents):
        issues.append(f"{manifest_path}: cardinalidad incoherente")
    for document in documents:
        if not isinstance(document, dict):
            issues.append(f"{manifest_path}: documento inválido")
            continue
        document_path = bundle_dir / str(document.get("path", ""))
        if not document_path.is_file():
            issues.append(f"{manifest_path}: documento inexistente {document_path}")
        elif _sha256(document_path) != document.get("sha256"):
            issues.append(f"{manifest_path}: hash de documento no coincide")


def validate_okf_bundle(bundle_dir: Path) -> tuple[str, ...]:
    """Devuelve incidencias de conformidad OKF, enlaces, secciones y hashes."""

    issues: list[str] = []
    _validate_indexes(bundle_dir, issues)
    concept_paths = tuple(
        path for path in bundle_dir.rglob("*.md") if path.name not in {"index.md", "log.md"}
    )
    if not concept_paths:
        issues.append(f"{bundle_dir}: no contiene conceptos")
    for concept_path in concept_paths:
        _validate_concept(concept_path, issues)
    _validate_manifest(bundle_dir, issues)
    return tuple(issues)
