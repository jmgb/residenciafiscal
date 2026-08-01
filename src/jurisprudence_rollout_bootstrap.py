"""Preparación explícita de insumos para el rollout jurisprudencial."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from export_verbatim import export_verbatim_document
from jurisprudence_case_derivative_artifacts import write_case_derivative
from jurisprudence_legacy_draft import build_legacy_case_draft
from jurisprudence_rollout_models import RolloutManifest
from okf_provenance import sha256_file
from verbatim_artifact import load_verbatim_corpus


@dataclass(frozen=True)
class BootstrapResult:
    generated_documents: tuple[str, ...]
    preserved_documents: tuple[str, ...]
    manifest_path: Path


def _load_records(path: Path) -> tuple[dict[str, object], ...]:
    records = tuple(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines())
    source_files = tuple(item.get("archivo") for item in records)
    if any(not isinstance(item, str) for item in source_files):
        raise ValueError("todos los registros deben declarar archivo")
    if len(source_files) != len(set(source_files)):
        raise ValueError("el análisis legado contiene archivos duplicados")
    return tuple(sorted(records, key=lambda item: str(item["archivo"])))


def _relative(path: Path, project_root: Path) -> str:
    resolved = path.resolve()
    root = project_root.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"ruta fuera de project_root: {path}")
    return resolved.relative_to(root).as_posix()


def _judgment_id(source_file: str) -> str:
    return source_file.removesuffix(".pdf").lower().replace("_", "-")


def _risk(record: dict[str, object]) -> str:
    high_risk = (
        record.get("confianza_extraccion") == "MEDIA"
        or record.get("se_invoca_CDI") == "SI"
        or record.get("resultado_final") in {"PARCIAL", "RETROACCION"}
    )
    return "HIGH" if high_risk else "STANDARD"


def _render(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _is_bootstrap_proposal(path: Path) -> bool:
    if not path.is_file():
        return False
    payload = json.loads(path.read_text(encoding="utf-8"))
    judgment = payload.get("judgment")
    provenance = judgment.get("analysis_provenance") if isinstance(judgment, dict) else None
    return isinstance(provenance, dict) and provenance.get("producer") == (
        "residenciafiscal-legacy-bootstrap"
    )


def _prepare_document(
    record: dict[str, object],
    *,
    legacy_path: Path,
    output_root: Path,
    project_root: Path,
    generated_at: datetime,
) -> tuple[dict[str, object], bool]:
    source_name = str(record["archivo"])
    judgment_id = _judgment_id(source_name)
    source = project_root / "sentencias" / source_name
    proposal = project_root / f"knowledge/jurisprudence-case-proposals/{judgment_id}.proposal.json"
    evaluation = output_root / f"evaluations/{judgment_id}.questions.json"
    verbatim = output_root / f"verbatim/{judgment_id}.pages.json"
    if not source.is_file():
        raise ValueError(f"PDF inexistente: {source_name}")
    if proposal.is_file() != evaluation.is_file():
        raise ValueError(f"{judgment_id}: propuesta y evaluación deben existir juntas")
    preserved = proposal.is_file() and not _is_bootstrap_proposal(proposal)
    if not verbatim.is_file():
        export_verbatim_document(
            pdf_path=source,
            document_id=judgment_id,
            source_file=f"sentencias/{source_name}",
            output_path=verbatim,
            project_root=project_root,
        )
    if not preserved:
        draft = build_legacy_case_draft(
            record,
            verbatim=load_verbatim_corpus(verbatim.read_bytes()),
            verbatim_resource=_relative(verbatim, project_root),
            legacy_resource=_relative(legacy_path, project_root),
            generated_at=generated_at,
        )
        write_case_derivative(_render(draft.proposal), proposal)
        write_case_derivative(_render(draft.evaluation), evaluation)
    return (
        {
            "judgment_id": judgment_id,
            "source_file": f"sentencias/{source_name}",
            "source_sha256": sha256_file(source),
            "proposal_path": _relative(proposal, project_root),
            "proposal_sha256": sha256_file(proposal),
            "evaluation_path": _relative(evaluation, project_root),
            "evaluation_sha256": sha256_file(evaluation),
            "risk": _risk(record),
        },
        preserved,
    )


def bootstrap_rollout_inputs(
    *,
    legacy_path: Path,
    manifest_path: Path,
    output_root: Path,
    project_root: Path,
    generated_at: datetime,
    batch_size: int,
) -> BootstrapResult:
    """Materializa entradas faltantes y congela un manifiesto validado."""

    if batch_size < 1:
        raise ValueError("batch_size debe ser positivo")
    records = _load_records(legacy_path)
    prepared = tuple(
        _prepare_document(
            record,
            legacy_path=legacy_path,
            output_root=output_root,
            project_root=project_root,
            generated_at=generated_at,
        )
        for record in records
    )
    documents = tuple(
        document | {"batch_id": f"batch-{index // batch_size + 1:03d}"}
        for index, (document, _preserved) in enumerate(prepared)
    )
    manifest = RolloutManifest.model_validate(
        {
            "schema_version": "residenciafiscal-rollout/1",
            "rollout_id": "jurisprudencia-v3-fase-e",
            "expected_documents": len(documents),
            "documents": documents,
        }
    )
    write_case_derivative(_render(manifest.model_dump(mode="json")), manifest_path)
    return BootstrapResult(
        generated_documents=tuple(
            str(document["judgment_id"]) for document, preserved in prepared if not preserved
        ),
        preserved_documents=tuple(
            str(document["judgment_id"]) for document, preserved in prepared if preserved
        ),
        manifest_path=manifest_path,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepara las entradas explícitas de fase E.")
    parser.add_argument("--legacy", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--generated-at", required=True)
    parser.add_argument("--batch-size", type=int, default=10)
    args = parser.parse_args(argv)
    result = bootstrap_rollout_inputs(
        legacy_path=args.legacy,
        manifest_path=args.manifest,
        output_root=args.output_root,
        project_root=args.project_root,
        generated_at=datetime.fromisoformat(args.generated_at),
        batch_size=args.batch_size,
    )
    print(
        _render(
            {
                "generated_documents": len(result.generated_documents),
                "preserved_documents": len(result.preserved_documents),
                "manifest": str(result.manifest_path),
            }
        ),
        end="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
