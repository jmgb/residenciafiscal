#!/bin/bash
# Quick test runner for residenciafiscal.py with single PDF

cd "$(dirname "$0")/.." || exit 1

if ! command -v uv >/dev/null 2>&1; then
    echo "❌ uv no está instalado."
    echo "Instálalo con: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "⚠️ Entorno no encontrado. Ejecutando 'make setup'..."
    make setup || exit 1
fi

echo "🧪 Starting single PDF test..."
uv run python test/test_single_pdf.py

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo ""
    echo "📚 To see full usage, check: test/README.md"
else
    echo ""
    echo "❌ Test failed with exit code: $exit_code"
fi

exit $exit_code
