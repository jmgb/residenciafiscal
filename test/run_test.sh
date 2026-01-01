#!/bin/bash
# Quick test runner for residenciafiscal.py with single PDF

cd "$(dirname "$0")/.." || exit 1

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate venv
source venv/bin/activate

# Run test
echo "🧪 Starting single PDF test..."
python test/test_single_pdf.py

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo ""
    echo "📚 To see full usage, check: test/README.md"
else
    echo ""
    echo "❌ Test failed with exit code: $exit_code"
fi

exit $exit_code
