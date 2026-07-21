from config import GEMINI_FLASH, GEMINI_PRO


def test_text_gemini_models_use_new_supported_ids():
    assert GEMINI_PRO == "gemini-3.6-flash"
    assert GEMINI_FLASH == "gemini-3.6-flash"
