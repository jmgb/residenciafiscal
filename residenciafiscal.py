# residenciafiscal.py
# Recorre la carpeta de sentencias PDFs, extrae texto (con marcadores de página),
# llama a un LLM con tu prompt de sistema (prompt.py), y genera:
#  - output.jsonl (una línea JSON por sentencia PDF)
#  - output.csv (una fila por sentencia PDF, con datos estructurados)
#
# Usa la función gpt_request() universal que soporta múltiples proveedores
# y reasoning_effort para modelos GPT-5+.
#
# Requisitos:
#   pip install -r requirements.txt
#
# Uso básico (automático):
#   source venv/bin/activate
#   python residenciafiscal.py
#
# Uso con argumentos personalizados:
#   python residenciafiscal.py --input /ruta/a/pdfs --output /ruta/salida --model gpt-4

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from dotenv import load_dotenv
from pypdf import PdfReader
from tqdm import tqdm

from config import (
    DEFAULT_INPUT_DIR,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_JSONL_NAME,
    DEFAULT_CSV_NAME,
    DEFAULT_MODEL,
    DEFAULT_MAX_PAGES,
    PAGE_MARKER_FMT,
    DEFAULT_MISSING_VALUE,
    REQUIRED_FIELDS,
    CSV_COLUMN_ORDER,
    ARGUMENT_HELP,
    SCRIPT_DESCRIPTION,
    REASONING_EFFORT,
    GPT_5_MINI,
)

# Intenta importar gpt_request de ai_service_adapter
try:
    from ai_service_adapter import gpt_request_for_sentencia
    USE_GPT_REQUEST = True
except ImportError:
    USE_GPT_REQUEST = False

# Importa tu prompt
try:
    from prompt import system_prompt as SYSTEM_PROMPT  # type: ignore
except Exception as e:
    raise RuntimeError(
        "No pude importar system_prompt desde prompt.py. "
        "Asegúrate de tener system_prompt = '''...''' en prompt.py."
    ) from e


# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# CLIENT INITIALIZATION
# ============================================================================

def initialize_client(ai_model: str) -> str:
    """Initialize the AI client needed for the selected model.

    Detects the provider from the model name and validates required API keys
    are available before processing starts. Fails fast if credentials missing.

    Args:
        ai_model: Model identifier (e.g., "gpt-5-mini", "groq-llama")

    Returns:
        Provider name (openai, groq, gemini, openrouter, etc.)

    Raises:
        RuntimeError: If required API key is missing for the detected provider
    """
    ai_model_lower = ai_model.lower()

    # Detect provider from model name
    if "gpt" in ai_model_lower or "o1" in ai_model_lower:
        provider = "openai"
    elif "groq" in ai_model_lower or "mixtral" in ai_model_lower or "llama" in ai_model_lower:
        provider = "groq"
    elif "gemini" in ai_model_lower or "claude" in ai_model_lower:
        provider = "gemini"
    else:
        provider = "openrouter"  # default fallback provider

    logger.info(f"🔌 Model: {ai_model}")
    logger.info(f"📡 Provider detected: {provider.upper()}")

    # Validate required API keys are available
    if provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError(
                "❌ OPENAI_API_KEY not found in environment. "
                "Please set it in .env file before running."
            )
        logger.info("✅ OPENAI_API_KEY found")

    elif provider == "groq":
        if not os.getenv("GROQ_API_KEY"):
            raise RuntimeError(
                "❌ GROQ_API_KEY not found in environment. "
                "Please set it in .env file before running."
            )
        logger.info("✅ GROQ_API_KEY found")

    elif provider == "gemini":
        if not os.getenv("GEMINI_API_KEY"):
            raise RuntimeError(
                "❌ GEMINI_API_KEY not found in environment. "
                "Please set it in .env file before running."
            )
        logger.info("✅ GEMINI_API_KEY found")

    else:  # openrouter
        if not os.getenv("OPENROUTER_API_KEY"):
            raise RuntimeError(
                "❌ OPENROUTER_API_KEY not found in environment. "
                "Please set it in .env file before running."
            )
        logger.info("✅ OPENROUTER_API_KEY found")

    logger.info(f"🚀 Client initialized for provider: {provider.upper()}")
    return provider


# ============================================================================
# PDF EXTRACTION
# ============================================================================

def extract_pdf_text_with_pages(pdf_path: Path, max_pages: Optional[int] = None) -> str:
    """Extrae texto del PDF e inserta marcadores de página (1-indexed)."""
    reader = PdfReader(str(pdf_path))
    parts: List[str] = []
    num_pages = len(reader.pages)
    limit = min(num_pages, max_pages) if max_pages else num_pages

    for i in range(limit):
        page = reader.pages[i]
        text = page.extract_text() or ""
        # Limpieza mínima (sin destruir)
        text = text.replace("\x00", " ").strip()
        parts.append(PAGE_MARKER_FMT.format(page_num=i + 1) + text)

    return "\n".join(parts).strip()


# ============================================================================
# FIELD VALIDATION
# ============================================================================

