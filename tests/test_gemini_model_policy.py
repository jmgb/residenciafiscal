from config import GEMINI_FLASH


def test_text_gemini_models_use_new_supported_ids():
    """`GEMINI_PRO` desapareció: era un segundo nombre para este mismo id.

    Dos constantes con el mismo valor prometen dos modelos donde solo hay uno,
    y en la allowlist de la API colapsaban en una única entrada.
    """
    assert GEMINI_FLASH == "gemini-3.6-flash"
