# Reasoning Effort Configuration

## Overview

The `residenciafiscal.py` script now supports OpenAI's **Reasoning Effort** parameter for GPT-5 models. This allows fine-tuning the balance between:
- **Speed**: How fast the model generates responses
- **Accuracy**: How thoroughly the model thinks through the problem
- **Cost**: More reasoning = higher token usage

## Configuration

### Default Setting

Located in `config.py`:

```python
REASONING_EFFORT = "medium"  # Options: low | medium | high | minimal
```

## Model Support

Reasoning Effort is **only** applied to GPT-5+ models:
- ✅ `gpt-5.2-2025-12-11`
- ✅ `gpt-5-mini-2025-08-07`
- ✅ `gpt-5-nano-2025-08-07`
- ✅ Any model string containing `"gpt-5"`

For other models (gpt-4, gpt-4-mini, etc.), the parameter is **automatically skipped**.

## Implementation Details

In `residenciafiscal.py`, the `call_llm_extract()` function:

```python
# Detect if model is GPT-5+
is_gpt5_model = any(gpt5 in model for gpt5 in [GPT_5, GPT_5_MINI, GPT_5_NANO, "gpt-5"])

# Build API call with reasoning_effort if applicable
create_kwargs = {
    "model": model,
    "instructions": system_prompt,
    "input": user_input,
}

if is_gpt5_model:
    create_kwargs["reasoning_effort"] = REASONING_EFFORT

resp = client.responses.create(**create_kwargs)
```

## Usage

### Command Line

```bash
# Uses default reasoning effort (medium)
python residenciafiscal.py --model gpt-5-mini

# With custom model
python residenciafiscal.py --model gpt-5 --max-pages 5
```

### Changing Reasoning Effort

Edit `config.py`:

```python
# config.py
REASONING_EFFORT = "high"  # For maximum accuracy (slower, more expensive)
```

Then run normally:

```bash
python residenciafiscal.py
```

## Effort Levels Comparison

| Level | Speed | Accuracy | Cost | Use Case |
|-------|-------|----------|------|----------|
| **minimal** | ⚡ Very Fast | ⚠️ Low | $ Cheap | Quick testing |
| **low** | 🚀 Fast | 📊 Medium | $$ Low | Initial analysis |
| **medium** | ⚙️ Balanced | 🎯 High | $$$ Medium | **Default - Recommended** |
| **high** | 🐢 Slow | 🔍 Very High | $$$$ High | Complex documents |

## Performance Impact

Based on OpenAI's guidance:

- **medium** (default): 
  - ~20-30% more tokens than minimal
  - Good balance for legal document analysis
  - ~2-3x the cost of gpt-4-mini but better accuracy

- **high**:
  - ~50-100% more tokens than minimal
  - Recommended for critical analysis
  - 5-10x the cost of gpt-4-mini

## Example: Cost Estimation

Processing 100 PDFs (~5 pages each):

```
Model: gpt-5-mini
Effort: medium

Estimated:
- Input tokens: 5,000 per PDF
- Output tokens: 500 per PDF (with reasoning overhead)
- Total: ~550,000 tokens per run
- Cost: ~$2.75 at typical GPT-5 pricing
```

## Troubleshooting

### Error: "reasoning_effort not supported for this model"

**Solution**: The model doesn't support reasoning_effort.
- Change to GPT-5+ in config.py
- Or edit the script to force-disable it

### Timeout errors with high reasoning effort

**Solution**: Increase retry backoff or use lower effort:

```python
# config.py
REASONING_EFFORT = "low"  # Instead of "high"
```

## Future Enhancements

Planned features:
- [ ] CLI flag to override REASONING_EFFORT: `--reasoning low|medium|high|minimal`
- [ ] Adaptive reasoning effort based on document complexity
- [ ] Cost estimation before processing
- [ ] Support for other models' equivalent parameters

## References

- [OpenAI Reasoning Effort Docs](https://platform.openai.com/docs/)
- [GPT-5 API Reference](https://platform.openai.com/docs/api-reference)
