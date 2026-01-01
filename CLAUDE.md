# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Residencia Fiscal** is a Python pipeline that processes Spanish court rulings (sentencias) on fiscal residency disputes to extract structured data about tax law arguments, evidence, and outcomes. The system:

1. **Reads PDFs** from a specified directory and extracts text with page markers
2. **Calls an LLM** (OpenAI Responses API) with a specialized prompt to analyze each ruling
3. **Extracts structured data** about criteria, evidence, and legal outcomes
4. **Outputs JSONL** (one JSON object per line) and converts to **CSV** for analysis

Target users: Tax researchers, lawyers, and compliance professionals analyzing Spanish IRPF (Impuesto sobre la Renta de las Personas Físicas) residency case law.

## Architecture

### Three Core Components

**1. Main Processing Pipeline** (`residenciafiscal.py`)
- Reads PDF files from input directory
- Extracts text with page markers (`--- PÁGINA N ---`)
- Calls OpenAI Responses API with system prompt from `prompt.py`
- Handles retries with exponential backoff (base 1.8)
- Repairs malformed JSON responses using model-guided recovery
- Writes results to JSONL (append mode for resumability)
- Converts JSONL to CSV with flattened structure

**2. Analysis Prompt** (`prompt.py`)
- Contains `SYSTEM_PROMPT` string that instructs the LLM on analysis rules
- Defines 7 residency criteria categories (CRIT_* constants)
- Specifies 12 evidence categories (PRESENCIA_FISICA, VIVIENDA, etc.)
- Requires exhaustive listing of all evidence with acceptance/rejection status
- Enforces mandatory fields with "NO CONSTA" fallback
- Critical: Output must be valid JSON in a single line

**3. Output Structure**
- **JSONL format**: One complete JSON object per line (resumable, streamable)
- **CSV format**: Flattened version with complex fields as JSON strings
- **Key fields**: archivo, ROJ, ECLI, organo, fecha_resolucion, ejercicios_afectados, pais_alegado_residencia, se_invoca_CDI, Criterios_residencia_detectados, Criterio_decisivo, Pruebas_AEAT, Pruebas_contribuyente, Pruebas_rechazadas_clave, resultado_final, confianza_extraccion

## Key Design Patterns

### JSON Extraction Robustness
The pipeline includes sophisticated JSON parsing:
- Strips markdown code fences (```json...```)
- Finds first balanced `{...}` object within text
- Attempts parse with detailed error messages
- Falls back to model-guided repair if JSON is malformed
- Never invents missing data (uses "NO CONSTA")

### Resumable Processing
- JSONL appends rather than overwrites (maintains progress)
- `--skip-existing` flag detects already-processed files
- Failed PDFs (extraction errors, LLM failures) still write minimal entries
- Graceful degradation: partial success > total failure

### Retry Strategy
- Max 4 retries per PDF
- Exponential backoff: `(1.8 ^ attempt) + (0.1 * attempt)` seconds
- Retries only on transient failures (timeout, rate limits)
- Permanent failures (invalid PDF, model errors) stop retrying

### CSV Flattening
- Nested structures (lists, dicts) saved as JSON strings (not lost to CSV limitations)
- Maintains original information density while enabling spreadsheet analysis
- Preferred column order ensures critical fields appear first

## Development Workflow

### Installation & Setup

```bash
# Using uv (recommended)
uv pip install openai pypdf pandas tqdm python-dotenv

# Using pip
pip install openai pypdf pandas tqdm python-dotenv

# Set environment variable
export OPENAI_API_KEY="sk-..."
# OR create .env file in project root
echo "OPENAI_API_KEY=sk-..." > .env
```

### Running the Pipeline

