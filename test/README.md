# 🧪 Test Suite for residenciafiscal.py

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
cd /home/ubuntu/ai_projects/residenciafiscal
source venv/bin/activate
python test/test_single_pdf.py
```

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

1. **Virtual environment activated**:
   ```bash
   source venv/bin/activate
   ```

2. **Dependencies installed**:
   ```bash
   pip install -r requirements.txt
   ```

3. **API key configured**:
   ```bash
   # Copy .env.example to .env and add your API key
   cp .env.example .env
   # Edit .env and add OPENAI_API_KEY (or GROQ_API_KEY, etc.)
   ```

4. **PDF files in sentencias/ folder**:
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
   python residenciafiscal.py
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
python test/test_single_pdf.py 2>&1 | tee test.log

# Check residenciafiscal logs
grep "ERROR\|WARNING" test.log
```

### File Structure

```
test/
├── README.md              # This file
└── test_single_pdf.py     # Main test script
```
