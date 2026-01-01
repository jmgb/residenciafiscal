# residenciafiscal.py
# Recorre la carpeta de sentencias PDFs, extrae texto (con marcadores de página),
# llama a un LLM con tu prompt de sistema (prompt.py), y genera:
#  - output.jsonl (una línea JSON por sentencia PDF)
#  - output.csv (una fila por sentencia PDF, con datos estructurados)
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
#
# Nota:
# - Script asume SYSTEM_PROMPT en prompt.py
# - Requiere OPENAI_API_KEY en entorno o .env
# - Busca PDFs recursivamente en subcarpetas
# - Genera una fila CSV por cada sentencia procesada

from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from dotenv import load_dotenv
from pypdf import PdfReader
from tqdm import tqdm

from openai import OpenAI

# Importa configuración centralizada
from config import (
    DEFAULT_INPUT_DIR,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_JSONL_NAME,
    DEFAULT_CSV_NAME,
    DEFAULT_MODEL,
    DEFAULT_MAX_PAGES,
    PAGE_MARKER_FMT,
    LLM_MAX_RETRIES,
    LLM_BACKOFF_BASE,
    DEFAULT_MISSING_VALUE,
    REQUIRED_FIELDS,
    CSV_COLUMN_ORDER,
    SHOW_PROGRESS_BAR,
    ARGUMENT_HELP,
    SCRIPT_DESCRIPTION,
    ERROR_CODES,
    REASONING_EFFORT,
    GPT_5,
    GPT_5_MINI,
    GPT_5_NANO,
)

# Importa tu prompt (ya lo tienes)
try:
    from prompt import system_prompt as SYSTEM_PROMPT  # type: ignore
except Exception as e:
    raise RuntimeError(
        "No pude importar system_prompt desde prompt.py. "
        "Asegúrate de tener system_prompt = '''...''' en prompt.py."
    ) from e


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


def strip_code_fences(s: str) -> str:
    """El modelo a veces devuelve JSON dentro de ```...```. Lo quitamos."""
    s = s.strip()
    # ```json ... ```
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    return s.strip()


def first_json_object_from_text(s: str) -> str:
    """
    Extrae el primer objeto JSON válido dentro de un texto.
    Si el texto ya es JSON, lo devuelve.
    """
    s = strip_code_fences(s)
    if s.startswith("{") and s.endswith("}"):
        return s

    # Búsqueda del primer bloque {...} balanceado
    start = s.find("{")
    if start == -1:
        raise ValueError("No se encontró '{' para iniciar JSON.")

    depth = 0
    for idx in range(start, len(s)):
        ch = s[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start : idx + 1]

    raise ValueError("No se pudo extraer un objeto JSON balanceado.")


def safe_json_loads(s: str) -> Dict[str, Any]:
    """Carga JSON con extracción robusta."""
    s2 = first_json_object_from_text(s)
    try:
        obj = json.loads(s2)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON inválido: {e}") from e
    if not isinstance(obj, dict):
        raise ValueError("El JSON devuelto no es un objeto (dict).")
    return obj


@dataclass
class CallResult:
    ok: bool
    data: Optional[Dict[str, Any]] = None
    raw_text: Optional[str] = None
    error: Optional[str] = None


