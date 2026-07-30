"""
config.py
Configuración centralizada para residenciafiscal.py
Externaliza variables, rutas y parámetros de LLM en un solo lugar.
"""

from pathlib import Path
from typing import Any

from llm_gateway.models import resolve_provider

# ============================================================================
# RUTAS POR DEFECTO
# ============================================================================

# Ruta base del proyecto
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Directorio donde se encuentran las sentencias PDF
DEFAULT_INPUT_DIR = PROJECT_ROOT / "sentencias"

# Directorio donde se guardan los resultados
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"

# Archivo con lista de sentencias clave (procesadas con modelo premium)
KEY_SENTENCIAS_FILE = DEFAULT_INPUT_DIR / "sentencias_CLAVE.txt"

# ============================================================================
# NOMBRES DE ARCHIVOS DE SALIDA
# ============================================================================

DEFAULT_JSONL_NAME = "analisis.jsonl"
DEFAULT_CSV_NAME = "analisis.csv"

# ============================================================================
# CONFIGURACIÓN DE OPENAI
# ============================================================================

# Modelos OpenAI disponibles
GPT_4_MINI = "gpt-4-mini"
GPT_4 = "gpt-4"
GPT_4_TURBO = "gpt-4-turbo"
GPT_5 = "gpt-5.6-sol"
GPT_5_MINI = "gpt-5.6-luna"
GPT_5_NANO = "gpt-5.6-luna"

# Modelos Gemini (si se implementa soporte)
GEMINI_PRO = "gemini-3.6-flash"
GEMINI_FLASH = "gemini-3.6-flash"

# Parámetro de esfuerzo de razonamiento para GPT-5 (low|medium|high)
# Mayor esfuerzo = mayor precisión pero más lento y caro
REASONING_EFFORT = "medium"

# Modelo por defecto a usar
DEFAULT_MODEL = GPT_5_MINI
SENTENCIA_CLAVE_MODEL = GPT_5


# Credenciales por proveedor. Las claves son de la aplicación: `llm_gateway` no
# lee el entorno, así que alguien de este lado tiene que decidir qué entregarle.
PROVIDER_API_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}


# Ids heredados que el catálogo del paquete no reconoce. Se declaran como
# **prefijos**, no como subcadenas, porque el registro del gateway enruta por
# prefijo: una regla que acertase aquí y no allí validaría la credencial de un
# proveedor y dejaría la llamada sin adaptador que la sirva, con un error que
# ni siquiera menciona la credencial. `gateway_setup` registra estos mismos
# prefijos para que las dos caras no puedan discrepar.
LEGACY_MODEL_PREFIXES: tuple[tuple[str, str], ...] = (("groq-", "groq"),)


def detect_provider(ai_model: str) -> str:
    """Resuelve el proveedor a partir del ID del modelo.

    La autoridad es el catálogo del paquete, que es también el que usa el
    registro del gateway para elegir adaptador. Mantener aquí una segunda tabla
    completa permitiría que ambas discrepasen, y una discrepancia significa
    validar una clave y llamar a otro proveedor: `openai/gpt-oss-120b` lo sirve
    Groq pese a su prefijo.

    Lo único que se añade al catálogo es `LEGACY_MODEL_PREFIXES`, y el último
    recurso histórico: OpenRouter, por donde llegaba lo que no se identificaba
    de otro modo. Ese último recurso es una conjetura, no una promesa —si el
    registro tampoco sabe enrutar el id, la llamada falla al resolverla, antes
    de gastar nada.
    """
    declared = resolve_provider(ai_model)
    if declared is not None:
        return declared

    model = ai_model.lower()
    for prefix, provider in LEGACY_MODEL_PREFIXES:
        if model.startswith(prefix):
            return provider
    return "openrouter"


# ============================================================================
# PARÁMETROS DE EXTRACCIÓN DE PDF
# ============================================================================

# Formato del marcador de página en el texto extraído
PAGE_MARKER_FMT = "\n\n--- PÁGINA {page_num} ---\n\n"

# Máximo de archivos PDF a procesar (0 = sin límite)
# Útil para pruebas rápidas con 1, 5, 10 archivos, etc.
DEFAULT_MAX_FILES = 0

