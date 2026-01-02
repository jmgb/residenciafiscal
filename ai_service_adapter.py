"""Adapter for gpt_request function - simplified version for residenciafiscal.py

This module provides a simplified interface to gpt_request() function
adapted for the residenciafiscal project.
"""

import logging
import sys
import warnings
from pathlib import Path
from typing import Any, Optional

# Suppress deprecated warnings from optional dependencies
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*google.generativeai.*")

# Suppress root logger errors from failed optional imports
logging.getLogger().setLevel(logging.WARNING)
root_logger = logging.getLogger()
root_logger.handlers = [h for h in root_logger.handlers if not isinstance(h, logging.StreamHandler)]

# Try to import gpt_request from multiple possible locations
HAS_UNIVERSAL_GPT = False
universal_gpt_request = None

try:
    # Try standard app structure first
    from app.services.ai_client_service import gpt_request as universal_gpt_request
    HAS_UNIVERSAL_GPT = True
except ImportError as e1:
    # Try adding parent project to path and import from there
    try:
        # Get absolute path to backend project
        # File: /home/ubuntu/ai_projects/residenciafiscal/ai_service_adapter.py
        # Backend: /home/ubuntu/ai_projects/apps/backend
        current_file = Path(__file__).resolve()
        parent_backend = current_file.parent.parent / "apps" / "backend"

        if parent_backend.exists() and parent_backend.is_dir():
            sys.path.insert(0, str(parent_backend))
            try:
                # Suppress warnings during import
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore")
                    # Suppress logging during import
                    old_level = logging.root.level
                    logging.root.setLevel(logging.CRITICAL)
                    try:
                        from app.services.ai_client_service import gpt_request as universal_gpt_request
                        HAS_UNIVERSAL_GPT = True
                    finally:
                        logging.root.setLevel(old_level)
            except Exception as e2:
                # Silently fail - we'll use OpenAI fallback
                pass
    except Exception as e3:
        # Silently fail
        pass


