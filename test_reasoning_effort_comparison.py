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
    python test_reasoning_effort_comparison.py [--pdf PATH] [--max-pages N]

Examples:
    # Test with first available PDF, limit to 10 pages
    python test_reasoning_effort_comparison.py --max-pages 10

    # Test with specific PDF
    python test_reasoning_effort_comparison.py --pdf sentencias/STS_371_2020.pdf --max-pages 20
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

PROJECT_ROOT = Path(__file__).parent

# Test configurations: (model, reasoning_effort)
TEST_CONFIGURATIONS = [
    ("gpt-5.2-2025-12-11", "high"),
    ("gpt-5.2-2025-12-11", "medium"),
    ("gpt-5.2-2025-12-11", "low"),
    ("gpt-5.2-2025-12-11", "minimal"),
    ("gpt-5-mini-2025-08-07", "high"),
    ("gpt-5-mini-2025-08-07", "medium"),
    ("gpt-5-mini-2025-08-07", "low"),
    ("gpt-5-mini-2025-08-07", "minimal"),
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


def extract_metrics_from_jsonl(jsonl_path: Path) -> dict[str, Any]:
    """Extract metrics from generated JSONL file."""
    if not jsonl_path.exists():
        return {"error": "JSONL file not found"}

    metrics = {
        "tokens_in": 0,
        "tokens_out": 0,
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

    try:
        with open(jsonl_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)

                    # Extract token and cost info
                    metrics["tokens_in"] += data.get("tokens_in", 0)
                    metrics["tokens_out"] += data.get("tokens_out", 0)
                    metrics["cost_usd"] += data.get("cost_usd", 0.0)

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

        return metrics
    except Exception as e:
        return {"error": f"Failed to parse JSONL: {str(e)}"}


async def run_single_test(
    pdf_path: Path,
    model: str,
    reasoning_effort: str,
    max_pages: int,
    temp_dir: Path
) -> dict[str, Any]:
    """Run a single configuration test.

    Args:
        pdf_path: Path to the PDF to process
        model: Model name
        reasoning_effort: Reasoning effort level
        max_pages: Maximum pages to process
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

    if max_pages > 0:
        cmd.extend(["--max-pages", str(max_pages)])

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
                "tokens_in": 0,
                "tokens_out": 0,
                "cost_usd": 0.0,
                "confianza_extraccion": "ERROR",
                "resultado_final": "ERROR",
            }

        # Extract metrics from JSONL output
        jsonl_path = output_subdir / "analisis.jsonl"
        metrics = extract_metrics_from_jsonl(jsonl_path)

        # Combine metrics
        result_dict = {
            "model": model.split('-')[2],  # Extract version (5 or 5-mini)
            "reasoning_effort": reasoning_effort,
            "time_seconds": round(elapsed_time, 2),
            **metrics,
        }

        print_success(f"Completed in {elapsed_time:.2f}s")
        print(f"  Tokens: {metrics['tokens_in']} in, {metrics['tokens_out']} out")
        print(f"  Cost: ${metrics['cost_usd']:.4f}")
        print(f"  Confidence: {metrics['confianza_extraccion']}")
        print(f"  Criteria detected: {metrics['criterios_detectados']}")

        return result_dict

    except Exception as e:
        print_error(f"Test execution failed: {e}")
        logger.exception("Full traceback:")
        return {
            "model": model,
            "reasoning_effort": reasoning_effort,
            "time_seconds": elapsed_time if 'elapsed_time' in locals() else 0,
            "error": str(e),
            "tokens_in": 0,
            "tokens_out": 0,
            "cost_usd": 0.0,
            "confianza_extraccion": "ERROR",
            "resultado_final": "ERROR",
        }


async def run_all_tests(
    pdf_path: Path,
    max_pages: int = 0,
) -> list[dict[str, Any]]:
    """Run all test configurations sequentially.

    Args:
        pdf_path: Path to the PDF to test
        max_pages: Maximum pages to process per PDF

    Returns:
        List of result dictionaries
    """
    results = []
    temp_dir = Path(tempfile.mkdtemp(prefix="residencia_test_"))

    try:
        print_header("REASONING EFFORT COMPARISON TEST")
        print(f"Testing PDF: {pdf_path.name}")
        print(f"Max pages per PDF: {max_pages if max_pages > 0 else 'unlimited'}")
        print(f"Configurations: {len(TEST_CONFIGURATIONS)}")

        for i, (model, reasoning_effort) in enumerate(TEST_CONFIGURATIONS, 1):
            print(f"\n[{i}/{len(TEST_CONFIGURATIONS)}]", end=" ")

            result = await run_single_test(
                pdf_path=pdf_path,
                model=model,
                reasoning_effort=reasoning_effort,
                max_pages=max_pages,
                temp_dir=temp_dir,
            )

            results.append(result)

            # Small delay between requests to avoid rate limiting
            if i < len(TEST_CONFIGURATIONS):
                await asyncio.sleep(2)

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

    print_section("Token Usage Comparison")
    gpt5_tokens_in = df[df["model"] == "5"]["tokens_in"].sum()
    gpt5_tokens_out = df[df["model"] == "5"]["tokens_out"].sum()
    gpt5mini_tokens_in = df[df["model"] == "5-mini"]["tokens_in"].sum()
    gpt5mini_tokens_out = df[df["model"] == "5-mini"]["tokens_out"].sum()

    print(f"GPT-5:      {gpt5_tokens_in} in, {gpt5_tokens_out} out")
    print(f"GPT-5-mini: {gpt5mini_tokens_in} in, {gpt5mini_tokens_out} out")

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
        default=None,
        help="Path to PDF to test (default: first PDF in sentencias/)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=10,
        help="Maximum pages per PDF (default: 10)",
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
        results = await run_all_tests(pdf_path, args.max_pages)
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