def call_llm_extract(
    client: OpenAI,
    model: str,
    system_prompt: str,
    pdf_filename: str,
    pdf_text: str,
    max_retries: int = LLM_MAX_RETRIES,
    backoff_base: float = LLM_BACKOFF_BASE,
) -> CallResult:
    """
    Llama al modelo para extraer el JSON (1 línea) según tu system prompt.
    Reintenta con backoff y repara si el JSON sale roto.
    Si el modelo es GPT-5+, aplica reasoning_effort configurado.
    """
    user_input = (
        "INPUT_DOCUMENTO:\n"
        f"ARCHIVO: {pdf_filename}\n\n"
        f"{pdf_text}\n"
    )

    # Determinar si aplicar reasoning_effort (solo para GPT-5+)
    is_gpt5_model = any(gpt5 in model for gpt5 in [GPT_5, GPT_5_MINI, GPT_5_NANO, "gpt-5"])

    last_error = None
    for attempt in range(max_retries):
        try:
            # Construir argumentos de llamada al modelo
            create_kwargs: Dict[str, Any] = {
                "model": model,
                "instructions": system_prompt,
                "input": user_input,
            }

            # Agregar reasoning_effort solo si es GPT-5+
            if is_gpt5_model:
                create_kwargs["reasoning_effort"] = REASONING_EFFORT

            resp = client.responses.create(**create_kwargs)
            text_out = (resp.output_text or "").strip()
            if not text_out:
                raise RuntimeError("Respuesta vacía del modelo.")

            # Parse JSON
            try:
                obj = safe_json_loads(text_out)
                return CallResult(ok=True, data=obj, raw_text=text_out)
            except Exception as parse_err:
                # Intento de reparación: 1 ronda extra con el propio modelo
                repair_prompt = (
                    "La salida anterior NO es un JSON válido según el formato requerido.\n"
                    "Devuelve SOLO un objeto JSON válido en UNA sola línea, sin texto adicional.\n"
                    "Aquí tienes la salida inválida:\n\n"
                    f"{text_out}\n"
                )
                # Reutilizar kwargs con reasoning_effort si corresponde
                create_kwargs["input"] = repair_prompt
                resp2 = client.responses.create(**create_kwargs)
                text_out2 = (resp2.output_text or "").strip()
                obj2 = safe_json_loads(text_out2)
                return CallResult(ok=True, data=obj2, raw_text=text_out2)

        except Exception as e:
            last_error = str(e)
            # Backoff
            sleep_s = (backoff_base ** attempt) + (0.1 * attempt)
            time.sleep(sleep_s)

    return CallResult(ok=False, error=last_error)


def ensure_required_keys(obj: Dict[str, Any], filename: str) -> Dict[str, Any]:
    """
    Asegura que haya claves mínimas para no romper el pipeline,
    sin inventar: si faltan, se completan con los valores por defecto de config.
    """
    def set_default(path: str, default: Any) -> None:
        if path not in obj:
            obj[path] = default

    # Aplicar estructura de campos requeridos desde config
    obj["archivo"] = filename

    for key, default_value in REQUIRED_FIELDS.items():
        if key == "archivo":
            continue  # Ya fue asignado arriba

        # Para nested dicts, hacer deep copy del default
        if isinstance(default_value, dict):
            set_default(key, {k: v for k, v in default_value.items()})
        elif isinstance(default_value, list):
            set_default(key, [])
        else:
            set_default(key, default_value)

    return obj