```bash
# Basic usage (processes all PDFs, outputs to ./output/)
python residenciafiscal.py --input ./pdfs --output ./output

# With specific model
python residenciafiscal.py --input ./pdfs --output ./output --model gpt-4

# Limit pages per PDF (useful for testing)
python residenciafiscal.py --input ./pdfs --output ./output --max-pages 10

# Resume interrupted run (skips already-processed files)
python residenciafiscal.py --input ./pdfs --output ./output --skip-existing

# Custom output filenames
python residenciafiscal.py --input ./pdfs --output ./output --jsonl-name results.jsonl --csv-name results.csv
```

### Testing

No automated test suite exists. Testing is manual:

```bash
# Test with single PDF or small batch
python residenciafiscal.py --input ./test_pdfs --output ./test_output --model gpt-4-mini

# Inspect output
head -1 ./test_output/output.jsonl | python -m json.tool

# Check CSV structure
head ./test_output/output.csv
```

### Code Quality

No linter/formatter is configured. Follow these conventions:
- **4-space indentation** (Python standard)
- **Type hints** where practical (dataclass, function signatures)
- **Docstrings** for functions (especially public APIs)
- **Snake_case** for variables, functions, and modules
- **PascalCase** for classes

## Common Development Tasks

### Adding a New Evidence Category

1. Define in `prompt.py` under "PRUEBAS / INDICIOS (CATÁLOGO NORMALIZADO)"
2. Add example types and sub-categories
3. Update schema in JSON output format section if needed
4. Update `flatten_for_csv()` in `residenciafiscal.py` if new top-level fields

Example:
```python
# In prompt.py:
# 13) DEUDA_TRIBUTARIA
#    - sentencias previas, recursos, multas, embargos, etc.

# Then update ensure_required_keys() and flatten_for_csv() if needed
```

### Modifying the Extraction Prompt

Edit `SYSTEM_PROMPT` in `prompt.py`:
- Critical: Keep JSON format example valid (single-line output required)
- Critical: All field names must match the JSON schema
- Keep "NO CONSTA" as fallback for missing data
- Use "SI/NO/NO CONSTA" for boolean/ternary fields

After changes:
```bash
python residenciafiscal.py --input ./test_pdfs --output ./test_output
```

### Handling Failed PDFs

Failed PDFs write entries with minimal data:
```json
{"archivo":"failed.pdf","observaciones":"ERROR_PROCESO: [error message]","confianza_extraccion":"BAJA","identificadores":{"ROJ":"NO CONSTA","ECLI":"NO CONSTA"},...}
```

To investigate:
1. Check PDF validity: `pypdf` may fail on corrupted PDFs
2. Check text extraction: some PDFs have no readable text (images only)
3. Increase `max_retries` or backoff multiplier for rate-limit issues

### Modifying CSV Output

Edit `flatten_for_csv()` function:
- Add new row keys for new fields
- Use `jdump()` helper to serialize complex types
- Update `preferred_order` list to control column sequence

## Dependencies & Versions

| Package | Version | Purpose |
|---------|---------|---------|
| openai | Latest | Responses API client |
| pypdf | Latest | PDF text extraction |
| pandas | Latest | DataFrame → CSV conversion |
| tqdm | Latest | Progress bar for PDF loop |
| python-dotenv | Latest | .env file loading |

No version pinning because project is research-focused (not production). Upgrading is generally safe.

## API Integration Details

### OpenAI Responses API Usage

Uses OpenAI's **Responses API** (not Chat Completions):
```python
resp = client.responses.create(
    model=args.model,
    instructions=system_prompt,  # System-level instructions
    input=user_input,            # Document text + filename
)
text_out = resp.output_text
```

- **Advantage**: Optimized for structured output (faster, cheaper than Chat)
- **Model support**: gpt-4-mini, gpt-4, gpt-5-mini, gpt-5.2, gpt-4.1 (as of Jan 2026)
- **Rate limits**: Standard OpenAI rate limits apply; exponential backoff handles throttling
- **Cost**: Charged per output token; long documents → higher costs

### Environment Variable

