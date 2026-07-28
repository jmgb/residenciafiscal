# CLAUDE.md

Guía para Claude Code en el proyecto **Residencia Fiscal**.

## Quick Start

El proyecto usa **uv** (no pip/venv a mano) y un **Makefile** como interfaz única.

```bash
# Instalar dependencias (crea .venv con Python 3.13 e instala desde uv.lock)
make setup

# Configurar API key: rellenar OPENAI_API_KEY en .env
cp .env.example .env

# Ver todos los comandos disponibles
make help

# Ejecutar pipeline completo (106 PDFs → ~$2.80 USD, ~2-3h)
make run

# Test rápido con 1 PDF
make run-sample

# Levantar la API HTTP (Swagger en http://127.0.0.1:8010/docs)
make dev
```

> Cualquier comando suelto se lanza con `uv run` (p. ej. `uv run python residenciafiscal.py --help`).
> Nunca hace falta activar el entorno: `uv run` lo resuelve solo.

## Resumen del Proyecto

Pipeline Python que analiza **106 sentencias judiciales españolas** sobre residencia fiscal (Art. 9 LIRPF) usando LLMs para extraer:

- **Criterios de residencia** aplicados (183 días, centro de intereses, familia, CDI)
- **Pruebas aportadas** por AEAT y contribuyente (aceptadas/rechazadas)
- **Razonamiento judicial** (doctrina, carga de prueba, motivación)
- **Resultado** (GANA_AEAT / GANA_CONTRIBUYENTE / PARCIAL)

**Usuarios objetivo**: Investigadores fiscales, abogados tributaristas, compliance.

## Arquitectura

Dos frontends sobre el mismo núcleo: el **CLI por lotes** y la **API HTTP**. Ambos
llaman a `process_pdf_async()`, así que producen exactamente el mismo objeto.

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────────┐
│  sentencias/    │────▶│ residencia   │────▶│  output/            │
│  106 PDFs       │ CLI │ fiscal.py    │     │  ├─ analisis.jsonl  │
│  (STS + SAN)    │     │              │     │  ├─ sentencias.csv  │
└─────────────────┘     │  + prompt.py │     │  ├─ pruebas.csv     │
                        │  + config.py │     │  └─ analisis.xlsx   │
┌─────────────────┐     │              │     └─────────────────────┘
│  POST /analizar │────▶│ process_pdf  │────▶  JSON en la respuesta
│  (api/main.py)  │ API │  _async()    │
└─────────────────┘     └──────────────┘
                               │
                               ▼
                        ┌──────────────┐
                        │ OpenAI API   │
                        │ GPT-5 / Nano │
                        └──────────────┘
