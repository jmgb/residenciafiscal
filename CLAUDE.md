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
- Asynchronous processing of multiple PDFs concurrently
- Reads PDF files from input directory
- Extracts text with page markers (`--- PÁGINA N ---`)
- Calls universal `gpt_request()` function via `ai_service_adapter.py`
- Supports multiple AI providers: OpenAI, Groq, Gemini, OpenRouter with automatic fallback
- Intelligent provider detection from model name
- Validates required API keys at startup (fail-fast)
- Repairs malformed JSON responses with multiple parsing strategies
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

# Resume interrupted run (skips already-processed files)
python residenciafiscal.py --input ./pdfs --output ./output --skip-existing

# Custom output filenames
python residenciafiscal.py --input ./pdfs --output ./output --jsonl-name results.jsonl --csv-name results.csv
```

### Testing

**Automated single-PDF test suite** available in `/test/` directory:

```bash
# Quick test with single PDF (recommended before full batch)
./test/run_test.sh

# Or run directly with Python
python test/test_single_pdf.py
```

The test script:
- Creates temporary input/output directories (auto-cleanup)
- Copies 1 PDF from `sentencias/` folder
- Runs full pipeline (all pages)
- Displays formatted JSONL and CSV output
- Shows extraction quality metrics

**Manual testing** for development:

```bash
# Test with single PDF
python residenciafiscal.py --input ./test_pdfs --output ./test_output

# Inspect JSONL output
head -1 ./test_output/analisis_*.jsonl | python -m json.tool

# Check CSV structure
head ./test_output/analisis_*.csv
```

See `test/README.md` for detailed testing documentation.

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

### Universal AI Client Integration

Uses **universal `gpt_request()` function** from `ai_client_service.py`:

```python
# Called via ai_service_adapter.py
result = await gpt_request_for_sentencia(
    ai_model=model_name,
    system_prompt=SYSTEM_PROMPT,
    pdf_text=extracted_text,
    logger=logger,
    temperature=0,
    response_format="json_object",
    reasoning_effort=REASONING_EFFORT if "gpt-5" in model else None,
)
```

**Key Features**:
- **Multi-provider support**: OpenAI (GPT-5+), Groq, Gemini, OpenRouter
- **Automatic provider detection**: Parses model name to determine provider
- **Smart reasoning**: Adds `reasoning_effort` for GPT-5+ models automatically
- **Robust JSON parsing**: Multiple strategies to repair malformed responses
- **Automatic fallback**: Switches providers if one fails
- **Error recovery**: Detailed logging and graceful degradation
- **Async support**: Non-blocking API calls for better concurrency

**Supported Models**:
- OpenAI: `gpt-5`, `gpt-5-mini`, `gpt-4`, `gpt-4-turbo`, `o1-preview`
- Groq: `groq-mixtral`, `llama-*` models
- Gemini: `gemini-*` models
- OpenRouter: Any model via OpenRouter API

**Rate Limits & Cost**:
- Each provider has standard rate limits
- Costs vary by model and token usage
- Document length controls token budget (all pages are processed)
- `REASONING_EFFORT` setting impacts cost/quality trade-off

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
├── residenciafiscal.py      # Main processing pipeline (async with gpt_request integration)
├── ai_service_adapter.py    # Wrapper for universal gpt_request() function
├── config.py                # Centralized configuration (models, paths, constants)
├── prompt.py                # System prompt definition
├── sentencias/              # Directory for input PDFs
├── output/                  # Default output directory (auto-created)
│   ├── output.jsonl         # Raw extracted data (one JSON per line)
│   └── output.csv           # Flattened CSV export
├── test/                    # Test suite directory
│   ├── test_single_pdf.py   # Automated single-PDF test script
│   ├── run_test.sh          # Convenience test runner shell script
│   └── README.md            # Testing documentation
├── .env                     # Local environment (gitignored)
├── .env.example             # Environment template
├── requirements.txt         # Python dependencies
├── CLAUDE.md                # This file
└── README.md                # Project overview
```

## Important Constraints & Limitations

### PDF Extraction Limitations
- **OCR not included**: Only reads text PDFs (prints to PDF work; scans do not)
- **Page markers inserted**: `--- PÁGINA N ---` added before each page for LLM context
- **All pages processed**: El sistema lee el PDF completo para evitar pérdida de información

### LLM Output Constraints
- **Single-line JSON required**: Cannot span multiple lines (validated in `safe_json_loads()`)
- **All fields must be present**: Missing fields trigger "NO CONSTA" fallback
- **Citation format strict**: Field must be `{"pagina":"...","texto":"..."}`

### CSV Flattening Trade-offs
- **Loss of nesting**: Complex structures become JSON strings (not ideal for Excel pivot tables)
- **Workaround**: Parse JSON in processing layer, or use JSONL directly for analysis

### Scale Considerations
- **Memory**: Entire dataset held in pandas DataFrame before CSV write (OK for <50K PDFs)
- **API costs**: Long documents → many tokens → higher costs (monitoriza por modelo)
- **Rate limiting**: Backoff handles this; exponential delay can be slow for large batches

## Debugging & Troubleshooting

### Empty or Missing Output

```bash
# Check if JSONL was created
ls -lh ./output/analisis_*.jsonl

# Check first few lines
head -3 ./output/analisis_*.jsonl | python -m json.tool

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
python residenciafiscal.py --input ./pdfs --output ./output
```

## Performance Notes

- **Average time per PDF**: 5-20 seconds (depends on length, model, reasoning_effort)
- **Cost per PDF**: $0.01-$0.10+ (varies by provider and model; GPT-5 with reasoning_effort costs more)
- **Bottleneck**: LLM API latency (async helps with I/O parallelization)
- **With async**: Multiple PDFs can be processed with better I/O concurrency
- **Optimization**: Ajusta `BATCH_SIZE` y el modelo para balancear coste/tiempo

## Recent Enhancements (Jan 2026)

Recently implemented improvements:
1. ✅ **Async processing** - Full asyncio support for concurrent PDF processing
2. ✅ **Multi-provider support** - OpenAI, Groq, Gemini, OpenRouter with automatic fallback
3. ✅ **Client initialization** - Validates API keys at startup, provider auto-detection
4. ✅ **Centralized configuration** - All settings in `config.py` (models, paths, constants)
5. ✅ **Automated testing** - Single-PDF test suite for quick validation
6. ✅ **Reasoning effort** - Intelligent GPT-5+ reasoning control via config

## Future Enhancement Ideas

Potential improvements (not currently implemented):
1. **Concurrent PDF processing** - Batch multiple PDFs in parallel
2. **Local LLM fallback** (Ollama, Llama 2) for cost reduction or offline use
3. **Schema validation** (Pydantic models) to ensure output completeness
4. **Keyword extraction** from frases_clave for full-text search indexing
5. **Progress persistence** (SQLite checkpoint) for large-scale runs
6. **Cost estimation** - Pre-calculate total cost before processing

## References

- **OpenAI API Docs**: https://platform.openai.com/docs
- **Responses API Guide**: https://platform.openai.com/docs/guides/responses
- **pypdf Documentation**: https://pypdf.readthedocs.io/
- **Spanish IRPF Law**: Real Decreto Legislativo 5/2004
