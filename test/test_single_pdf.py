#!/usr/bin/env python3
"""
Test script: Run residenciafiscal.py with a single PDF to verify output format.

This script:
1. Creates temporary input/output directories
2. Copies 1 PDF from sentencias folder
3. Runs residenciafiscal.py
4. Displays the generated JSONL and CSV outputs

Usage:
    cd /home/ubuntu/ai_projects/residenciafiscal
    python test/test_single_pdf.py
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# Este módulo es un script ejecutable, no una suite pytest: hoy no define funciones
# `test_*`, así que `make test` solo lo importa. El marker está puesto de antemano
# para que, si alguien añade un `def test_...` aquí, quede excluido del pytest por
# defecto (`addopts` en pyproject.toml) en vez de empezar a gastar API real sin aviso.
# Para ejecutarlo a propósito: `make test-llm`.
pytestmark = pytest.mark.manual_real_llm

# Colors for terminal output
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{BOLD}{BLUE}{'=' * 70}{RESET}")
    print(f"{BOLD}{BLUE}{text}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 70}{RESET}\n")


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"{GREEN}✅ {text}{RESET}")


def print_info(text: str) -> None:
    """Print an info message."""
    print(f"{BLUE}ℹ️  {text}{RESET}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"{RED}❌ {text}{RESET}")


def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"{YELLOW}⚠️  {text}{RESET}")


def main() -> int:
    """Run the test."""
    project_root = Path(__file__).parent.parent
    sentencias_dir = project_root / "sentencias"

    print_header("🧪 Single PDF Test for residenciafiscal.py")

    # Check if sentencias directory exists
    if not sentencias_dir.exists():
        print_error(f"Sentencias directory not found: {sentencias_dir}")
        return 1

    # Find a PDF file
    pdf_files = list(sentencias_dir.glob("*.pdf"))
    if not pdf_files:
        print_error(f"No PDF files found in: {sentencias_dir}")
        return 1

    test_pdf = pdf_files[0]
    print_info(f"Found {len(pdf_files)} PDFs total")
    print_success(f"Using PDF: {test_pdf.name}")

    # Create persistent test output directories (not temporary)
    test_output_base = project_root / "test" / "test_outputs"
    test_input_dir = test_output_base / "input"
    test_output_dir = test_output_base / "output"

    test_input_dir.mkdir(parents=True, exist_ok=True)
    test_output_dir.mkdir(parents=True, exist_ok=True)

    print_info(f"Test input directory: {test_input_dir}")
    print_info(f"Test output directory: {test_output_dir}")

    # Note: Not using 'with' context manager so output persists after test completes

    try:
        # Copy single PDF to test input directory
        dest_pdf = test_input_dir / test_pdf.name
        shutil.copy2(test_pdf, dest_pdf)
        print_success(f"Copied {test_pdf.name} to test input")

        # Run residenciafiscal.py
        print_header("🚀 Running residenciafiscal.py")

        cmd = [
            sys.executable,
            str(project_root / "residenciafiscal.py"),
            "--input",
            str(test_input_dir),
            "--output",
            str(test_output_dir),
        ]

        print_info(f"Command: {' '.join(cmd)}\n")

        try:
            result = subprocess.run(cmd, cwd=str(project_root), capture_output=False)

            if result.returncode != 0:
                print_error(f"Script exited with code: {result.returncode}")
                return result.returncode

        except Exception as e:
            print_error(f"Failed to run script: {e}")
            return 1

        # Check output files
        print_header("📊 Generated Output Files")

        jsonl_files = list(test_output_dir.glob("*.jsonl"))
        csv_files = list(test_output_dir.glob("*.csv"))

        jsonl_file = max(jsonl_files, key=lambda p: p.stat().st_mtime) if jsonl_files else None
        csv_file = max(csv_files, key=lambda p: p.stat().st_mtime) if csv_files else None

        if not jsonl_file or not jsonl_file.exists():
            print_error(f"JSONL file not found in: {test_output_dir}")
            return 1

        if not csv_file or not csv_file.exists():
            print_error(f"CSV file not found in: {test_output_dir}")
            return 1

        print_success(f"JSONL: {jsonl_file.name} ({jsonl_file.stat().st_size} bytes)")
        print_success(f"CSV:  {csv_file.name} ({csv_file.stat().st_size} bytes)")

        # Display JSONL content
        print_header(f"📄 JSONL Content ({jsonl_file.name})")

        with jsonl_file.open("r", encoding="utf-8") as f:
            jsonl_lines = f.readlines()

        print_info(f"Lines in JSONL: {len(jsonl_lines)}\n")

        for i, line in enumerate(jsonl_lines, 1):
            try:
                data = json.loads(line)
                print(f"{YELLOW}Line {i}:{RESET}")
                print(json.dumps(data, ensure_ascii=False, indent=2))
                print()
            except json.JSONDecodeError as e:
                print_error(f"Invalid JSON on line {i}: {e}")
                print(f"Raw: {line[:200]}...")

        # Display CSV content
        print_header(f"📊 CSV Content ({csv_file.name})")

        with csv_file.open("r", encoding="utf-8") as f:
            csv_lines = f.readlines()

        print_info(f"Rows in CSV: {len(csv_lines)} (including header)\n")

        for line in csv_lines[:3]:  # Show first 3 rows
            print(line.rstrip())

        if len(csv_lines) > 3:
            print(f"\n{YELLOW}... ({len(csv_lines) - 3} more rows){RESET}")

        # Summary
        print_header("✨ Test Summary")

        print_success(f"PDF processed: {test_pdf.name}")
        print_success(f"JSONL output: {len(jsonl_lines)} records")
        print_success(f"CSV output: {len(csv_lines)} rows (incl. header)")

        # Extract key fields from JSONL
        if jsonl_lines:
            try:
                first_record = json.loads(jsonl_lines[0])
                print(f"\n{BLUE}Key fields extracted:{RESET}")
                print(f"  • archivo: {first_record.get('archivo', 'N/A')}")
                print(f"  • organo: {first_record.get('organo', 'N/A')}")
                print(f"  • fecha_resolucion: {first_record.get('fecha_resolucion', 'N/A')}")
                print(
                    f"  • pais_alegado_residencia: {first_record.get('pais_alegado_residencia_pf', 'N/A')}"
                )
                print(f"  • resultado_final: {first_record.get('resultado_final', 'N/A')}")
                print(
                    f"  • confianza_extraccion: {first_record.get('confianza_extraccion', 'N/A')}"
                )
            except Exception as e:
                print_warning(f"Could not extract key fields: {e}")

        print(f"\n{GREEN}{BOLD}✅ Test completed successfully!{RESET}\n")
        print_info(f"📂 Test outputs saved to: {test_output_base}")
        return 0

    except Exception as e:
        print_error(f"Test failed with error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
