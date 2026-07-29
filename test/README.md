# 🧪 Test Suite for residenciafiscal.py

## Overview

| Fichero | Qué cubre | Coste |
|---------|-----------|-------|
| `test_api.py` | Capa HTTP (`api/main.py`): health, config, validación de uploads | Ninguno |
| `test_gemini_model_policy.py` | Que los IDs de modelos Gemini en `config.py` son los soportados | Ninguno |
| `test_single_pdf.py` | Smoke test end-to-end del pipeline con 1 PDF | ~$0.01–0.04 |
| `test_reasoning_effort_comparison.py` | Comparativa de reasoning effort entre modelos | Alto |

```bash
make test          # pytest: solo lo que no gasta (test_api + gemini policy)
make test-single   # smoke test end-to-end con 1 PDF (gasta)
make test-llm      # alias compatible de make test-single
```

Los módulos de scripts con llamadas reales llevan el marker
`manual_real_llm`, por lo que quedan excluidos del `pytest` por defecto (ver
`addopts` en `pyproject.toml`). Los smoke reales se lanzan de forma explícita
con `make test-single` o `make test-llm`.

## Single PDF Test

### Purpose
Test the main processing pipeline with a single PDF to verify:
- PDF text extraction with page markers
- LLM API integration via `gpt_request`
- JSON output format (JSONL)
- CSV conversion
- All required fields are populated

### Quick Start

```bash
# desde la raíz del repositorio
make test-single
```

Equivalente directo: `uv run python test/test_single_pdf.py`. No hace falta activar
ningún entorno — `uv run` lo resuelve solo.

### What the Test Does

1. **Creates temporary directories** for isolated input/output
2. **Copies 1 PDF** from `sentencias/` folder (the first one found)
3. **Runs residenciafiscal.py** with:
   - No page limit (always processes full PDF)
   - Temporary input/output paths
4. **Displays results**:
   - Generated JSONL content (all fields)
   - Generated CSV sample (first 3 rows)
   - Key metrics (records count, file sizes)

### Output Format

The test will show:

```
========================================================================
🧪 Single PDF Test for residenciafiscal.py
========================================================================

ℹ️  Found 22 PDFs total
✅ Using PDF: STS_107_2018.pdf
ℹ️  Temp input directory: /tmp/xyz/input
ℹ️  Temp output directory: /tmp/xyz/output

========================================================================
🚀 Running residenciafiscal.py
========================================================================

[PDF processing logs here]

========================================================================
📄 JSONL Content (latest .jsonl)
========================================================================

Line 1:
{
  "archivo": "STS_107_2018.pdf",
  "identificadores": {...},
  "organo": "Audiencia Nacional",
  ...
}

========================================================================
📊 CSV Content (latest .csv)
========================================================================

archivo,ROJ,ECLI,organo,fecha_resolucion,...
STS_107_2018.pdf,AN/2018/107,...

========================================================================
✨ Test Summary
========================================================================

✅ PDF processed: STS_107_2018.pdf
✅ JSONL output: 1 records
✅ CSV output: 2 rows (incl. header)
```

### Requirements

Before running the test, ensure:

1. **Entorno instalado** (uv crea `.venv` con Python 3.13):
   ```bash
   make setup
   ```

2. **API key configured**:
   ```bash
   # Copy .env.example to .env and add your API key
   cp .env.example .env
   # Edit .env and add OPENAI_API_KEY (or GROQ_API_KEY, etc.)
   ```

3. **PDF files in sentencias/ folder**:
   ```bash
   ls sentencias/*.pdf  # Should show at least 1 PDF
   ```

### Interpreting Results

✅ **Success**:
- Both `*.jsonl` and `*.csv` files generated (timestamped)
- JSONL contains valid JSON with all required fields
- CSV has proper structure with column headers
- No API errors in the logs

⚠️ **Common Issues**:

| Issue | Solution |
|-------|----------|
| `API key not found` | Check `.env` file has correct key for selected model |
| `No PDFs found` | Ensure PDFs exist in `sentencias/` directory |
| `JSON parse error` | LLM returned invalid JSON - may need to adjust prompt |
| `Empty output` | PDF might have no extractable text |

### Test Configuration

The test uses these defaults:
- **Model**: gpt-5-mini (from config.py)
- **Max pages**: 5 (faster testing)
- **Input**: Auto-detected single PDF from sentencias/
- **Output**: Temporary directory (auto-cleanup)

To customize, edit the `cmd` variable in `test_single_pdf.py`:

```python
cmd = [
    sys.executable,
    str(project_root / "residenciafiscal.py"),
    "--input", str(test_input_dir),
    "--output", str(test_output_dir),
    "--model", "groq-mixtral-8x7b-32k",  # Change model
]
```

### Next Steps

After successful test:

1. **Run with more PDFs**:
   ```bash
   make run
   ```

2. **Check output files**:
   ```bash
   ls -lh output/
   head -c 500 output/analisis_*.jsonl
   head output/analisis_*.csv
   ```

### Debugging

If test fails, check logs:

```bash
# Run with verbose logging
uv run python test/test_single_pdf.py 2>&1 | tee test.log

# Check residenciafiscal logs
grep "ERROR\|WARNING" test.log
```

### File Structure

```
test/
├── README.md                              # This file
├── run_test.sh                            # Wrapper de test_single_pdf.py
├── test_api.py                            # Tests de la API HTTP (sin coste)
├── test_gemini_model_policy.py            # Política de modelos Gemini
├── test_single_pdf.py                     # Smoke test end-to-end (con coste)
└── test_reasoning_effort_comparison.py    # Comparativa de reasoning effort (coste alto)
```
