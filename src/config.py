"""Catálogos jurídicos y conexión de proveedores compartidos por la aplicación.

La política del modelo conversacional vive en ``chat_model_policy``. Este
módulo no define modelos para analizar sentencias: el corpus se prepara offline
mediante Python + agente.
"""

from llm_gateway.models import resolve_provider

# `llm_gateway` no lee el entorno. La aplicación entrega las credenciales al
# composition root del chat.
PROVIDER_API_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}

# Compatibilidad de routing para IDs históricos que todavía puede recibir el
# gateway del chat. No describe un pipeline de análisis de sentencias.
LEGACY_MODEL_PREFIXES: tuple[tuple[str, str], ...] = (("groq-", "groq"),)


def detect_provider(model_id: str) -> str:
    """Resuelve el proveedor de un modelo usando primero el catálogo común."""
    declared = resolve_provider(model_id)
    if declared is not None:
        return declared

    lowered = model_id.lower()
    for prefix, provider in LEGACY_MODEL_PREFIXES:
        if lowered.startswith(prefix):
            return provider
    return "openrouter"


VALID_CRITERIOS = {
    "CRIT_183_DIAS",
    "CRIT_AUSENCIAS_ESPORADICAS",
    "CRIT_CENTRO_INTERESES_ECONOMICOS",
    "CRIT_CENTRO_INTERESES_VITALES",
    "CRIT_PRESUNCION_FAMILIA",
    "CRIT_CDI_TIEBREAKER",
    "CRIT_OTRO",
}

VALID_CATEGORIAS_PRUEBA = {
    "PRESENCIA_FISICA_Y_DESPLAZAMIENTOS",
    "VIVIENDA_Y_USO_EFECTIVO",
    "SUMINISTROS_Y_CONSUMOS_DOMESTICOS",
    "CONSUMOS_FINANCIEROS",
    "FAMILIA_Y_ENTORNO_PERSONAL",
    "SALUD_Y_SERVICIOS_PERSONALES",
    "ACTIVIDAD_ECONOMICA_Y_GESTION",
    "DOCUMENTACION_FISCAL_EXTRANJERA",
    "VINCULOS_ADMINISTRATIVOS_EN_ESPANA",
    "TRAZAS_DIGITALES",
    "TESTIFICAL_Y_PERICIAL",
    "OTROS",
}

VALID_TIEBREAKER_PASOS = {
    "VIVIENDA_PERMANENTE",
    "CENTRO_INTERESES_VITALES",
    "MORADA_HABITUAL",
    "NACIONALIDAD",
    "ACUERDO_MUTUO",
    "NO_CONSTA",
    "NO_APLICA",
}

VALID_RESULTADO_FINAL = {
    "GANA_AEAT",
    "GANA_CONTRIBUYENTE",
    "PARCIAL",
    "RETROACCION",
    "INADMISION",
    "OTROS",
    "FUERA_DE_ALCANCE",
}