Must set `OPENAI_API_KEY` before running:
```bash
export OPENAI_API_KEY="sk-proj-..."
```

Or create `.env`:
```
OPENAI_API_KEY=sk-proj-...
```

Load with `load_dotenv()` at start of `main()`.

## File Structure

```
residenciafiscal/
├── residenciafiscal.py      # Main processing pipeline (392 lines)
├── prompt.py                # System prompt definition (131 lines)
├── sentencias/              # Directory for input PDFs (user-created)
├── output/                  # Default output directory (auto-created)
│   ├── output.jsonl         # Raw extracted data (one per line)
│   └── output.csv           # Flattened CSV export
├── README.md                # Minimal project description
└── .env                     # Local environment (gitignored)
```

## Important Constraints & Limitations

### PDF Extraction Limitations
- **OCR not included**: Only reads text PDFs (prints to PDF work; scans do not)
- **Page markers inserted**: `--- PÁGINA N ---` added before each page for LLM context
- **Max pages configurable**: `--max-pages` limits processing (useful for cost control)

### LLM Output Constraints
- **Single-line JSON required**: Cannot span multiple lines (validated in `safe_json_loads()`)
- **All fields must be present**: Missing fields trigger "NO CONSTA" fallback
- **Citation format strict**: Field must be `{"pagina":"...","texto":"..."}`

### CSV Flattening Trade-offs
- **Loss of nesting**: Complex structures become JSON strings (not ideal for Excel pivot tables)
- **Workaround**: Parse JSON in processing layer, or use JSONL directly for analysis

### Scale Considerations
- **Memory**: Entire dataset held in pandas DataFrame before CSV write (OK for <50K PDFs)
- **API costs**: Long documents → many tokens → higher costs (monitor with `--max-pages`)
- **Rate limiting**: Backoff handles this; exponential delay can be slow for large batches

## Debugging & Troubleshooting

### Empty or Missing Output

```bash
# Check if JSONL was created
ls -lh ./output/output.jsonl

# Check first few lines
head -3 ./output/output.jsonl | python -m json.tool

# If JSONL missing: ensure --output directory exists and is writable
mkdir -p ./output
```

### PDF Not Processed (--skip-existing)

```bash
# Remove existing JSONL to reprocess
rm ./output/output.jsonl
python residenciafiscal.py --input ./pdfs --output ./output
```

### JSON Parsing Failures

```bash
# Inspect raw output
# 1. Add print() in call_llm_extract() to see raw response
# 2. Check if response contains ```json...``` fences
# 3. Check if response is multi-line JSON (not allowed)
```

### Rate Limit or Timeout Errors

```bash
# Increase backoff multiplier (change line 130)
backoff_base: float = 2.5,  # Was 1.8

# Reduce batch size
python residenciafiscal.py --input ./pdfs --output ./output --max-pages 5
```

## Performance Notes

- **Average time per PDF**: 5-15 seconds (depends on length and model)
- **Cost per PDF**: $0.01-$0.10 (varies by model, document length)
- **Bottleneck**: LLM API latency (not Python code)
- **Optimization**: Parallel processing not implemented (would require async/threading)

## Future Enhancements

Potential improvements (not currently implemented):
1. **Parallel PDF processing** (asyncio, thread pool) to reduce wall-clock time
2. **Local LLM fallback** (Ollama, Llama 2) for cost reduction or offline use
3. **Auto-repair for common JSON errors** (missing commas, unescaped quotes)
4. **Keyword extraction** from frases_clave for full-text search indexing
5. **Schema validation** (Pydantic models) to ensure output completeness
6. **Progress persistence** (SQLite checkpoint) instead of JSONL append-only

## References

- **OpenAI API Docs**: https://platform.openai.com/docs
- **Responses API Guide**: https://platform.openai.com/docs/guides/responses
- **pypdf Documentation**: https://pypdf.readthedocs.io/
- **Spanish IRPF Law**: Real Decreto Legislativo 5/2004
