"""Adapter for gpt_request function - simplified version for residenciafiscal.py

This module provides a simplified interface to gpt_request() function
adapted for the residenciafiscal project.
"""

import logging
from typing import Any, Optional

try:
    # Try importing from app structure if available
    from app.services.ai_client_service import gpt_request as universal_gpt_request
    HAS_UNIVERSAL_GPT = True
except ImportError:
    HAS_UNIVERSAL_GPT = False


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
        dict: Response with parsed data or error information
    """
    
    if not HAS_UNIVERSAL_GPT:
        # Fallback: return error indicating gpt_request not available
        return {
            "error": "gpt_request not available",
            "detail": "Universal AI service not accessible",
            "archive": "unknown"
        }
    
    # Call universal gpt_request with adapted parameters
    try:
        result = await universal_gpt_request(
            ai_model=ai_model,
            system_prompt=system_prompt,
            user_message=pdf_text,
            user_examples=[],  # No examples for residencia fiscal
            assistant_examples=[],
            logger=logger,
            temperature=temperature,
            response_format=response_format,
            source="residenciafiscal_processor",
            client=None,  # Use default client
            file_ids=None,
            file_paths=None,
            max_tokens=max_tokens,
            reasoning_effort=reasoning_effort,
        )
        return result
    except Exception as e:
        logger.error(f"Error calling gpt_request: {e}")
        return {
            "error": str(e),
            "archive": "unknown"
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