async def gpt_request_for_sentencia(
    ai_model: str,
    system_prompt: str,
    pdf_text: str,
    logger: logging.Logger,
    temperature: float = 0,
    response_format: str = "json_object",
    reasoning_effort: Optional[str] = None,
    max_tokens: Optional[int] = None,
) -> dict[str, Any]:
    """Simplified gpt_request wrapper for sentencia analysis.

    Args:
        ai_model: Model identifier (e.g., "gpt-5-mini")
        system_prompt: System prompt with analysis instructions
        pdf_text: Extracted PDF text with page markers
        logger: Logger instance
        temperature: Temperature parameter (0-1)
        response_format: "json_object" or "text"
        reasoning_effort: "minimal", "low", "medium", "high" (for GPT-5+)
        max_tokens: Maximum tokens to generate

    Returns:
        dict: Response with parsed data or error information (includes 'tokens_in', 'tokens_out', 'cost_usd')
    """
    
    import os
    import json
    import time
    from model_pricing import calculate_cost as calc_cost_fn

    start_time = time.perf_counter()

    def add_execution_metadata(result_dict: dict) -> dict:
        """Añade metadata de ejecución al resultado."""
        elapsed = round(time.perf_counter() - start_time, 1)
        result_dict["tiempo_ejecucion"] = f"{ai_model} - {elapsed}s"
        return result_dict

    # Try using universal gpt_request if available
    request_timeout = 200

    if HAS_UNIVERSAL_GPT and universal_gpt_request:
        try:
            try:
                result = await universal_gpt_request(
                    ai_model=ai_model,
                    system_prompt=system_prompt,
                    user_message=pdf_text,
                    user_examples=[],
                    assistant_examples=[],
                    logger=logger,
                    temperature=temperature,
                    response_format=response_format,
                    source="residenciafiscal_processor",
                    client=None,
                    file_ids=None,
                    file_paths=None,
                    max_tokens=max_tokens,
                    reasoning_effort=reasoning_effort,
                    timeout=request_timeout,
                )
            except TypeError:
                result = await universal_gpt_request(
                    ai_model=ai_model,
                    system_prompt=system_prompt,
                    user_message=pdf_text,
                    user_examples=[],
                    assistant_examples=[],
                    logger=logger,
                    temperature=temperature,
                    response_format=response_format,
                    source="residenciafiscal_processor",
                    client=None,
                    file_ids=None,
                    file_paths=None,
                    max_tokens=max_tokens,
                    reasoning_effort=reasoning_effort,
                )
            return add_execution_metadata(result)
        except Exception as e:
            logger.warning(f"Universal gpt_request failed, using fallback: {e}")

    # Fallback: Use OpenAI directly for GPT models
    try:
        from openai import AsyncOpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {
                "error": "OPENAI_API_KEY not set",
                "detail": "No API key available for OpenAI models"
            }

        client = AsyncOpenAI(api_key=api_key, timeout=request_timeout)

        # Prepare kwargs for the API call
        kwargs = {
            "model": ai_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": pdf_text}
            ],
        }

        # Add temperature only if not 0 (some models like gpt-5 don't support 0)
        # Use 1 as default for models that don't support 0
        if temperature != 0:
            kwargs["temperature"] = temperature
        # For models that need temperature, use 1 as minimum instead of 0
        elif "gpt-5" in ai_model.lower() or "o1" in ai_model.lower():
            kwargs["temperature"] = 1
        else:
            kwargs["temperature"] = temperature

        # Add response format if specified
        if response_format == "json_object":
            kwargs["response_format"] = {"type": "json_object"}

        # Add reasoning effort for GPT-5 models
        if reasoning_effort and ("gpt-5" in ai_model.lower() or "o1" in ai_model.lower()):
            kwargs["reasoning_effort"] = reasoning_effort

        # Add max tokens if specified
        if max_tokens:
            kwargs["max_tokens"] = max_tokens

        response = await client.chat.completions.create(**kwargs)

        # Extract response text
        response_text = response.choices[0].message.content

        # Extract token usage and calculate cost
        tokens_in = 0
        tokens_out = 0
        cost_usd = 0.0

        if response.usage:
            tokens_in = response.usage.prompt_tokens or 0
            tokens_out = response.usage.completion_tokens or 0
            cost_info = calc_cost_fn(ai_model, tokens_in, tokens_out)
            cost_usd = cost_info.get("total_cost", 0.0) or 0.0
            logger.info(f"💰 Fallback OpenAI - Tokens: {tokens_in} entrada, {tokens_out} salida, ${cost_usd:.4f}")
        else:
            logger.warning(f"⚠️ response.usage es None para {ai_model}")

        # Try to parse as JSON if requested
        if response_format == "json_object":
            try:
                parsed = json.loads(response_text)
                # Add cost info
                parsed["cost_usd"] = cost_usd
                return add_execution_metadata(parsed)
            except json.JSONDecodeError:
                # Return as-is if not valid JSON
                parsed = safe_json_parse(response_text, logger, ai_model, "residenciafiscal")
                parsed["cost_usd"] = cost_usd
                return add_execution_metadata(parsed)

        result = {"response": response_text}
        result["cost_usd"] = cost_usd
        return add_execution_metadata(result)

    except Exception as e:
        logger.error(f"Fallback gpt_request failed: {e}")
        return {
            "error": str(e),
            "detail": "Both universal and OpenAI fallback failed"
        }


def safe_json_parse(
    text: str,
    logger: logging.Logger,
    ai_model: str = "unknown",
    source: str = "residenciafiscal",
) -> dict[str, Any]:
    """Safe JSON parsing with fallback handling.
    
    Attempts to parse JSON with multiple strategies:
    1. Direct JSON parsing
    2. Fix missing opening brace
    3. Extract JSON between first '{' and last '}'
    4. Return as text with error flag
    """
    import json
    
    # Clean text of backticks
    cleaned_text = text.strip()
    if cleaned_text.endswith("```"):
        cleaned_text = cleaned_text[:-3].strip()
    if cleaned_text.startswith("```json"):
        cleaned_text = cleaned_text[7:].strip()
    elif cleaned_text.startswith("```"):
        cleaned_text = cleaned_text[3:].strip()
    
    # Try direct parsing
    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError:
        pass
    
    # Try fixing missing opening brace
    if cleaned_text and not cleaned_text.startswith("{") and "}" in cleaned_text:
        if '"' in cleaned_text and ":" in cleaned_text:
            try:
                last_brace = cleaned_text.rfind("}")
                if last_brace != -1:
                    json_content = cleaned_text[:last_brace + 1]
                    fixed_json = "{" + json_content
                    result = json.loads(fixed_json)
                    logger.debug(f"✅ JSON fixed for {ai_model} - added missing '{{' at start")
                    return result
            except json.JSONDecodeError:
                pass
    
    # Try extracting between braces
    start_idx = cleaned_text.find("{")
    end_idx = cleaned_text.rfind("}") + 1
    if start_idx != -1 and end_idx > start_idx:
        json_str = cleaned_text[start_idx:end_idx]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    # Return error response
    logger.error(f"❌ JSON parse failed for {ai_model}: {text[:200]}...")
    return {
        "text": text,
        "_json_parse_error": True,
        "ai_model": ai_model,
        "source": source,
    }
