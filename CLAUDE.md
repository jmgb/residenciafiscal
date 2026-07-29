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

# Ejecutar pipeline completo (106 PDFs → ~$3.40 USD, ~2-3h)
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
- **Resultado** (GANA_AEAT / GANA_CONTRIBUYENTE / PARCIAL y 4 más; catálogo
  canónico de 7 valores en `VALID_RESULTADO_FINAL`, `config.py`)

**Usuarios objetivo**: Investigadores fiscales, abogados tributaristas, compliance.

## Arquitectura

Dos frontends sobre el mismo núcleo: el **CLI por lotes** y la **API HTTP**. Ambos
llaman a `process_pdf_async()`, así que producen exactamente el mismo objeto.

Cada ejecución del CLI escribe los cinco exports (`.jsonl`, dos `.csv` planos,
`pruebas_*.csv` y `.xlsx`) con el mismo timestamp; la API no persiste nada.

### Extracción de texto de los PDF (no hay OCR)

Los PDF del CENDOJ son digitales con capa de texto embebida, así que el texto se
extrae con **pypdf** (`extract_pdf_text_with_pages()` en `residenciafiscal.py`):
Python puro, determinista y sin LLM. La función inserta marcadores de página
1-indexados y solo limpia `\x00`; el LLM recibe ese texto y **analiza, no
extrae**. El spike de verificación de citas (`citation_spike.py`) usa el mismo
extractor.

No hay OCR en el proyecto: un PDF escaneado (imagen, sin capa de texto) devuelve
texto vacío y no se procesa. Si algún día llega uno, las opciones son OCR
clásico (`ocrmypdf`/Tesseract) o un modelo de visión — no añadirlo antes de que
exista el caso real.

## Schema

El schema completo (criterios `CRIT_*`, las 12 categorías de prueba, campos de
razonamiento y resultado) es fuente única en `prompt.py` y `config.py`, y
`GET /config` lo expone en vivo. No duplicarlo aquí: se desincroniza.

### Verificación de citas

**Invariante jurídico bloqueante:** el texto de una sentencia no se reescribe,
corrige, completa ni parafrasea. Puede formatearse, pero una cita solo se publica
desde una subcadena exacta del texto bruto extraído del PDF. La normalización y
el matching fuzzy sirven para localizar candidatos, nunca para construir texto
judicial. Toda corrección o interpretación vive en metadatos/sidecars separados.

Las `frases_clave` del JSONL se contrastan con los PDF mediante un pipeline
determinista, sin llamadas LLM. El rollout está limitado primero a una sentencia,
después a una muestra fija de cinco y solo entonces al corpus completo. El
resultado separa localización de evidencia y fidelidad literal, y registra tanto
el índice físico del PDF como la etiqueta impresa. La arquitectura, las
puntuaciones, el manifiesto, el resultado del piloto y los gates están en
[`docs/CITATION_VERIFICATION.md`](docs/CITATION_VERIFICATION.md).

```bash
make verify-citations  # hoy: SAN_1071_2025.pdf, 4 citas, umbral provisional 85
```

### Exportación jurisprudencial OKF

El ciclo JSONL → perfil jurídico → verificación de todas las citas anidadas →
sidecars → Markdown OKF está
implementado únicamente para `SAN_1071_2025.pdf`. Genera un concepto, índices y
un snapshot del registro, además de un manifiesto de hashes, sin llamadas LLM.
No editar `knowledge/jurisprudencia/` a mano: se regenera con el pipeline. Las
revisiones viven en `knowledge/annotations/` y nunca pueden alterar el texto
legal. Arquitectura, contrato, resultado y gates:
[`docs/OKF_PIPELINE.md`](docs/OKF_PIPELINE.md).

```bash
make export-okf  # hoy: genera y valida exactamente 1 sentencia
```

## Sentencias Clave

Las sentencias listadas en `sentencias/sentencias_CLAVE.txt` usan automáticamente
**GPT-5** (modelo premium) **independientemente del `--model` indicado**, tanto por
CLI como por la API.

**Coste real medido**: ~$0.098/sentencia clave vs ~$0.014/sentencia normal
(ver «Costes Medidos»)

## Comandos Útiles

Todo pasa por el Makefile (`make help` los lista todos); el CLI subyacente sigue
disponible con `uv run python residenciafiscal.py --help`. Los no evidentes:

- `make run-resume` / `make run-resume-from JSONL=...` — ver "Reanudar una ejecución".
- `make fast-check` — el gate obligatorio antes de commitear (lint + tipos + tests).
- `make test` **no** llama a ningún LLM; `make test-llm` y `make test-single` sí
  **gastan dinero** (smoke real de 1 PDF).
- `make export-requirements` — solo para consumidores externos; el repo no versiona
  `requirements.txt`.

## API HTTP

`make dev` levanta FastAPI en `127.0.0.1:8010` (puerto 8010 y no 8000 para no chocar
con el backend de presupuestor). Rutas y esquemas, en `/docs`.

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

## Costes Medidos

Medidos sobre el `costo_usd` real del último run completo
(`analisis_02012026_155032.jsonl`), no estimados. Las cifras antiguas
($0.006/PDF, $2.80 el lote) eran ~2,5× optimistas e indujeron a error en
estimaciones posteriores.

| Modelo | Coste/PDF (media real) | Subtotal |
|--------|-----------------------:|---------:|
| gpt-5.6-luna (83 normales) | $0.014 | $1.18 |
| gpt-5.6-sol (23 clave) | $0.098 | $2.24 |
| **Total mixto (106)** | $0.032 avg | **$3.42** |

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

## Calidad de código

ruff, mypy y pytest están configurados en `pyproject.toml`. Lo que no se deduce de
ahí: los tests que llaman a LLMs reales van marcados `@pytest.mark.manual_real_llm`
y **quedan excluidos por defecto** (evita gasto accidental); `make test-llm` lanza
el smoke de un PDF, y el comparador se ejecuta explícitamente con
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

La configuración de biome tiene sus propias trampas: ver
[`frontend/CLAUDE.md`](frontend/CLAUDE.md).

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

## Ficheros públicos del repositorio

El repo está preparado para ser público. Al tocar estas piezas, ten en cuenta:

- **`LICENSE` (MIT) cubre código y documentación, no los PDFs.** Las sentencias
  de `sentencias/` son documentos del CENDOJ con sus propias condiciones de
  reutilización, recogidas en `sentencias/AVISO_LEGAL.md`. Si añades PDFs,
  actualiza el inventario (`readme.txt`) y comprueba ese aviso.
- **Nada de rutas absolutas** (`/home/ubuntu/...`) en código ni en documentación
  pública: usa rutas relativas a la raíz del repositorio.
- **Ningún workflow de CI usa secrets**, y debe seguir así. Ver la sección de
  calidad de código.
- El correo personal no aparece en ningún fichero versionado: los canales de
  contacto de `SECURITY.md` y `CODE_OF_CONDUCT.md` son los avisos privados de
  GitHub.

## Frontend (residenciafiscal.org)

SPA React en `frontend/`, desplegada en Netlify: chatbot que consulta el corpus
de sentencias en lenguaje natural. Trampas del stack, marca, estado del motor de
chat y despliegue están en [`frontend/CLAUDE.md`](frontend/CLAUDE.md), que se
carga solo al trabajar dentro de ese directorio.

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
