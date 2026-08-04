"""CLI explícito para preparar, comparar y eliminar los recursos de F0."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import uuid
from collections.abc import Sequence
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

from chat_model_policy import CHAT_MODEL, CHAT_REASONING_EFFORT
from chat_strategy_comparison import compare_strategies
from chat_strategy_costs import (
    DEFAULT_FILE_SEARCH_MODEL,
    SUPPORTED_FILE_SEARCH_MODELS,
)
from current_structured_strategy import CurrentStructuredStrategy
from gateway_chat_writer import GatewayChatWriter
from gateway_setup import get_gateway
from gemini_file_search_answer import GeminiFileSearchResponder
from gemini_file_search_store import StoreReceipt, prepare_file_search_store
from google_genai_file_search import create_google_genai_gateway
from jurisprudence_retrieval_corpus import load_retrieval_corpus

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = PROJECT_ROOT / "sentencias/jurisprudence_v3_rollout_106.json"
DEFAULT_STORE_STATE = PROJECT_ROOT / "output/file-search/rollout-106-store.json"
DEFAULT_LOG = PROJECT_ROOT / "output/logs/chat-strategy-comparison.jsonl"
DEFAULT_CORPUS = PROJECT_ROOT / "knowledge/jurisprudencia-v3/retrieval/rollout-106.corpus.json"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gemini File Search F0")
    subcommands = parser.add_subparsers(dest="command", required=True)

    prepare = subcommands.add_parser("prepare-store")
    prepare.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    prepare.add_argument("--state", type=Path, default=DEFAULT_STORE_STATE)
    prepare.add_argument("--confirm-paid", action="store_true")

    compare = subcommands.add_parser("compare")
    compare.add_argument("question")
    compare.add_argument("--state", type=Path, default=DEFAULT_STORE_STATE)
    compare.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    compare.add_argument("--output", type=Path)
    compare.add_argument("--log", type=Path, default=DEFAULT_LOG)
    compare.add_argument(
        "--model",
        choices=SUPPORTED_FILE_SEARCH_MODELS,
        default=DEFAULT_FILE_SEARCH_MODEL,
        help=(
            "Modelo de la estrategia B (File Search). No afecta a A, que usa "
            f"la política del chat: {CHAT_MODEL} con esfuerzo {CHAT_REASONING_EFFORT}."
        ),
    )
    compare.add_argument("--confirm-paid", action="store_true")
    compare.add_argument(
        "--only",
        choices=("a", "b"),
        help=(
            "Ejecuta una sola estrategia. Sirve para el smoke de esquema, que "
            "solo necesita comprobar que A sobrevive al modo estricto sin pagar "
            "también la llamada de B."
        ),
    )

    delete = subcommands.add_parser("delete-store")
    delete.add_argument("--state", type=Path, default=DEFAULT_STORE_STATE)
    delete.add_argument("--confirm-delete", action="store_true")
    return parser


def _api_key() -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("Falta GEMINI_API_KEY")
    return api_key


def _require_paid_confirmation(confirmed: bool) -> None:
    if not confirmed:
        raise SystemExit("Se exige --confirm-paid antes de una llamada facturable")


def _load_store(path: Path, *, require_active: bool = True) -> StoreReceipt:
    if not path.is_file():
        raise SystemExit(f"No existe el estado del store: {path}")
    receipt = StoreReceipt.model_validate_json(path.read_bytes())
    if require_active and receipt.status != "ACTIVE":
        raise SystemExit(f"El store aún no está completo: {len(receipt.documents)} PDF")
    return receipt


def _write_model(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = model.model_dump(mode="json")
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _prepare(args: argparse.Namespace) -> int:
    _require_paid_confirmation(args.confirm_paid)
    gateway = create_google_genai_gateway(_api_key())
    existing = _load_store(args.state, require_active=False) if args.state.is_file() else None
    receipt = prepare_file_search_store(
        gateway=gateway,
        manifest_path=args.manifest,
        project_root=PROJECT_ROOT,
        existing_state=existing,
        checkpoint=lambda state: _write_model(args.state, state),
    )
    print(f"Store preparado: {receipt.store_name} ({len(receipt.documents)} PDF)")
    print(f"Estado local: {args.state}")
    return 0


def _verbatim_artifacts(receipt: StoreReceipt) -> dict[str, Path]:
    return {
        document.judgment_id: (
            PROJECT_ROOT / f"knowledge/jurisprudencia-v3/verbatim/{document.judgment_id}.pages.json"
        )
        for document in receipt.documents
    }


def _compare(args: argparse.Namespace) -> int:
    _require_paid_confirmation(args.confirm_paid)
    only = getattr(args, "only", None)
    run_structured = only in (None, "a")
    run_file_search = only in (None, "b")
    structured = None
    file_search = None
    if run_structured:
        corpus = load_retrieval_corpus(args.corpus.read_bytes())
        structured = CurrentStructuredStrategy(
            corpus,
            # A usa la política del chat; B, el modelo de File Search. Pasar el
            # mismo `--model` a las dos ataba A a una capacidad que no usa.
            writer=GatewayChatWriter(get_gateway()),
            model=CHAT_MODEL,
            reasoning_effort=CHAT_REASONING_EFFORT,
            verbatim_artifacts={
                source.judgment_id: (
                    PROJECT_ROOT
                    / f"knowledge/jurisprudencia-v3/verbatim/{source.judgment_id}.pages.json"
                )
                for source in corpus.sources
            },
        )
    if run_file_search:
        receipt = _load_store(args.state)
        file_search = GeminiFileSearchResponder(
            gateway=create_google_genai_gateway(_api_key()),
            store_name=receipt.store_name,
            verbatim_artifacts=_verbatim_artifacts(receipt),
            model=args.model,
        )
    request_id = f"f0-{uuid.uuid4()}"
    output = args.output or PROJECT_ROOT / f"output/file-search/{request_id}.json"
    report = asyncio.run(
        compare_strategies(
            question=args.question,
            structured=structured,
            file_search=file_search,
            output_path=output,
            log_path=args.log,
            request_id=request_id,
        )
    )
    for answer in report.answers:
        print(
            f"{answer.strategy}: {answer.status} — "
            f"USD {answer.cost.amount_usd} ({answer.cost.measurement}) — "
            f"{len(answer.claims)} afirmaciones sobre {len(answer.sources)} citas"
        )
        for limit in answer.limits:
            print(f"  límite: {limit}")
    print(f"Comparación: {output}")
    return 0


def _delete(args: argparse.Namespace) -> int:
    if not args.confirm_delete:
        raise SystemExit("Se exige --confirm-delete para eliminar el store")
    receipt = _load_store(args.state, require_active=False)
    gateway = create_google_genai_gateway(_api_key())
    gateway.delete_store(receipt.store_name)
    args.state.unlink()
    print(f"Store eliminado: {receipt.store_name}")
    print(f"Estado local eliminado: {args.state}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    # El entorno se carga una vez por invocación. Hacerlo dentro del lector de
    # la clave de Gemini ataba las credenciales de A a que B se ejecutara.
    load_dotenv(PROJECT_ROOT / ".env")
    args = _parser().parse_args(argv)
    if args.command == "prepare-store":
        return _prepare(args)
    if args.command == "compare":
        return _compare(args)
    return _delete(args)


if __name__ == "__main__":
    raise SystemExit(main())