```

| Archivo | Función |
|---------|---------|
| `residenciafiscal.py` | Pipeline principal (async, batches de 10 PDFs) |
| `api/main.py` | API HTTP (FastAPI) que envuelve el pipeline, 1 PDF por request |
| `prompt.py` | System prompt con contexto legal y schema JSON |
| `config.py` | Modelos, rutas, enums, campos requeridos |
| `ai_service_adapter.py` | Wrapper para llamadas LLM con retry y cost tracking |
| `pyproject.toml` | Dependencias (uv) + config de ruff, mypy y pytest |
| `Makefile` | Interfaz única de comandos (`make help`) |

## Dataset

| Concepto | Valor |
|----------|-------|
| Total PDFs | 106 sentencias |
| Tribunal Supremo (STS) | 74 |
| Audiencia Nacional (SAN) | 32 |
| Período | 2015-2025 |
| Sentencias clave | 23 (modelo premium GPT-5) |

## Outputs Generados

Cada ejecución genera 5 archivos con timestamp:

| Archivo | Formato | Uso |
|---------|---------|-----|
| `analisis_*.jsonl` | 1 JSON/línea | Raw data completo, resumable |
| `analisis_*.csv` | Flat | Campos complejos como JSON strings |
| `sentencias_*.csv` | 1 fila/sentencia | Agregados de pruebas |
| `pruebas_*.csv` | 1 fila/prueba | Detalle judicial completo |
| `analisis_*.xlsx` | 2 hojas | Excel con Sentencias + Pruebas |

## Campos Principales del Schema

### Identificación
- `archivo`, `ROJ`, `ECLI`, `organo`, `fecha_resolucion`

### Residencia
- `es_caso_residencia_irpf`: SI/NO
- `pais_alegado_residencia_pf`, `pais_CDI_aplicado`
- `se_invoca_CDI`, `tiebreaker_paso_decisivo`

### Criterios (CRIT_*)
- `CRIT_183_DIAS` - Permanencia >183 días
- `CRIT_AUSENCIAS_ESPORADICAS` - Art. 9.1.a) segundo párrafo
- `CRIT_CENTRO_INTERESES_ECONOMICOS` - Núcleo principal de actividades
- `CRIT_CENTRO_INTERESES_VITALES` - Vínculos personales y familiares
- `CRIT_PRESUNCION_FAMILIA` - Cónyuge e hijos menores en España
- `CRIT_CDI_TIEBREAKER` - Reglas de desempate Art. 4 CDI
- `CRIT_OTRO`

### Pruebas (por parte: AEAT / Contribuyente)
```json
{
  "categoria": "PRESENCIA_FISICA_Y_DESPLAZAMIENTOS",
  "subcategoria": "sellos_pasaporte",
  "detalle": "Pasaporte con sellos de entrada/salida",
  "objetivo_probatorio": "Acreditar estancia fuera de España",
  "criterio_atacado": "CRIT_183_DIAS",
  "tipo_prueba": "DIRECTA | INDICIARIA | PRESUNCION",
  "origen": "APORTADA_PARTE | REQUERIDA_INSPECCION | OBTENIDA_TERCEROS",
  "aceptada": "SI | NO",
  "peso": 1-5,
  "motivo_valoracion": "Razón del juez para aceptar/rechazar",
  "cita": {"pagina": "12", "texto": "...extracto literal..."}
}
```

### Categorías de Prueba (12)
1. `PRESENCIA_FISICA_Y_DESPLAZAMIENTOS`
2. `VIVIENDA_Y_USO_EFECTIVO`
3. `SUMINISTROS_Y_CONSUMOS_DOMESTICOS`
4. `CONSUMOS_FINANCIEROS`
5. `FAMILIA_Y_ENTORNO_PERSONAL`
6. `SALUD_Y_SERVICIOS_PERSONALES`
7. `ACTIVIDAD_ECONOMICA_Y_GESTION`
8. `DOCUMENTACION_FISCAL_EXTRANJERA`
9. `VINCULOS_ADMINISTRATIVOS_EN_ESPANA`
10. `TRAZAS_DIGITALES`
11. `TESTIFICAL_Y_PERICIAL`
12. `OTROS`

### Razonamiento Judicial
- `doctrina_citada`: Lista de sentencias precedentes
- `carga_prueba`: {quien_tenia_carga, motivo, cumplida, cita}
- `razonamiento_residencia`: Texto explicando la decisión

### Resultado
- `resultado_final`: GANA_AEAT | GANA_CONTRIBUYENTE | PARCIAL | RETROACCION | INADMISION
- `confianza_extraccion`: ALTA | MEDIA | BAJA
- `tiempo_ejecucion`, `costo_usd`

## Sentencias Clave

23 sentencias en `sentencias/sentencias_CLAVE.txt` usan automáticamente **GPT-5** (modelo premium) independientemente del `--model` indicado:

```
STS_107_2018.pdf    # Caso ICEX - 183 días
STS_4305_2017.pdf   # Doctrina TS sobre centro intereses
STS_3942_2021.pdf   # CDI España-Suiza
...
```

**Coste**: ~$0.10/sentencia clave vs ~$0.006/sentencia normal

## Comandos Útiles

Todo pasa por el Makefile. `make help` los lista todos.

```bash
# --- Pipeline ---
make run                                  # procesamiento completo
make run-sample                           # 1 PDF (prueba rápida)
make run-resume                           # continuar ejecución interrumpida
make run MAX_FILES=5                      # limitar archivos (testing)
make run MODEL=gpt-4-turbo                # modelo específico (ignorado en sentencias clave)
make run EFFORT=high                      # reasoning effort (low/medium/high)
make run-list LIST=./mi_lista.txt         # lista específica de PDFs
make run INPUT=./otros OUTPUT=./out2      # rutas alternativas

# --- API ---
make dev                                  # FastAPI con reload en 127.0.0.1:8010
make dev-public                           # accesible desde la red local (0.0.0.0)
make serve                                # sin reload
make dev PORT=9000                        # otro puerto

# --- Calidad ---
make fast-check                           # lint + typecheck + tests (gate pre-commit)
make lint / format / fix / typecheck
make test                                 # pytest sin llamadas LLM reales
make test-llm                             # incluye tests marcados manual_real_llm (con coste)
make test-single                          # smoke test end-to-end con 1 PDF