def ensure_required_keys(obj: Dict[str, Any], filename: str) -> Dict[str, Any]:
    """Asegura que haya claves mínimas para no romper el pipeline."""
    def set_default(path: str, default: Any) -> None:
        if path not in obj:
            obj[path] = default

    obj["archivo"] = filename

    for key, default_value in REQUIRED_FIELDS.items():
        if key == "archivo":
            continue

        if isinstance(default_value, dict):
            set_default(key, {k: v for k, v in default_value.items()})
        elif isinstance(default_value, list):
            set_default(key, [])
        else:
            set_default(key, default_value)

    return obj


# ============================================================================
# CSV FLATTENING
# ============================================================================

def flatten_for_csv(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Aplana a columnas 'amigables CSV'."""
    def jdump(x: Any) -> str:
        return json.dumps(x, ensure_ascii=False)

    row: Dict[str, Any] = {}
    row["archivo"] = obj.get("archivo", DEFAULT_MISSING_VALUE)

    # Campos de control de alcance (BLOQUE 0)
    row["es_caso_residencia_irpf"] = obj.get("es_caso_residencia_irpf", DEFAULT_MISSING_VALUE)
    row["fuera_de_alcance"] = obj.get("motivo_fuera_de_alcance", DEFAULT_MISSING_VALUE)

    ids = obj.get("identificadores", {}) or {}
    row["ROJ"] = ids.get("ROJ", DEFAULT_MISSING_VALUE)
    row["ECLI"] = ids.get("ECLI", DEFAULT_MISSING_VALUE)

    row["organo"] = obj.get("organo", DEFAULT_MISSING_VALUE)
    row["fecha_resolucion"] = obj.get("fecha_resolucion", DEFAULT_MISSING_VALUE)
    row["ejercicios_afectados"] = obj.get("ejercicios_afectados", DEFAULT_MISSING_VALUE)
    row["pais_alegado_residencia"] = obj.get("pais_alegado_residencia", DEFAULT_MISSING_VALUE)
    row["pais_alegado_residencia_pf"] = obj.get("pais_alegado_residencia_pf", DEFAULT_MISSING_VALUE)
    row["pais_CDI_aplicado"] = obj.get("pais_CDI_aplicado", DEFAULT_MISSING_VALUE)
    row["se_invoca_CDI"] = obj.get("se_invoca_CDI", DEFAULT_MISSING_VALUE)

    row["criterios_detectados"] = jdump(obj.get("Criterios_residencia_detectados", []))
    row["criterio_decisivo"] = jdump(obj.get("Criterio_decisivo", []))
    row["resumen_criterios"] = obj.get("Resumen_criterios", DEFAULT_MISSING_VALUE)

    row["pruebas_aeat"] = jdump(obj.get("Pruebas_AEAT", []))
    row["pruebas_contribuyente"] = jdump(obj.get("Pruebas_contribuyente", []))
    row["pruebas_rechazadas_clave"] = jdump(obj.get("Pruebas_rechazadas_clave", []))

    row["bala_de_plata"] = jdump(obj.get("Prueba_o_bala_de_plata", {}))
    row["resultado_final"] = obj.get("resultado_final", DEFAULT_MISSING_VALUE)

    row["frases_clave"] = jdump(obj.get("frases_clave", []))
    row["confianza_extraccion"] = obj.get("confianza_extraccion", DEFAULT_MISSING_VALUE)
    row["observaciones"] = obj.get("observaciones", DEFAULT_MISSING_VALUE)
    return row


# ============================================================================
# MAIN ASYNC PROCESSING LOOP
# ============================================================================

async def process_pdf_async(
    pdf_path: Path,
    ai_model: str,
    max_pages: Optional[int],
) -> Dict[str, Any]:
    """Procesa un PDF usando gpt_request."""
    fname = pdf_path.name
    
    try:
        pdf_text = extract_pdf_text_with_pages(pdf_path, max_pages=max_pages)
        
        if not pdf_text.strip():
            logger.warning(f"⚠️ {fname}: No se pudo extraer texto")
            return ensure_required_keys(
                {
                    "archivo": fname,
                    "observaciones": "PDF sin texto extraíble",
                    "confianza_extraccion": "BAJA"
                },
                fname
            )

        # Usar gpt_request si está disponible
        if USE_GPT_REQUEST:
            logger.info(f"📨 Procesando {fname} con gpt_request ({ai_model})")
            result = await gpt_request_for_sentencia(
                ai_model=ai_model,
                system_prompt=SYSTEM_PROMPT,
                pdf_text=pdf_text,
                logger=logger,
                temperature=0,
                response_format="json_object",
                reasoning_effort=REASONING_EFFORT if "gpt-5" in ai_model else None,
            )
            
            if "error" in result:
                logger.error(f"❌ {fname}: Error en gpt_request: {result.get('error')}")
                return ensure_required_keys(
                    {
                        "archivo": fname,
                        "observaciones": f"ERROR_GPT_REQUEST: {result.get('error')}",
                        "confianza_extraccion": "BAJA",
                    },
                    fname,
                )
            
            # Eliminar campos de metadata
            obj = {k: v for k, v in result.items() if k not in ["tiempo_ejecucion", "error"]}
        else:
            logger.warning(f"⚠️ gpt_request no disponible, usando fallback")
            return ensure_required_keys(
                {
                    "archivo": fname,
                    "observaciones": "ERROR: gpt_request no disponible",
                    "confianza_extraccion": "BAJA",
                },
                fname,
            )

        return ensure_required_keys(obj, fname)

    except Exception as e:
        logger.error(f"🚨 Error procesando {fname}: {e}")
        return ensure_required_keys(
            {
                "archivo": fname,
                "observaciones": f"ERROR_PROCESO: {str(e)}",
                "confianza_extraccion": "BAJA",
            },
            fname,
        )


async def main_async(
    in_dir: Path,
    out_dir: Path,
    jsonl_path: Path,
    csv_path: Path,
    ai_model: str,
    max_pages: Optional[int],
    skip_existing: bool,
) -> None:
    """Bucle principal de procesamiento."""
    
    if not in_dir.exists() or not in_dir.is_dir():
        raise RuntimeError(f"Carpeta de entrada no válida: {in_dir}")

    # Buscar PDFs recursivamente
    pdf_files = sorted([p for p in in_dir.glob("**/*.pdf") if p.is_file()])
    if not pdf_files:
        raise RuntimeError(f"No encontré PDFs en: {in_dir}")

    logger.info(f"📁 Encontrados {len(pdf_files)} PDFs para procesar")

    # Cargar ya procesados si skip-existing
    processed = set()
    if skip_existing and jsonl_path.exists():
        with jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    processed.add(obj.get("archivo"))
                except Exception:
                    continue

    # Procesar PDFs
    jsonl_mode = "a" if jsonl_path.exists() else "w"
    with jsonl_path.open(jsonl_mode, encoding="utf-8") as jf:
        for pdf_path in tqdm(pdf_files, desc="📄 Procesando PDFs"):
            fname = pdf_path.name
            if skip_existing and fname in processed:
                logger.debug(f"⏭️ Saltando {fname} (ya procesado)")
                continue

            # Procesar PDF
            obj = await process_pdf_async(pdf_path, ai_model, max_pages)
            
            # Guardar en JSONL
            jf.write(json.dumps(obj, ensure_ascii=False) + "\n")
            jf.flush()

    # Convertir JSONL -> CSV
    logger.info("🔄 Convirtiendo JSONL a CSV...")
    rows: List[Dict[str, Any]] = []
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                rows.append(flatten_for_csv(obj))
            except Exception:
                continue

    df = pd.DataFrame(rows)

    # Reordenar columnas
    cols = [c for c in CSV_COLUMN_ORDER if c in df.columns] + [
        c for c in df.columns if c not in CSV_COLUMN_ORDER
    ]
    df = df[cols]

    df.to_csv(csv_path, index=False, encoding="utf-8")
    logger.info(f"\n✅ Procesamiento completado!")
    logger.info(f"   📄 JSONL: {jsonl_path}")
    logger.info(f"   📊 CSV:   {csv_path}")
    logger.info(f"   📈 Filas: {len(df)}")


def main() -> None:
    """Punto de entrada principal."""
    load_dotenv()

    parser = argparse.ArgumentParser(description=SCRIPT_DESCRIPTION)
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT_DIR),
        help=ARGUMENT_HELP["input"]
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_DIR),
        help=ARGUMENT_HELP["output"]
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help=ARGUMENT_HELP["model"])
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES, help=ARGUMENT_HELP["max_pages"])
    parser.add_argument("--jsonl-name", default=DEFAULT_JSONL_NAME, help=ARGUMENT_HELP["jsonl_name"])
    parser.add_argument("--csv-name", default=DEFAULT_CSV_NAME, help=ARGUMENT_HELP["csv_name"])
    parser.add_argument("--skip-existing", action="store_true", help=ARGUMENT_HELP["skip_existing"])
    args = parser.parse_args()

    in_dir = Path(args.input).expanduser().resolve()
    out_dir = Path(args.output).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    jsonl_path = out_dir / args.jsonl_name
    csv_path = out_dir / args.csv_name

    max_pages = args.max_pages if args.max_pages and args.max_pages > 0 else None

    logger.info(f"🚀 Iniciando procesamiento de sentencias")
    logger.info(f"   📁 Entrada: {in_dir}")
    logger.info(f"   📤 Salida: {out_dir}")
    logger.info(f"   🤖 Modelo: {args.model}")
    logger.info(f"   ⚙️ Reasoning Effort: {REASONING_EFFORT}")

    # Initialize client for selected model (fails fast if API key missing)
    try:
        provider = initialize_client(args.model)
        logger.info(f"   ✅ Provider: {provider.upper()}")
    except RuntimeError as e:
        logger.error(str(e))
        raise

    # Ejecutar bucle async
    asyncio.run(
        main_async(
            in_dir=in_dir,
            out_dir=out_dir,
            jsonl_path=jsonl_path,
            csv_path=csv_path,
            ai_model=args.model,
            max_pages=max_pages,
            skip_existing=args.skip_existing,
        )
    )


if __name__ == "__main__":
    main()
