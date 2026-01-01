"""
config.py
Configuración centralizada para residenciafiscal.py
Externaliza variables, rutas y parámetros de LLM en un solo lugar.
"""

from pathlib import Path

# ============================================================================
# RUTAS POR DEFECTO
# ============================================================================

# Ruta base del proyecto
PROJECT_ROOT = Path(__file__).parent

# Directorio donde se encuentran las sentencias PDF
DEFAULT_INPUT_DIR = PROJECT_ROOT / "sentencias"

# Directorio donde se guardan los resultados
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"

# ============================================================================
# NOMBRES DE ARCHIVOS DE SALIDA
# ============================================================================

DEFAULT_JSONL_NAME = "output.jsonl"
DEFAULT_CSV_NAME = "output.csv"

# ============================================================================
# CONFIGURACIÓN DE OPENAI
# ============================================================================

# Modelos OpenAI disponibles
GPT_4_MINI = "gpt-4-mini"
GPT_4 = "gpt-4"
GPT_4_TURBO = "gpt-4-turbo"
GPT_5 = "gpt-5.2-2025-12-11"
GPT_5_MINI = "gpt-5-mini-2025-08-07"
GPT_5_NANO = "gpt-5-nano-2025-08-07"

# Modelos Gemini (si se implementa soporte)
GEMINI_PRO = "gemini-3-pro-preview"
GEMINI_FLASH = "gemini-3-flash-preview"

# Parámetro de esfuerzo de razonamiento para GPT-5 (low|medium|high|minimal)
# Mayor esfuerzo = mayor precisión pero más lento y caro
REASONING_EFFORT = "medium"

# Modelo por defecto a usar
DEFAULT_MODEL = GPT_5_MINI


# ============================================================================
# PARÁMETROS DE EXTRACCIÓN DE PDF
# ============================================================================

# Formato del marcador de página en el texto extraído
PAGE_MARKER_FMT = "\n\n--- PÁGINA {page_num} ---\n\n"

# Máximo de páginas a procesar por defecto (0 = sin límite)
DEFAULT_MAX_PAGES = 0

# ============================================================================
# PARÁMETROS DE LLM (RETRIES Y BACKOFF)
# ============================================================================

# Número máximo de reintentos cuando la API falla
LLM_MAX_RETRIES = 4

# Base de backoff exponencial: sleep_time = (base ^ attempt) + (0.1 * attempt)
# Ejemplo: attempt 0 = 1s, attempt 1 = ~1.8s, attempt 2 = ~3.3s, attempt 3 = ~5.9s
LLM_BACKOFF_BASE = 1.8

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
# CAMPOS REQUERIDOS EN OUTPUT JSON
# ============================================================================

# Estructura de campos mínimos que debe tener cada registro
REQUIRED_FIELDS = {
    "archivo": None,
    "identificadores": {"ROJ": DEFAULT_MISSING_VALUE, "ECLI": DEFAULT_MISSING_VALUE},
    "organo": DEFAULT_MISSING_VALUE,
    "fecha_resolucion": DEFAULT_MISSING_VALUE,
    "ejercicios_afectados": DEFAULT_MISSING_VALUE,
    "pais_alegado_residencia": DEFAULT_MISSING_VALUE,
    "se_invoca_CDI": DEFAULT_MISSING_VALUE,
    "Criterios_residencia_detectados": [],
    "Criterio_decisivo": [],
    "Resumen_criterios": DEFAULT_MISSING_VALUE,
    "Pruebas_AEAT": [],
    "Pruebas_contribuyente": [],
    "Pruebas_rechazadas_clave": [],
    "Prueba_o_bala_de_plata": {
        "parte": DEFAULT_MISSING_VALUE,
        "categoria": DEFAULT_MISSING_VALUE,
        "detalle": DEFAULT_MISSING_VALUE,
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
    "archivo",
    "ROJ",
    "ECLI",
    "organo",
    "fecha_resolucion",
    "ejercicios_afectados",
    "pais_alegado_residencia",
    "se_invoca_CDI",
    "criterios_detectados",
    "criterio_decisivo",
    "resumen_criterios",
    "pruebas_aeat",
    "pruebas_contribuyente",
    "pruebas_rechazadas_clave",
    "bala_de_plata",
    "resultado_final",
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
    "max_pages": "Máximo de páginas a procesar por PDF (0 = todas) (default: 0)",
    "jsonl_name": f"Nombre del archivo JSONL de salida (default: {DEFAULT_JSONL_NAME})",
    "csv_name": f"Nombre del archivo CSV de salida (default: {DEFAULT_CSV_NAME})",
    "skip_existing": "Si existe JSONL previo, salta PDFs ya procesados",
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