def flatten_for_csv(obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aplana a columnas "amigables CSV".
    Las listas/dicts se guardan como JSON-string para no perder detalle.
    """
    def jdump(x: Any) -> str:
        return json.dumps(x, ensure_ascii=False)

    row: Dict[str, Any] = {}
    row["archivo"] = obj.get("archivo", DEFAULT_MISSING_VALUE)

    ids = obj.get("identificadores", {}) or {}
    row["ROJ"] = ids.get("ROJ", DEFAULT_MISSING_VALUE)
    row["ECLI"] = ids.get("ECLI", DEFAULT_MISSING_VALUE)

    row["organo"] = obj.get("organo", DEFAULT_MISSING_VALUE)
    row["fecha_resolucion"] = obj.get("fecha_resolucion", DEFAULT_MISSING_VALUE)
    row["ejercicios_afectados"] = obj.get("ejercicios_afectados", DEFAULT_MISSING_VALUE)
    row["pais_alegado_residencia"] = obj.get("pais_alegado_residencia", DEFAULT_MISSING_VALUE)
    row["se_invoca_CDI"] = obj.get("se_invoca_CDI", DEFAULT_MISSING_VALUE)

    row["criterios_detectados"] = jdump(obj.get("Criterios_residencia_detectados", []))
    row["criterio_decisivo"] = jdump(obj.get("Criterio_decisivo", []))
    row["resumen_criterios"] = obj.get("Resumen_criterios", DEFAULT_MISSING_VALUE)

    # Pruebas (guardar completo)
    row["pruebas_aeat"] = jdump(obj.get("Pruebas_AEAT", []))
    row["pruebas_contribuyente"] = jdump(obj.get("Pruebas_contribuyente", []))
    row["pruebas_rechazadas_clave"] = jdump(obj.get("Pruebas_rechazadas_clave", []))

    row["bala_de_plata"] = jdump(obj.get("Prueba_o_bala_de_plata", {}))
    row["resultado_final"] = obj.get("resultado_final", DEFAULT_MISSING_VALUE)

    row["frases_clave"] = jdump(obj.get("frases_clave", []))
    row["confianza_extraccion"] = obj.get("confianza_extraccion", DEFAULT_MISSING_VALUE)
    row["observaciones"] = obj.get("observaciones", DEFAULT_MISSING_VALUE)
    return row


def main() -> None:
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

    if not in_dir.exists() or not in_dir.is_dir():
        raise RuntimeError(f"Carpeta de entrada no válida: {in_dir}")

    # Busca PDFs recursivamente en subdirectorios también
    pdf_files = sorted([p for p in in_dir.glob("**/*.pdf") if p.is_file()])
    if not pdf_files:
        raise RuntimeError(f"No encontré PDFs en: {in_dir}")

    # Cargar ya procesados si skip-existing
    processed = set()
    if args.skip_existing and jsonl_path.exists():
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

    client = OpenAI()  # Usa OPENAI_API_KEY del entorno

    # Abrimos JSONL en append
    jsonl_mode = "a" if jsonl_path.exists() else "w"
    with jsonl_path.open(jsonl_mode, encoding="utf-8") as jf:
        for pdf_path in tqdm(pdf_files, desc="Procesando PDFs"):
            fname = pdf_path.name
            if args.skip_existing and fname in processed:
                continue

            try:
                pdf_text = extract_pdf_text_with_pages(pdf_path, max_pages=max_pages)
                if not pdf_text.strip():
                    # Guardar fila mínima si no hay texto
                    obj = ensure_required_keys({"archivo": fname, "observaciones": "PDF sin texto extraíble"}, fname)
                    jf.write(json.dumps(obj, ensure_ascii=False) + "\n")
                    jf.flush()
                    continue

                result = call_llm_extract(
                    client=client,
                    model=args.model,
                    system_prompt=SYSTEM_PROMPT,
                    pdf_filename=fname,
                    pdf_text=pdf_text,
                )

                if not result.ok or not result.data:
                    obj = ensure_required_keys(
                        {
                            "archivo": fname,
                            "observaciones": f"ERROR_LLM: {result.error or 'desconocido'}",
                            "confianza_extraccion": "BAJA",
                        },
                        fname,
                    )
                else:
                    obj = ensure_required_keys(result.data, fname)

                jf.write(json.dumps(obj, ensure_ascii=False) + "\n")
                jf.flush()

            except Exception as e:
                obj = ensure_required_keys(
                    {"archivo": fname, "observaciones": f"ERROR_PROCESO: {str(e)}", "confianza_extraccion": "BAJA"},
                    fname,
                )
                jf.write(json.dumps(obj, ensure_ascii=False) + "\n")
                jf.flush()

    # Convertir JSONL -> CSV
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

    # Reordenar columnas según CSV_COLUMN_ORDER de config
    cols = [c for c in CSV_COLUMN_ORDER if c in df.columns] + [c for c in df.columns if c not in CSV_COLUMN_ORDER]
    df = df[cols]

    df.to_csv(csv_path, index=False, encoding="utf-8")
    print(f"\nOK ✅\n- JSONL: {jsonl_path}\n- CSV:  {csv_path}\n- Filas: {len(df)}\n")


if __name__ == "__main__":
    main()
