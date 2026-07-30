"""CLI explícita para inicializar, inspeccionar y reanudar fase E."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from jurisprudence_rollout import (
    batch_gate,
    initialize_rollout,
    load_rollout_state,
    write_rollout_state,
)
from jurisprudence_rollout_pipeline import execute_rollout_next_batch


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Orquesta el rollout jurisprudencial v3.")
    commands = parser.add_subparsers(dest="command", required=True)
    initialize = commands.add_parser("init")
    initialize.add_argument("--manifest", type=Path, required=True)
    initialize.add_argument("--state", type=Path, required=True)
    status = commands.add_parser("status")
    status.add_argument("--state", type=Path, required=True)
    run = commands.add_parser("run-next")
    run.add_argument("--manifest", type=Path, required=True)
    run.add_argument("--state", type=Path, required=True)
    run.add_argument("--output-root", type=Path, required=True)
    run.add_argument("--project-root", type=Path, default=Path.cwd())
    run.add_argument("--retry-failed", action="store_true")
    return parser


def _status_payload(state_path: Path) -> dict[str, object]:
    state = load_rollout_state(state_path)
    batches = tuple(dict.fromkeys(item.batch_id for item in state.documents))
    return {
        "batches": {batch_id: batch_gate(state_path, batch_id) for batch_id in batches},
        "documents": len(state.documents),
        "execution_status": dict(
            sorted(Counter(item.execution_status.value for item in state.documents).items())
        ),
        "rollout_id": state.rollout_id,
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "init":
        if args.state.exists():
            raise ValueError("el estado ya existe; no se sobrescribe")
        state = initialize_rollout(args.manifest)
        write_rollout_state(state, args.state)
        payload: object = _status_payload(args.state)
    elif args.command == "status":
        payload = _status_payload(args.state)
    else:
        result = execute_rollout_next_batch(
            manifest_path=args.manifest,
            state_path=args.state,
            output_root=args.output_root,
            project_root=args.project_root,
            retry_failed=args.retry_failed,
        )
        payload = {
            "batch_id": result.batch_id,
            "failed": result.failed,
            "passed": result.passed,
            "state": str(result.state_path),
        }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