# --- Dependencias ---
make lock                                 # regenera uv.lock
make upgrade                              # actualiza dentro de los rangos de pyproject.toml
make export-requirements                  # requirements.txt derivado del lock (para terceros)

# --- Limpieza ---
make clean                                # caches
make clean-output                         # artefactos de ./output
```

El CLI subyacente sigue disponible: `uv run python residenciafiscal.py --help`.

## API HTTP

`make dev` levanta FastAPI en `127.0.0.1:8010` (puerto 8010 y no 8000 para no chocar
con el backend de presupuestor).

| Método | Ruta        | Descripción                                          |
|--------|-------------|------------------------------------------------------|
| GET    | `/health`   | Estado + qué API keys están presentes                |
| GET    | `/config`   | Modelos, criterios y categorías vigentes             |
| POST   | `/analizar` | Sube un PDF → análisis estructurado (mismo schema)   |
| GET    | `/docs`     | Swagger UI                                            |

```bash
curl -X POST -F "archivo=@sentencias/SAN_1226_2021.pdf" \
  http://127.0.0.1:8010/analizar | jq .
```

`POST /analizar` acepta además los campos de formulario `modelo`, `reasoning_effort`
(`low|medium|high`) y `max_pages` (entero positivo). Reutiliza `process_pdf_async()`, así
que devuelve el mismo objeto que una línea del JSONL, envuelto en
`{"modelo_usado": ..., "analisis": {...}}`. Si el nombre del fichero está en
`sentencias_CLAVE.txt`, se fuerza el modelo premium.

**Importante**: la API es de un PDF por request y **no persiste nada** en `output/`.
Para lotes, sigue usando `make run`.

### Guardarraíles de la API

`POST /analizar` es la única ruta que gasta dinero, así que lleva:

| Guardarraíl | Detalle |
|-------------|---------|
| Token opcional | Si `RESIDENCIAFISCAL_API_TOKEN` está en `.env`, exige la cabecera `X-API-Token`. Sin definir, la ruta queda abierta (cómodo en localhost, imprudente con `make dev-public`, que además avisa al arrancar). |
| Límite de subida | 25 MB, cortado por `Content-Length` en un middleware **antes** de parsear el multipart, con un contador en el handler como respaldo para peticiones `chunked`. |
| Allowlist de modelos | `modelo` solo acepta IDs declarados en `config.py` (ver `/config` → `modelos_permitidos`). Motivo: `initialize_client()` cae a **openrouter** para IDs desconocidos mientras `_detect_provider()` del adaptador cae a **openai**, así que un ID arbitrario validaría una API key y usaría otra. |
| Validación de entrada | Solo `.pdf`; `reasoning_effort` ∈ {low, medium, high}; `max_pages` ≥ 1 (un valor negativo hacía que el pipeline no leyera páginas y devolviera un 200 con confianza BAJA). |

No hay rate limiting. Si algún día esto se expone más allá de la LAN, hay que añadirlo.

## Costes Estimados

| Modelo | Coste/PDF | 106 PDFs |
|--------|-----------|----------|
| gpt-5-nano (default) | $0.006 | $0.50 |
| gpt-5 (clave) | $0.10 | $2.30 |
| **Total mixto** | $0.026 avg | **$2.80** |

## Configuración (config.py)

```python
# Modelos
DEFAULT_MODEL = GPT_5_MINI           # gpt-5.6-luna
SENTENCIA_CLAVE_MODEL = GPT_5        # gpt-5.6-sol
REASONING_EFFORT = "medium"

# Procesamiento
BATCH_SIZE = 10                      # PDFs en paralelo
LLM_MAX_RETRIES = 4
LLM_BACKOFF_BASE = 1.8

