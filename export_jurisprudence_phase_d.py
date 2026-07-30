"""Exporta la evaluación reproducible de recuperación de la fase D."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from jurisprudence_case_derivative_artifacts import write_case_derivative
from jurisprudence_phase_d_evaluation import (
    evaluate_phase_d,
    load_paraphrase_bank,
    materialize_paraphrase_bank,
    render_phase_d_report,
)
from jurisprudence_phase_d_evaluation_models import PhaseDEvaluationReport
from jurisprudence_retrieval_corpus import load_retrieval_corpus
from jurisprudence_sample_evaluation import parse_question_pilot


@dataclass(frozen=True)
class PhaseDExportResult:
    artifact_path: Path
    report: PhaseDEvaluationReport


def export_phase_d_evaluation(
    *,
    corpus_path: Path,
    pilot_path: Path,
    paraphrases_path: Path,
    output_path: Path,
) -> PhaseDExportResult:
    corpus = load_retrieval_corpus(corpus_path.read_bytes())
    original = parse_question_pilot(pilot_path)
    paraphrase_definitions = load_paraphrase_bank(paraphrases_path)
    if paraphrase_definitions.sample_id != corpus.sample_id:
        raise ValueError("paraphrases.sample_id no coincide con el corpus")
    paraphrases = materialize_paraphrase_bank(paraphrase_definitions, original)
    if len(original.questions) != 40:
        raise ValueError("el banco original debe contener 40 preguntas")
    if len(paraphrases.questions) != 20:
        raise ValueError("el banco de paráfrasis debe contener 20 preguntas")
    report = evaluate_phase_d(
        corpus=corpus,
        original_bank=original,
        paraphrase_bank=paraphrases,
    )
    write_case_derivative(render_phase_d_report(report), output_path)
    return PhaseDExportResult(artifact_path=output_path, report=report)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evalúa la recuperación estructurada de fase D.")
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--pilot", type=Path, required=True)
    parser.add_argument("--paraphrases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = export_phase_d_evaluation(
        corpus_path=args.corpus,
        pilot_path=args.pilot,
        paraphrases_path=args.paraphrases,
        output_path=args.output,
    )
    report = result.report
    print(
        json.dumps(
            {
                "artifact": str(result.artifact_path),
                "baseline": report.baseline.model_dump(mode="json"),
                "candidate": report.candidate.model_dump(mode="json"),
                "embedding_decision": report.embedding_decision,
                "gate_status": report.gate_status,
                "original_behavior_accuracy": report.original.behavior_accuracy,
                "paraphrase_behavior_accuracy": report.paraphrases.behavior_accuracy,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report.gate_status == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
