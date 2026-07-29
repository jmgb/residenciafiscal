"""Adapter for gpt_request function - simplified version for residenciafiscal.py

This module provides a simplified interface to gpt_request() function
adapted for the residenciafiscal project.
"""

import logging
import warnings
from typing import Any

# Suppress deprecated warnings from optional dependencies
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*google.generativeai.*")

# Suppress root logger errors from failed optional imports
logging.getLogger().setLevel(logging.WARNING)
root_logger = logging.getLogger()
root_logger.handlers = [h for h in root_logger.handlers if not isinstance(h, logging.StreamHandler)]

# Always use direct OpenAI client in this project.
HAS_UNIVERSAL_GPT = False
universal_gpt_request = None


def _detect_provider(ai_model: str) -> str:
    ai_model_lower = ai_model.lower()
    if "gemini" in ai_model_lower or "claude" in ai_model_lower:
        return "gemini"
    if "groq" in ai_model_lower or "mixtral" in ai_model_lower or "llama" in ai_model_lower:
        return "groq"
    return "openai"


async def gpt_request_for_sentencia(
    ai_model: str,
    system_prompt: str,
    pdf_text: str,
    logger: logging.Logger,
    temperature: float = 0,
    response_format: str = "json_object",
    reasoning_effort: str | None = None,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    """Simplified gpt_request wrapper for sentencia analysis.

    Args:
        ai_model: Model identifier (e.g., "gpt-5-mini")
        system_prompt: System prompt with analysis instructions
        pdf_text: Extracted PDF text with page markers
        logger: Logger instance
        temperature: Temperature parameter (0-1)
        response_format: "json_object" or "text"
        reasoning_effort: "low", "medium", "high" (for GPT-5+)
        max_tokens: Maximum tokens to generate

    Returns:
        dict: Response with parsed data or error information (includes 'tokens_in', 'tokens_out', 'cost_usd')
    """

    import json
    import os
    import time

    from model_pricing import calculate_cost as calc_cost_fn

    start_time = time.perf_counter()

    def add_execution_metadata(result_dict: dict) -> dict:
        """Añade metadata de ejecución al resultado."""
        elapsed = round(time.perf_counter() - start_time, 1)
        result_dict["tiempo_ejecucion"] = f"{ai_model} - {elapsed}s"
        return result_dict

    request_timeout = 200

    try:
        from openai import AsyncOpenAI

        provider = _detect_provider(ai_model)

        if provider == "gemini":
            try:
                import google.generativeai as genai
            except Exception as e:
                return {
                    "error": f"Gemini client unavailable: {e}",
                    "detail": "google-generativeai not installed",
                }

            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                return {
                    "error": "GEMINI_API_KEY not set",
                    "detail": "No API key available for Gemini models",
                }

            genai.configure(api_key=api_key)
            try:
                model = genai.GenerativeModel(model_name=ai_model, system_instruction=system_prompt)
                prompt_text = pdf_text
            except TypeError:
                model = genai.GenerativeModel(model_name=ai_model)
                prompt_text = f"{system_prompt}\n\n{pdf_text}"

            generation_config: dict[str, Any] = {"temperature": temperature}
            if max_tokens is not None:
                generation_config["max_output_tokens"] = max_tokens
            if response_format == "json_object":
                generation_config["response_mime_type"] = "application/json"

            try:
                response = await model.generate_content_async(
                    prompt_text,
                    generation_config=generation_config,  # type: ignore[arg-type]
                )
            except AttributeError:
                # Fallback síncrono para versiones antiguas del SDK sin *_async
                response = model.generate_content(  # type: ignore[assignment]
                    prompt_text,
                    generation_config=generation_config,  # type: ignore[arg-type]
                )
            except TypeError:
                response = await model.generate_content_async(prompt_text)

            response_text = getattr(response, "text", "") or ""

            tokens_in = 0
            tokens_out = 0
            cost_usd = 0.0
            usage = getattr(response, "usage_metadata", None)
            if usage:
                tokens_in = getattr(usage, "prompt_token_count", 0) or 0
                tokens_out = getattr(usage, "candidates_token_count", 0) or 0
                cost_info = calc_cost_fn(ai_model, tokens_in, tokens_out)
                cost_usd = float(cost_info.get("total_cost", 0.0) or 0.0)  # type: ignore[arg-type]
                logger.info(
                    f"💰 Gemini - Tokens: {tokens_in} entrada, {tokens_out} salida, ${cost_usd:.4f}"
                )
            else:
                logger.info("💰 Gemini - Uso de tokens no disponible")

            if response_format == "json_object":
                try:
                    parsed = json.loads(response_text)
                    parsed["cost_usd"] = cost_usd
                    return add_execution_metadata(parsed)
                except json.JSONDecodeError:
                    parsed = safe_json_parse(response_text, logger, ai_model, "residenciafiscal")
                    parsed["cost_usd"] = cost_usd
                    return add_execution_metadata(parsed)

            result = {"response": response_text, "cost_usd": cost_usd}
            return add_execution_metadata(result)

        if provider == "groq":
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                return {
                    "error": "GROQ_API_KEY not set",
                    "detail": "No API key available for Groq models",
                }
            client = AsyncOpenAI(
                api_key=api_key,
                base_url="https://api.groq.com/openai/v1",
                timeout=request_timeout,
            )
        else:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return {
                    "error": "OPENAI_API_KEY not set",
                    "detail": "No API key available for OpenAI models",
                }
            client = AsyncOpenAI(api_key=api_key, timeout=request_timeout)

        # Prepare kwargs for the API call
        kwargs: dict[str, Any] = {
            "model": ai_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": pdf_text},
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

        # Add reasoning effort for GPT-5 models (OpenAI only)
        if (
            provider == "openai"
            and reasoning_effort
            and ("gpt-5" in ai_model.lower() or "o1" in ai_model.lower())
        ):
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
            cost_usd = float(cost_info.get("total_cost", 0.0) or 0.0)  # type: ignore[arg-type]
            label = "Groq" if provider == "groq" else "OpenAI"
            logger.info(
                f"💰 {label} - Tokens: {tokens_in} entrada, {tokens_out} salida, ${cost_usd:.4f}"
            )
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
        logger.error(f"LLM request failed: {e}")
        return {"error": str(e), "detail": "LLM request failed"}


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
                    json_content = cleaned_text[: last_brace + 1]
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