# Rutas
DEFAULT_INPUT_DIR = PROJECT_ROOT / "sentencias"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"
KEY_SENTENCIAS_FILE = DEFAULT_INPUT_DIR / "sentencias_CLAVE.txt"
```

## Gestión de dependencias (uv)

La fuente de verdad es `pyproject.toml`; `uv.lock` fija las versiones exactas y **se
versiona en git**. No hay `requirements.txt` en el repo (se genera bajo demanda con
`make export-requirements` si algún consumidor externo lo necesita).

```bash
uv add pandas          # añadir una dependencia (actualiza pyproject + lock)
uv add --dev pytest    # dependencia solo de desarrollo
uv remove groq         # quitarla
make lock              # regenerar el lock tras editar pyproject a mano
make upgrade           # subir versiones dentro de los rangos declarados
```

Runtime: Python **3.13** (fijado en `.python-version`; `uv` lo instala solo).

Dependencias principales:

```
openai, groq, google-generativeai   # proveedores LLM
pypdf                               # extracción de texto de PDF
pandas, openpyxl                    # DataFrames y export a Excel
fastapi[standard], uvicorn          # API HTTP
pydantic, python-dotenv, aiohttp, tqdm
# dev: pytest, pytest-asyncio, ruff, mypy
```

## Calidad de código

Configurado todo en `pyproject.toml`:

- **ruff** — lint + format, `line-length = 100`, reglas `E W F I B C4 UP`
- **mypy** — `check_untyped_defs`, `ignore_missing_imports` (libs sin stubs)
- **pytest** — `testpaths = ["test"]`, `asyncio_mode = "auto"`. Los tests que llaman a
  LLMs reales van marcados `@pytest.mark.manual_real_llm` y **quedan excluidos por
  defecto** (evita gasto accidental); se lanzan con `make test-llm`.

Gate antes de commitear: `make fast-check`.

## Troubleshooting

| Problema | Solución |
|----------|----------|
| `OPENAI_API_KEY not set` | Rellenar `.env` (`cp .env.example .env`) |
| `uv: command not found` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Entorno desincronizado | `uv sync` (o `make setup` para recrearlo) |
| `Address already in use` en `make dev` | `make dev PORT=9000` |
| PDF sin texto | Solo PDFs con texto (no scans/OCR) |
| Rate limits | Reducir `BATCH_SIZE` o aumentar `LLM_BACKOFF_BASE` |
| JSON parse error | El pipeline auto-repara; revisar logs si persiste |
| Ejecución interrumpida | `make run-resume` |

## Estructura de Archivos

```
residenciafiscal/
├── Makefile                 # Interfaz de comandos (make help)
├── pyproject.toml           # Dependencias (uv) + ruff/mypy/pytest
├── uv.lock                  # Versiones exactas (versionado)
├── .python-version          # 3.13
├── residenciafiscal.py      # Pipeline principal
├── prompt.py                # System prompt + schema
├── config.py                # Configuración centralizada
├── ai_service_adapter.py    # Wrapper LLM
├── model_pricing.py         # Cálculo de costes
├── api/
│   └── main.py              # API HTTP (FastAPI)
├── test/
│   ├── test_api.py          # Tests de la capa HTTP (sin coste)
│   ├── test_gemini_model_policy.py
│   └── test_single_pdf.py   # Smoke test end-to-end (con coste)
├── sentencias/              # 106 PDFs entrada
│   ├── sentencias_CLAVE.txt # 23 sentencias premium
│   └── readme.txt           # Inventario
├── output/                  # Resultados generados
├── .venv/                   # Entorno gestionado por uv (gitignored)
├── .env                     # API keys (gitignored)
└── CLAUDE.md                # Este archivo
```

## Referencias

- [Art. 9 LIRPF](https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764) - Residencia habitual
- [Modelo OCDE Art. 4](https://www.oecd.org/tax/treaties/) - CDI tie-breaker rules
- [CENDOJ](https://www.poderjudicial.es/search/) - Fuente de sentencias
- [OpenAI API](https://platform.openai.com/docs)

## 🔍 Cross-review con Codex (segundo par de ojos)

Tras una feature/cambio **relevante**, lanzar automáticamente `/codex:review --wait` como gate de IA antes del primer commit.

**Posición en el flujo**: tests/lint verdes → `/codex:review --wait` → (aplicar fixes) → `git add/commit/push`. Pre-commit (no pre-push) para que los fixes entren en el mismo commit y la historia git quede limpia.

**Lanzar SÍ**: features nuevas, refactors multi-archivo, cambios en lógica crítica/seguridad/auth, infra/deploy, migraciones DB, o cualquier cambio donde el coste de un bug sea alto.
**Lanzar NO**: typos, comentarios, logging, formateo, cambios de 1 línea o exploración.
**En duda**: lanzar (coste bajo, upside alto).

**Si hay hallazgos serios**: `/codex:rescue --resume "aplica los fixes propuestos"` antes de commit.

**Features grandes con commits incrementales**: una sola review al cerrar la feature con `--scope branch --base main`; los fixes van en un commit final "address codex review" antes del push.