# ============================================================================
# PROCESAMIENTO EN PARALELO
# ============================================================================

# Tamaño del batch: cuántos PDFs procesar en paralelo simultáneamente
# Mayor = más rápido pero más carga en API (respeta rate limits)
BATCH_SIZE = 10

# ============================================================================
# VALORES PREDETERMINADOS PARA CAMPOS FALTANTES
# ============================================================================

# Valor usado cuando un campo no se encuentra en el documento
DEFAULT_MISSING_VALUE = "NO CONSTA"

# ============================================================================
# CONFIGURACIÓN DE LOGGING
# ============================================================================

# Mostrar detalles de progreso (tqdm)
SHOW_PROGRESS_BAR = True

# Nivel de verbosidad (podría ser expandido a logging formal)
VERBOSE = False

# ============================================================================
# ENUMS VÁLIDOS (para validación de schema)
# ============================================================================

# Control de limpieza de schema: si es False, no se eliminan keys extra
ENFORCE_ALLOWED_KEYS = False

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

# Keys permitidas en el JSON (para schema clean)
ALLOWED_KEYS = {
    "archivo",
    "identificadores",
    "organo",
    "fecha_resolucion",
    "es_caso_residencia_irpf",
    "motivo_fuera_de_alcance",
    "ejercicios_afectados",
    "pais_alegado_residencia_pf",
    "pais_CDI_aplicado",
    "se_invoca_CDI",
    "tiebreaker_paso_decisivo",
    "Criterios_residencia_detectados",
    "Criterio_decisivo",
    "resumen_criterios",
    # Nuevos campos de razonamiento judicial
    "doctrina_citada",
    "carga_prueba",
    "razonamiento_residencia",
    # Pruebas
    "Pruebas_AEAT",
    "Pruebas_contribuyente",
    "categorias_admitidas_aeat",
    "categorias_rechazadas_aeat",
    "categorias_admitidas_contribuyente",
    "categorias_rechazadas_contribuyente",
    "Pruebas_rechazadas_clave",
    "Prueba_o_bala_de_plata",
    "resultado_final",
    "frases_clave",
    "confianza_extraccion",
    "observaciones",
    # Metadata de ejecución
    "tiempo_ejecucion",
    "costo_usd",
    "costo_medicion",
}

# ============================================================================
# CAMPOS REQUERIDOS EN OUTPUT JSON
# ============================================================================

# Estructura de campos mínimos que debe tener cada registro
REQUIRED_FIELDS: dict[str, Any] = {
    "archivo": None,
    "identificadores": {"ROJ": DEFAULT_MISSING_VALUE, "ECLI": DEFAULT_MISSING_VALUE},
    "organo": DEFAULT_MISSING_VALUE,
    "fecha_resolucion": DEFAULT_MISSING_VALUE,
    "es_caso_residencia_irpf": DEFAULT_MISSING_VALUE,
    "motivo_fuera_de_alcance": DEFAULT_MISSING_VALUE,
    "ejercicios_afectados": DEFAULT_MISSING_VALUE,
    "pais_alegado_residencia_pf": DEFAULT_MISSING_VALUE,
    "pais_CDI_aplicado": DEFAULT_MISSING_VALUE,
    "se_invoca_CDI": DEFAULT_MISSING_VALUE,
    "tiebreaker_paso_decisivo": DEFAULT_MISSING_VALUE,
    "Criterios_residencia_detectados": [],
    "Criterio_decisivo": [],
    "resumen_criterios": DEFAULT_MISSING_VALUE,
    # Nuevos campos de razonamiento judicial
    "doctrina_citada": [],
    "carga_prueba": {
        "quien_tenia_carga": DEFAULT_MISSING_VALUE,
        "motivo": DEFAULT_MISSING_VALUE,
        "cumplida": DEFAULT_MISSING_VALUE,
        "cita": {"pagina": DEFAULT_MISSING_VALUE, "texto": DEFAULT_MISSING_VALUE},
    },
    "razonamiento_residencia": DEFAULT_MISSING_VALUE,
    # Pruebas
    "Pruebas_AEAT": [],
    "Pruebas_contribuyente": [],
    "categorias_admitidas_aeat": [],
    "categorias_rechazadas_aeat": [],
    "categorias_admitidas_contribuyente": [],
    "categorias_rechazadas_contribuyente": [],
    "Pruebas_rechazadas_clave": [],
    "Prueba_o_bala_de_plata": {
        "parte": DEFAULT_MISSING_VALUE,
        "categoria": DEFAULT_MISSING_VALUE,
        "subcategoria": DEFAULT_MISSING_VALUE,
        "detalle": DEFAULT_MISSING_VALUE,
        "por_que_decisiva": DEFAULT_MISSING_VALUE,
        "cita": {"pagina": DEFAULT_MISSING_VALUE, "texto": DEFAULT_MISSING_VALUE},
    },
    "resultado_final": DEFAULT_MISSING_VALUE,
    "frases_clave": [],
    "confianza_extraccion": DEFAULT_MISSING_VALUE,
    "observaciones": DEFAULT_MISSING_VALUE,
}

