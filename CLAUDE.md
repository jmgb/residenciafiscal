# CLAUDE.md

Guía para Claude Code en el proyecto **Residencia Fiscal** — [residenciafiscal.org](https://residenciafiscal.org).

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
make run-resume                           # continuar sobre el JSONL más reciente de ./output
make run-resume-from JSONL=./output/analisis_01012026_120000.jsonl   # sobre uno concreto
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
make test-llm                             # alias del smoke test real con 1 PDF (con coste)
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
| Allowlist de modelos | `modelo` solo acepta IDs declarados en `config.py` (ver `/config` → `modelos_permitidos`) para que el endpoint de pago no actúe como proxy abierto. El CLI sí admite IDs de OpenAI, Gemini, Groq y OpenRouter; ambos caminos comparten `detect_provider()`. |
| Validación de entrada | Solo `.pdf`; `reasoning_effort` ∈ {low, medium, high}; `max_pages` ≥ 1 (un valor negativo hacía que el pipeline no leyera páginas y devolviera un 200 con confianza BAJA). |

No hay rate limiting. Si algún día esto se expone más allá de la LAN, hay que añadirlo.

## Costes Estimados

| Modelo | Coste/PDF | 106 PDFs |
|--------|-----------|----------|
| gpt-5.6-luna (default) | $0.006 | $0.50 |
| gpt-5.6-sol (clave) | $0.10 | $2.30 |
| **Total mixto** | $0.026 avg | **$2.80** |

## Configuración (config.py)

```python
# Modelos
DEFAULT_MODEL = GPT_5_MINI           # gpt-5.6-luna
SENTENCIA_CLAVE_MODEL = GPT_5        # gpt-5.6-sol
REASONING_EFFORT = "medium"

# Procesamiento
BATCH_SIZE = 10                      # PDFs en paralelo
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
  defecto** (evita gasto accidental). `make test-llm` lanza el smoke de un PDF; el
  comparador se ejecuta explícitamente con
  `uv run python test/test_reasoning_effort_comparison.py`.

Gate antes de commitear: `make fast-check`.

En CI hay dos workflows, uno por área, ambos en push y PR contra `main`:

| Workflow | Cubre | Pasos |
|----------|-------|-------|
| `.github/workflows/ci.yml` | Python (todo salvo `docs/`, `sentencias/`, `*.md`) | ruff → mypy → pytest |
| `.github/workflows/frontend.yml` | `frontend/**` | biome → tsc → vitest |

**Ninguno usa secrets, a propósito**: la suite Python por defecto no llama a ningún
LLM. Si algún día hace falta un job con API real, va en un workflow aparte con
`workflow_dispatch`, nunca en estos. `uv sync --locked` además falla si `uv.lock` se
queda desincronizado de `pyproject.toml`.

`ci.yml` **no ignora `frontend/**`** aunque el frontend tenga su propio workflow: hay
tests de pytest que leen ficheros del frontend (`test_frontend_seo_assets.py` valida
`frontend/public/robots.txt`, `sitemap.xml` y `llms.txt`). Ignorarlo dejaría esos
tests sin gate, porque `frontend.yml` no corre pytest. Si añades un test Python que
lea otra ruta, comprueba que no esté en `paths-ignore`.

El gate del frontend cubre lint, tipos, tests y build, en ese orden:

- **Corre `npm run build`**, y con él los hooks `prebuild`/`postbuild` de npm. No
  necesita `output/`, que no se versiona: sin JSONL del pipeline,
  `frontend/scripts/build-corpus.mjs` conserva el `frontend/public/data/corpus.json`
  versionado y avisa por stderr.
- **Vitest corre sin `--passWithNoTests`**: ya hay suites en `frontend/tests/`, así que
  borrarlas accidentalmente vuelve a poner el gate rojo.

`frontend/biome.json` necesita `css.parser.tailwindDirectives: true` (el CSS usa
`@theme`/`@apply` de Tailwind 4) y `css.formatter.quoteStyle: "single"` (coherente con
el JS). Sin lo primero biome aborta el parseo del CSS y el lint no revisa 6 de los 15
ficheros. Ojo: `biome.json` **no admite comentarios** `//`, aunque sea JSONC en otros
contextos.

## Reanudar una ejecución

Cada ejecución escribe `analisis_DDMMYYYY_HHMMSS.jsonl`. Para continuar una tanda
interrumpida hay que apuntar al JSONL **anterior**, no al del timestamp nuevo:

```bash
make run-resume                                    # el más reciente de ./output
make run-resume-from JSONL=./output/analisis_01012026_120000.jsonl
```

`--skip-existing` resuelve el JSONL previo con `find_latest_jsonl()`, lee de él los
`archivo` ya procesados y le **añade** los nuevos resultados; el CSV y los exports se
regeneran completos con el timestamp de esta ejecución. Si no hay JSONL previo, avisa
y procesa todo.

## Troubleshooting

| Problema | Solución |
|----------|----------|
| `OPENAI_API_KEY not set` | Rellenar `.env` (`cp .env.example .env`) |
| `uv: command not found` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Entorno desincronizado | `uv sync` (o `make setup` para recrearlo) |
| `Address already in use` en `make dev` | `make dev PORT=9000` |
| PDF sin texto | Solo PDFs con texto (no scans/OCR) |
| Rate limits | Reducir `BATCH_SIZE` |
| JSON parse error | El pipeline auto-repara; revisar logs si persiste |
| Ejecución interrumpida | `make run-resume` (reanuda sobre el JSONL más reciente de `output/`) |

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
├── .github/workflows/
│   └── ci.yml               # Gate de CI: ruff + mypy + pytest (sin secrets)
├── test/
│   ├── test_api.py          # Tests de la capa HTTP (sin coste)
│   ├── test_resume.py       # Reanudación (find_latest_jsonl)
│   ├── test_gemini_model_policy.py
│   └── test_single_pdf.py   # Smoke test end-to-end (con coste)
├── sentencias/              # 106 PDFs entrada
│   ├── sentencias_CLAVE.txt # 23 sentencias premium
│   └── readme.txt           # Inventario
├── output/                  # Resultados generados
├── frontend/                # SPA React (residenciafiscal.org)
│   ├── src/                 # Código de la aplicación
│   ├── scripts/             # build-corpus.mjs
│   └── tests/               # Suites Vitest
├── netlify.toml             # Despliegue en Netlify (ver docs/operations/)
├── .venv/                   # Entorno gestionado por uv (gitignored)
├── .env                     # API keys (gitignored)
└── CLAUDE.md                # Este archivo
```

## Frontend (residenciafiscal.org)

SPA React en `frontend/`, desplegada en Netlify. Chatbot que consulta el corpus
de sentencias en lenguaje natural.

### Stack

Vite 7 + React 19 + TypeScript + Tailwind CSS v4 + Radix UI + zustand +
react-router-dom. Gestión de dependencias con `npm` (no hay Makefile de
frontend; el Makefile de la raíz solo cubre la parte Python).

### Comandos

```bash
cd frontend
npm install
npm run dev         # servidor de desarrollo en 127.0.0.1:5174
npm run test        # Vitest
npm run test:watch  # Vitest en modo watch
npm run typecheck   # tsc --noEmit
npm run lint        # Biome
npm run format      # Biome --write
npm run build       # prebuild (genera el corpus) + tsc --noEmit + vite build
npm run fast-check  # lint + typecheck + tests (gate pre-commit, análogo a `make fast-check`)
```

### Estructura

| Ruta | Función |
|---|---|
| `src/lib/chat-engine.ts` | Punto único de selección del motor. Cambiar aquí al conectar el backend |
| `src/lib/chat-engine.stub.ts` | Motor simulado con streaming y citas reales |
| `src/lib/corpus.ts` | Carga `public/data/corpus.json`; degrada a corpus vacío si falla |
| `src/stores/useConversations.ts` | Historial de conversaciones en localStorage |
| `src/components/layout/` | `SiteFooter` y `GoogleAnalyticsFooter` (integración GA4) |
| `src/components/chat/` | Componentes de la vista de chat (`ChatMessageContent`, ...) |
| `src/shared/components/ui/` | Primitivas de UI sobre Radix (button, sheet, tooltip...) |
| `src/types/chat.ts` | Tipos compartidos del motor de chat y del corpus |
| `scripts/build-corpus.mjs` | Genera `public/data/corpus.json` desde `output/analisis_*.jsonl` en el prebuild |
| `tests/` | Suites Vitest (`*.test.ts` / `*.test.tsx`) |

### Marca

La marca está documentada y tiene gate automático. Antes de producir cualquier
pieza visual o copy, consultar:

- [`docs/brand/brand-guidelines.md`](docs/brand/brand-guidelines.md) — brandbook
  canónico: isotipo, color (tabla de contraste), tipografía, voz y vetos.
- [`docs/brand/manifiesto.md`](docs/brand/manifiesto.md) — narrativa y manifiesto
  (versiones íntegra, corta y de una línea, con reglas de uso).

Fuentes únicas: `frontend/src/index.css` (tokens), `frontend/public/favicon.svg`
(isotipo), `frontend/src/assets/logo.svg` (lockup), `frontend/og/og-image.html`
(imagen OG). `favicon.ico`, `apple-touch-icon.png` y `og-image.png` son
**artefactos generados** (`npm run favicon` / `npm run og`): no editarlos a mano;
si cambia un token, regenerarlos en el mismo commit. El gate
`frontend/tests/brand-tokens.test.ts` (en `fast-check`) recalcula contrastes y
vigila HEX sueltos, escalas inexistentes y clases `control-*` sin definir.

### Estado del motor

El chat funciona hoy con un **stub**. `chatEngineMode` en
`src/lib/chat-engine.ts` vale `'stub'`, lo que activa el aviso de contenido
simulado en la UI. Al conectar el backend real hay que cambiarlo a `'live'`,
que apaga el aviso automáticamente.

Opciones de backend evaluadas y aún abiertas: ampliar la **API FastAPI ya
existente** (`api/main.py`) con un endpoint `/chat` — hoy el camino de menor
fricción —, Netlify Functions + OpenAI file_search, o Netlify Functions +
Supabase pgvector.

### Despliegue y analítica

`netlify.toml` en la raíz del repo (`base = "frontend"`, `publish = "dist"`),
con Cloudflare por delante del dominio. Configuración de DNS, TLS, WAF y
verificación en [`docs/operations/NETLIFY.md`](docs/operations/NETLIFY.md) y
[`docs/operations/CLOUDFLARE.md`](docs/operations/CLOUDFLARE.md). Integración
de Google Analytics 4 documentada en [`docs/ANALYTICS.md`](docs/ANALYTICS.md).

Al conectar el backend real hay que ampliar `connect-src` en la CSP de
`netlify.toml` con el origen de la API.

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
