#!/usr/bin/env python3
"""
Comprehensive comparison test for different reasoning_effort levels.

This script runs the residenciafiscal pipeline with 8 different configurations:
- GPT-5 with reasoning_effort: high, medium, low, minimal
- GPT-5-mini with reasoning_effort: high, medium, low, minimal

It measures:
- Time to process
- Tokens (input/output)
- Cost (USD)
- Quality metrics from the extraction

Usage:
    python test/test_reasoning_effort_comparison.py [--pdf PATH]

Examples:
    # Test with default PDF
    python test/test_reasoning_effort_comparison.py

    # Test with specific PDF
    python test/test_reasoning_effort_comparison.py --pdf sentencias/STS_4220_2024.pdf
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent

# Test configurations: (model, reasoning_effort)
# Ordenado de más barato/rápido a más lento/caro.
TEST_CONFIGURATIONS = [
    ("gpt-5.6-luna", "medium"),
    ("gpt-5.6-luna", "high"),
    ("gpt-5.2-2025-12-11", "medium"),
]

# Colors for CLI output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def print_header(text: str) -> None:
    """Print a colored header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}")
    print(f"{text:^80}")
    print(f"{'=' * 80}{Colors.ENDC}\n")


def print_section(text: str) -> None:
    """Print a colored section header."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.CYAN}{'-' * len(text)}{Colors.ENDC}")


def print_success(text: str) -> None:
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")


def print_error(text: str) -> None:
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")


def print_warning(text: str) -> None:
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.ENDC}")


def find_available_pdf() -> Optional[Path]:
    """Find an available PDF in sentencias directory."""
    sentencias_dir = PROJECT_ROOT / "sentencias"
    if not sentencias_dir.exists():
        return None

    pdfs = list(sentencias_dir.glob("*.pdf"))
    return pdfs[0] if pdfs else None


def default_metrics() -> dict[str, Any]:
    """Default metrics shape to keep outputs consistent."""
    return {
        "cost_usd": 0.0,
        "confianza_extraccion": "NO CONSTA",
        "resultado_final": "NO CONSTA",
        "es_caso_residencia_irpf": "NO CONSTA",
        "se_invoca_CDI": "NO CONSTA",
        "criterios_detectados": 0,
        "pruebas_aeat": 0,
        "pruebas_contribuyente": 0,
        "error": None,
    }


def serialize_for_csv(value: Any) -> Any:
    """Serialize nested structures to JSON strings for CSV safety."""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value


def find_jsonl_output(output_dir: Path) -> Optional[Path]:
    """Find the most recent JSONL file in the output directory."""
    jsonl_files = list(output_dir.glob("*.jsonl"))
    if not jsonl_files:
        return None
    return max(jsonl_files, key=lambda p: p.stat().st_mtime)


def extract_metrics_from_jsonl(jsonl_path: Path) -> dict[str, Any]:
    """Extract metrics from generated JSONL file."""
    metrics = default_metrics()

    if not jsonl_path.exists():
        metrics["error"] = "JSONL file not found"
        return metrics

    try:
        with open(jsonl_path, 'r') as f:
            first_record = None
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    if first_record is None:
                        first_record = data

                    metrics["cost_usd"] += data.get("costo_usd", data.get("cost_usd", 0.0))

                    # Extract quality metrics
                    if data.get("confianza_extraccion"):
                        metrics["confianza_extraccion"] = data.get("confianza_extraccion")

                    if data.get("resultado_final"):
                        metrics["resultado_final"] = data.get("resultado_final")

                    if data.get("es_caso_residencia_irpf"):
                        metrics["es_caso_residencia_irpf"] = data.get("es_caso_residencia_irpf")

                    if data.get("se_invoca_CDI"):
                        metrics["se_invoca_CDI"] = data.get("se_invoca_CDI")

                    if data.get("Criterios_residencia_detectados"):
                        metrics["criterios_detectados"] = len(data.get("Criterios_residencia_detectados", []))

                    if data.get("Pruebas_AEAT"):
                        metrics["pruebas_aeat"] = len(data.get("Pruebas_AEAT", []))

                    if data.get("Pruebas_contribuyente"):
                        metrics["pruebas_contribuyente"] = len(data.get("Pruebas_contribuyente", []))

                    if data.get("observaciones"):
                        metrics["error"] = data.get("observaciones")

                except json.JSONDecodeError:
                    continue

        if first_record:
            for key, value in first_record.items():
                if key == "error" and metrics["error"] in (None, "NO CONSTA"):
                    metrics["error"] = serialize_for_csv(value)
                    continue
                if key in metrics:
                    continue
                metrics[key] = serialize_for_csv(value)

        return metrics
    except Exception as e:
        metrics["error"] = f"Failed to parse JSONL: {str(e)}"
        return metrics


async def run_single_test(
    pdf_path: Path,
    model: str,
    reasoning_effort: str,
    temp_dir: Path
) -> dict[str, Any]:
    """Run a single configuration test.

    Args:
        pdf_path: Path to the PDF to process
        model: Model name
        reasoning_effort: Reasoning effort level
        temp_dir: Temporary directory for output

    Returns:
        Dictionary with metrics and results
    """
    config_name = f"{model.split('-')[2]}_{reasoning_effort}"
    print_section(f"Testing: {model} with reasoning_effort={reasoning_effort}")

    # Create unique output subdirectory
    output_subdir = temp_dir / config_name
    output_subdir.mkdir(exist_ok=True)

    # Build command
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "residenciafiscal.py"),
        "--input", str(pdf_path.parent),
        "--output", str(output_subdir),
        "--model", model,
        "--reasoning-effort", reasoning_effort,
        "--max-files", "1",  # Process only one PDF
    ]

    try:
        # Record start time
        start_time = time.time()

        # Run the pipeline
        logger.info(f"Running: {' '.join(cmd)}")
        result = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await result.communicate()
        elapsed_time = time.time() - start_time

        if result.returncode != 0:
            print_error(f"Process exited with code {result.returncode}")
            logger.error(f"STDERR: {stderr.decode()}")
            return {
                "model": model,
                "reasoning_effort": reasoning_effort,
                "time_seconds": elapsed_time,
                "error": f"Process exited with code {result.returncode}",
                **default_metrics(),
                "confianza_extraccion": "ERROR",
                "resultado_final": "ERROR",
            }

        # Extract metrics from JSONL output (timestamped name)
        jsonl_path = find_jsonl_output(output_subdir)
        if jsonl_path is None:
            metrics = extract_metrics_from_jsonl(output_subdir / "analisis.jsonl")
        else:
            metrics = extract_metrics_from_jsonl(jsonl_path)

        # Combine metrics
        result_dict = {
            "model": model.split('-')[2],  # Extract version (5 or 5-mini)
            "reasoning_effort": reasoning_effort,
            "time_seconds": round(elapsed_time, 2),
            **metrics,
        }

        print_success(f"Completed in {elapsed_time:.2f}s")
        print(f"  Cost: ${metrics.get('cost_usd', 0.0):.4f}")
        print(f"  Confidence: {metrics.get('confianza_extraccion', 'NO CONSTA')}")
        print(f"  Criteria detected: {metrics.get('criterios_detectados', 0)}")

        return result_dict

    except Exception as e:
        print_error(f"Test execution failed: {e}")
        logger.exception("Full traceback:")
        return {
            "model": model,
            "reasoning_effort": reasoning_effort,
            "time_seconds": elapsed_time if 'elapsed_time' in locals() else 0,
            "error": str(e),
            **default_metrics(),
            "confianza_extraccion": "ERROR",
            "resultado_final": "ERROR",
        }


async def run_all_tests(
    pdf_path: Path,
) -> list[dict[str, Any]]:
    """Run all test configurations in parallel.

    Args:
        pdf_path: Path to the PDF to test
    Returns:
        List of result dictionaries
    """
    results = []
    temp_dir = Path(tempfile.mkdtemp(prefix="residencia_test_"))

    try:
        print_header("REASONING EFFORT COMPARISON TEST")
        print(f"Testing PDF: {pdf_path.name}")
        print(f"Configurations: {len(TEST_CONFIGURATIONS)}")
        print("Running all configurations in parallel...\n")

        tasks = [
            run_single_test(
                pdf_path=pdf_path,
                model=model,
                reasoning_effort=reasoning_effort,
                temp_dir=temp_dir,
            )
            for model, reasoning_effort in TEST_CONFIGURATIONS
        ]

        results = await asyncio.gather(*tasks)
        return results

    finally:
        # Cleanup temp directory
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp directory: {e}")


def format_results_table(results: list[dict[str, Any]]) -> pd.DataFrame:
    """Format results as a DataFrame for display and export."""
    df = pd.DataFrame(results)

    # Sort by model and reasoning effort
    effort_order = {"minimal": 0, "low": 1, "medium": 2, "high": 3}
    df["effort_rank"] = df["reasoning_effort"].map(effort_order)
    df = df.sort_values(["model", "effort_rank"]).drop("effort_rank", axis=1)

    return df


def print_results_summary(results: list[dict[str, Any]]) -> None:
    """Print summary of results."""
    print_header("TEST RESULTS SUMMARY")

    df = format_results_table(results)

    # Display table
    print(df.to_string(index=False))

    # Calculate statistics
    print_section("Cost Comparison")
    gpt5_costs = df[df["model"] == "5"]["cost_usd"].sum()
    gpt5mini_costs = df[df["model"] == "5-mini"]["cost_usd"].sum()
    total_cost = df["cost_usd"].sum()

    print(f"GPT-5 total cost:      ${gpt5_costs:.4f}")
    print(f"GPT-5-mini total cost: ${gpt5mini_costs:.4f}")
    print(f"Overall cost:          ${total_cost:.4f}")
    print(f"Cost difference:       ${abs(gpt5_costs - gpt5mini_costs):.4f} ({(abs(gpt5_costs - gpt5mini_costs) / max(gpt5_costs, gpt5mini_costs) * 100):.1f}%)")

    print_section("Time Comparison")
    gpt5_time = df[df["model"] == "5"]["time_seconds"].sum()
    gpt5mini_time = df[df["model"] == "5-mini"]["time_seconds"].sum()

    print(f"GPT-5:      {gpt5_time:.2f}s")
    print(f"GPT-5-mini: {gpt5mini_time:.2f}s")

    print_section("Quality Comparison")
    print("\nConfidence levels:")
    print(df[["model", "reasoning_effort", "confianza_extraccion"]].to_string(index=False))

    print("\nCriteria detected:")
    print(df[["model", "reasoning_effort", "criterios_detectados"]].to_string(index=False))


def export_results_csv(results: list[dict[str, Any]], output_path: Path) -> None:
    """Export results to CSV file."""
    df = format_results_table(results)
    df.to_csv(output_path, index=False)
    print_success(f"Results exported to: {output_path}")


def export_results_json(results: list[dict[str, Any]], output_path: Path) -> None:
    """Export results to JSON file."""
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print_success(f"Results exported to: {output_path}")


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        default=PROJECT_ROOT / "sentencias" / "STS_4220_2024.pdf",
        help="Path to PDF to test (default: sentencias/STS_4220_2024.pdf)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "test_results",
        help="Directory for test results (default: test_results/)",
    )

    args = parser.parse_args()

    # Validate PDF path
    pdf_path = args.pdf
    if pdf_path is None:
        pdf_path = find_available_pdf()
        if pdf_path is None:
            print_error("No PDF found in sentencias/ directory")
            sys.exit(1)
        print_success(f"Using PDF: {pdf_path.name}")
    elif not pdf_path.exists():
        print_error(f"PDF not found: {pdf_path}")
        sys.exit(1)

    # Ensure output directory exists
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Run tests
    try:
        results = await run_all_tests(pdf_path)
    except Exception as e:
        print_error(f"Test execution failed: {e}")
        logger.exception("Full traceback:")
        sys.exit(1)

    # Display results
    print_results_summary(results)

    # Export results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = args.output_dir / f"reasoning_effort_comparison_{timestamp}.csv"
    json_path = args.output_dir / f"reasoning_effort_comparison_{timestamp}.json"

    export_results_csv(results, csv_path)
    export_results_json(results, json_path)

    print_header("TEST COMPLETE")
    print(f"Results saved to:\n  {csv_path}\n  {json_path}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print_error("\nTest interrupted by user")
        sys.exit(130)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        logger.exception("Full traceback:")
        sys.exit(1)