# ============================================================================
# ORDEN DE COLUMNAS EN CSV (para mejor legibilidad)
# ============================================================================

CSV_COLUMN_ORDER = [
    # Identificación y filtrado
    "archivo",
    "es_caso_residencia_irpf",
    "fuera_de_alcance",
    "ROJ",
    "ECLI",
    "organo",
    "fecha_resolucion",
    "ejercicios_afectados",
    # Residencia y CDI
    "pais_alegado_residencia_pf",
    "pais_CDI_aplicado",
    "se_invoca_CDI",
    "tiebreaker_paso_decisivo",
    # Criterios
    "criterios_detectados",
    "criterio_decisivo",
    "resumen_criterios",
    # Razonamiento judicial (nuevos campos)
    "doctrina_citada",
    "carga_prueba",
    "razonamiento_residencia",
    # Pruebas detalladas
    "pruebas_aeat",
    "pruebas_contribuyente",
    # Agregados para análisis (admitidas/rechazadas por parte)
    "categorias_admitidas_aeat",
    "categorias_rechazadas_aeat",
    "categorias_admitidas_contribuyente",
    "categorias_rechazadas_contribuyente",
    # Pruebas clave
    "pruebas_rechazadas_clave",
    "bala_de_plata",
    # Resultado
    "resultado_final",
    # Metadata
    "frases_clave",
    "confianza_extraccion",
    "observaciones",
]

# ============================================================================
# MENSAJES Y DESCRIPCIONES
# ============================================================================

SCRIPT_DESCRIPTION = "Extrae información de sentencias PDF y genera CSV estructurado con análisis de residencia fiscal."

ARGUMENT_HELP = {
    "input": f"Carpeta con PDFs (default: {DEFAULT_INPUT_DIR})",
    "output": f"Carpeta de salida (default: {DEFAULT_OUTPUT_DIR})",
    "model": f"Modelo OpenAI a usar (default: {DEFAULT_MODEL})",
    "pdf_list": "Ruta a .txt con lista de PDFs a procesar (uno por línea)",
    "max_files": "Máximo de archivos PDF a procesar (0 = todos) - Útil para pruebas (default: 0)",
    "jsonl_name": f"Nombre del archivo JSONL de salida (default: {DEFAULT_JSONL_NAME})",
    "csv_name": f"Nombre del archivo CSV de salida (default: {DEFAULT_CSV_NAME})",
    "skip_existing": "Reanuda sobre el JSONL más reciente de la carpeta de salida, saltando los PDFs ya procesados",
    "resume_from": "Reanuda sobre un JSONL concreto (implica --skip-existing)",
}

# ============================================================================
# CÓDIGOS DE ERROR EN OBSERVACIONES
# ============================================================================

ERROR_CODES = {
    "PDF_NO_TEXT": "PDF sin texto extraíble",
    "PDF_EXTRACTION_FAILED": "ERROR_PROCESO",
    "LLM_CALL_FAILED": "ERROR_LLM",
    "JSON_PARSING_FAILED": "ERROR_JSON",
}
