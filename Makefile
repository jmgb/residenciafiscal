# Residencia Fiscal — Makefile
# Requiere: uv (https://docs.astral.sh/uv/)
#
# Estructura:
#   1. ESENCIAL   — Lo que usas a diario (setup, dev, run)
#   2. PIPELINE   — Ejecuciones del análisis por lotes
#   3. CALIDAD    — Lint, format, typecheck, tests
#   4. DEPS       — Lock y actualización de dependencias
#   5. LIMPIEZA

SHELL := /bin/bash

.SILENT:
.PHONY: help setup dev dev-api dev-frontend dev-public serve \
	run run-sample run-resume run-resume-from run-list \
	verify-citations export-okf export-okf-sample export-verbatim export-case-v3 \
	export-case-v3-derivatives export-case-v3-sample evaluate-retrieval-phase-d \
	evaluate-holdout-e0 rollout-init rollout-status rollout-next \
	file-search-prepare compare-chat-strategies build-chat-f03-review \
	file-search-delete \
	descargar-normativa export-normativa enlazar-normativa \
	test test-llm test-single \
	lint format format-check fix typecheck fast-check \
	lock upgrade export-requirements \
	clean clean-output env-print

# Mantener sincronizado con .python-version
PY ?= 3.13
export UV_PROJECT_ENVIRONMENT := .venv
PYTHON_SOURCE := src
export PYTHONPATH := $(CURDIR)/$(PYTHON_SOURCE)

HOST ?= 127.0.0.1
PORT ?= 8010

INPUT ?= ./sentencias
OUTPUT ?= ./output
MODEL ?=
EFFORT ?=
MAX_FILES ?=
CITATION_JSONL ?= $(shell ls -t output/analisis_*.jsonl 2>/dev/null | head -1)
CITATION_THRESHOLD ?= 85
CITATION_SOURCE_FILE ?= SAN_1071_2025.pdf
OKF_JSONL ?= $(CITATION_JSONL)
OKF_THRESHOLD ?= 85
OKF_SOURCE_FILE ?= SAN_1071_2025.pdf
OKF_OUTPUT ?= ./knowledge/jurisprudencia
NORMATIVA_JURISDICCION ?= es
NORMATIVA_JSONL ?= $(CITATION_JSONL)
NORMATIVA_SOURCES ?= ./normativa
NORMATIVA_OUTPUT ?= ./knowledge/normativa
OKF_SAMPLE_MANIFEST ?= ./sentencias/okf_muestra_5.json
OKF_SAMPLE_OUTPUT ?= ./knowledge/jurisprudencia-muestra-5
VERBATIM_PDF ?= ./sentencias/SAN_1210_2023.pdf
VERBATIM_DOCUMENT_ID ?= san-1210-2023
VERBATIM_SOURCE_FILE ?= sentencias/SAN_1210_2023.pdf
VERBATIM_OUTPUT ?= ./knowledge/jurisprudencia-v3/verbatim/san-1210-2023.pages.json
CASE_PROPOSAL ?= ./knowledge/jurisprudence-case-proposals/san-1210-2023.proposal.json
CASE_VERBATIM ?= $(VERBATIM_OUTPUT)
CASE_EVALUATION ?= ./knowledge/jurisprudencia-v3/evaluations/san-1210-2023.questions.json
CASE_OUTPUT ?= ./knowledge/jurisprudencia-v3/cases/san-1210-2023.case.json
CASE_REPORT ?= ./knowledge/jurisprudencia-v3/reports/san-1210-2023.case-validation.json
FILE_SEARCH_STATE ?= ./output/file-search/f0-store.json
FILE_SEARCH_LOG ?= ./output/logs/chat-strategy-comparison.jsonl
FILE_SEARCH_MODEL ?= gemini-3.5-flash-lite
CHAT_QUESTION ?=
CHAT_F03_MANIFEST ?= ./docs/experiments/CHAT_STRATEGY_F03_BUILD.json
CHAT_F03_PACKAGE_JSON ?= ./docs/experiments/CHAT_STRATEGY_F03_BLIND_REVIEW.json
CHAT_F03_PACKAGE_MD ?= ./docs/experiments/CHAT_STRATEGY_F03_BLIND_REVIEW.md
CHAT_F03_REVIEW_FORM ?= ./docs/experiments/CHAT_STRATEGY_F03_REVIEW_FORM_TEMPLATE.md
CHAT_F03_REVEAL_KEY ?= ./docs/experiments/CHAT_STRATEGY_F03_REVEAL_KEY.json
CASE_MARKDOWN_OUTPUT ?= ./knowledge/jurisprudencia-v3/perfiles/san-1210-2023.md
CASE_RETRIEVAL_OUTPUT ?= ./knowledge/jurisprudencia-v3/retrieval/san-1210-2023.issues.json
CASE_DERIVATIVES_REPORT ?= ./knowledge/jurisprudencia-v3/reports/san-1210-2023.derivatives-validation.json
CASE_SAMPLE_MANIFEST ?= ./sentencias/jurisprudence_v3_sample_5.json
CASE_SAMPLE_OUTPUT ?= ./knowledge/jurisprudencia-v3
CASE_QUESTION_PILOT ?= ./docs/experiments/CHAT_QUESTION_PILOT_5.md
CASE_PARAPHRASES ?= ./docs/experiments/CHAT_QUESTION_PARAPHRASES_5.json
CASE_PHASE_D_REPORT ?= ./knowledge/jurisprudencia-v3/reports/phase-d-retrieval-evaluation.json
CASE_HOLDOUT_LOCK ?= ./docs/experiments/CHAT_QUESTION_HOLDOUT_E.lock.json
CASE_HOLDOUT_REPORT ?= ./knowledge/jurisprudencia-v3/reports/phase-e0-holdout-evaluation.json
CASE_ROLLOUT_MANIFEST ?=
CASE_ROLLOUT_STATE ?= ./output/jurisprudence-v3-rollout-state.json
CASE_ROLLOUT_OUTPUT ?= ./knowledge/jurisprudencia-v3
ROLLOUT_RETRY ?=

# Flags opcionales: solo se añaden si la variable tiene valor
RUN_FLAGS := --input $(INPUT) --output $(OUTPUT)
ifneq ($(MODEL),)
RUN_FLAGS += --model $(MODEL)
endif
ifneq ($(EFFORT),)
RUN_FLAGS += --reasoning-effort $(EFFORT)
endif
ifneq ($(MAX_FILES),)
RUN_FLAGS += --max-files $(MAX_FILES)
endif

# =============================================================================
# 1. ESENCIAL
# =============================================================================
help:
	@echo "=== ESENCIAL ==="
	@echo "  make setup                Crea .venv con uv e instala dependencias"
	@echo "  make dev                  Levanta API + frontend en desarrollo"
	@echo "  make dev-api              Levanta solo la API con reload en $(HOST):$(PORT)"
	@echo "  make dev-frontend         Levanta solo el frontend en http://127.0.0.1:5174"
	@echo "  make dev-public           Igual pero accesible desde la red local (0.0.0.0)"
	@echo "  make serve                API sin reload (modo producción local)"
	@echo ""
	@echo "=== PIPELINE ==="
	@echo "  make run                  Procesa todos los PDFs de $(INPUT)"
	@echo "  make run-sample           Procesa 1 PDF (prueba rápida, ~\$$0.01)"
	@echo "  make run-resume           Continúa sobre el JSONL más reciente de $(OUTPUT)"
	@echo "  make run-resume-from JSONL=x.jsonl  Continúa sobre un JSONL concreto"
	@echo "  make run-list LIST=x.txt  Procesa solo los PDFs listados en un .txt"
	@echo "  make verify-citations     Verifica frases_clave contra los PDF (sin LLM)"
	@echo "  make export-okf           Genera el bundle OKF piloto de 1 sentencia (sin LLM)"
	@echo "  make export-okf-sample    Genera la muestra OKF congelada (sin llamadas LLM)"
	@echo "  make export-verbatim      Genera y revalida el verbatim piloto (sin LLM)"
	@echo "  make export-case-v3       Compila y valida el caso v3 piloto (sin LLM)"
	@echo "  make export-case-v3-derivatives  Deriva OKF e índice del caso v3 (sin LLM)"
	@echo "  make export-case-v3-sample  Regenera y evalúa las 5 sentencias v3 (sin LLM)"
	@echo "  make evaluate-retrieval-phase-d  Compara baseline y recuperación estructurada"
	@echo "  make evaluate-holdout-e0  Mide el holdout congelado sin ajustar el router"
	@echo "  make file-search-prepare CONFIRM_PAID=1  Crea el store F0 y sube los 5 PDF"
	@echo "  make compare-chat-strategies CONFIRM_PAID=1 CHAT_QUESTION='...'  Ejecuta F0 con $(FILE_SEARCH_MODEL)"
	@echo "  make build-chat-f03-review  Regenera el paquete ciego F0.3 (sin LLM)"
	@echo "  make file-search-delete CONFIRM_DELETE=1  Elimina explícitamente el store F0"
	@echo "  make rollout-init         Inicializa estado; requiere CASE_ROLLOUT_MANIFEST"
	@echo "  make rollout-status       Inspecciona lotes sin ejecutar documentos"
	@echo "  make rollout-next         Ejecuta/reanuda un lote explícito"
	@echo "  make descargar-normativa  Baja del BOE el XML de las normas (con red, ~3 min)"
	@echo "  make export-normativa     Genera los preceptos legales en Markdown (sin LLM)"
	@echo "  make enlazar-normativa    Resuelve las citas de las sentencias a los preceptos"
	@echo "  Variables: INPUT= OUTPUT= MODEL= EFFORT=low|medium|high MAX_FILES="
	@echo "  Verificación: CITATION_SOURCE_FILE= CITATION_JSONL= CITATION_THRESHOLD="
	@echo "  OKF: OKF_SOURCE_FILE= OKF_JSONL= OKF_THRESHOLD= OKF_OUTPUT="
	@echo "  Muestra OKF: OKF_SAMPLE_MANIFEST= OKF_SAMPLE_OUTPUT="
	@echo "  Verbatim: VERBATIM_PDF= VERBATIM_DOCUMENT_ID= VERBATIM_SOURCE_FILE= VERBATIM_OUTPUT="
	@echo "  Caso v3: CASE_PROPOSAL= CASE_VERBATIM= CASE_EVALUATION= CASE_OUTPUT= CASE_REPORT="
	@echo "  Derivados v3: CASE_MARKDOWN_OUTPUT= CASE_RETRIEVAL_OUTPUT= CASE_DERIVATIVES_REPORT="
	@echo "  Muestra v3: CASE_SAMPLE_MANIFEST= CASE_SAMPLE_OUTPUT= CASE_QUESTION_PILOT="
	@echo "  Fase D: CASE_PARAPHRASES= CASE_PHASE_D_REPORT="
	@echo "  Fase E0: CASE_HOLDOUT_LOCK= CASE_HOLDOUT_REPORT="
	@echo "  Rollout: CASE_ROLLOUT_MANIFEST= CASE_ROLLOUT_STATE= CASE_ROLLOUT_OUTPUT= ROLLOUT_RETRY=1"
	@echo ""
	@echo "=== CALIDAD ==="
	@echo "  make fast-check           Lint + format + typecheck + tests (gate pre-commit)"
	@echo "  make lint                 Ruff check"
	@echo "  make format               Ruff format"
	@echo "  make format-check         Comprueba que Ruff format está aplicado"
	@echo "  make fix                  Ruff format + check --fix"
	@echo "  make typecheck            Mypy"
	@echo "  make test                 Pytest (sin tests de LLM real)"
	@echo "  make test-llm             Alias del smoke test real con 1 PDF (con coste)"
	@echo "  make test-single          Script de humo: 1 PDF end-to-end"
	@echo ""
	@echo "=== DEPS ==="
	@echo "  make lock                 Regenera uv.lock"
	@echo "  make upgrade              Actualiza dependencias dentro de los rangos"
	@echo "  make export-requirements  Genera requirements.txt desde el lock"
	@echo ""
	@echo "=== LIMPIEZA ==="
	@echo "  make clean                Borra caches (__pycache__, .ruff_cache, .pytest_cache)"
	@echo "  make clean-output         Borra los artefactos generados en $(OUTPUT)"

setup:
	uv python install $(PY)
	uv venv --python $(PY) $(UV_PROJECT_ENVIRONMENT)
	uv sync
	@echo "✅ Entorno listo. Recuerda tener OPENAI_API_KEY en .env"

dev:
	@set -m; \
	uv run python -m fastapi dev $(PYTHON_SOURCE)/api/main.py --host $(HOST) --port $(PORT) & api_pid=$$!; \
	(cd frontend && npm run dev) & frontend_pid=$$!; \
	trap 'kill "$$api_pid" "$$frontend_pid" 2>/dev/null || true' EXIT INT TERM; \
	wait -n "$$api_pid" "$$frontend_pid"

dev-api:
	uv run python -m fastapi dev $(PYTHON_SOURCE)/api/main.py --host $(HOST) --port $(PORT)

dev-frontend:
	cd frontend && npm run dev

dev-public:
	@echo "⚠️  Escuchando en 0.0.0.0: /analizar gasta dinero en cada llamada."
	@echo "   Define RESIDENCIAFISCAL_API_TOKEN en .env para exigir la cabecera X-API-Token."
	$(MAKE) HOST=0.0.0.0 dev

serve:
	uv run uvicorn --app-dir $(PYTHON_SOURCE) api.main:app --host $(HOST) --port $(PORT)

# =============================================================================
# 2. PIPELINE
# =============================================================================
run:
	uv run python $(PYTHON_SOURCE)/residenciafiscal.py $(RUN_FLAGS)

run-sample:
	uv run python $(PYTHON_SOURCE)/residenciafiscal.py --input $(INPUT) --output $(OUTPUT) --max-files 1

run-resume:
	uv run python $(PYTHON_SOURCE)/residenciafiscal.py $(RUN_FLAGS) --skip-existing

run-resume-from:
	@if [ -z "$(JSONL)" ]; then echo "❌ Falta JSONL=. Ej: make run-resume-from JSONL=./output/analisis_01012026_120000.jsonl"; exit 1; fi
	uv run python $(PYTHON_SOURCE)/residenciafiscal.py $(RUN_FLAGS) --resume-from $(JSONL)

run-list:
	@if [ -z "$(LIST)" ]; then echo "❌ Falta LIST=. Ej: make run-list LIST=./mi_lista.txt"; exit 1; fi
	uv run python $(PYTHON_SOURCE)/residenciafiscal.py $(RUN_FLAGS) --pdf-list $(LIST)

verify-citations:
	@if [ -z "$(CITATION_JSONL)" ]; then echo "❌ No hay output/analisis_*.jsonl"; exit 1; fi
	uv run python $(PYTHON_SOURCE)/verify_citations.py \
		--jsonl $(CITATION_JSONL) \
		--pdf-dir $(INPUT) \
		--output-dir $(OUTPUT)/citation-verification \
		--source-file $(CITATION_SOURCE_FILE) \
		--threshold $(CITATION_THRESHOLD)

export-okf:
	@if [ -z "$(OKF_JSONL)" ]; then echo "❌ No hay output/analisis_*.jsonl"; exit 1; fi
	uv run python $(PYTHON_SOURCE)/export_okf.py \
		--jsonl $(OKF_JSONL) \
		--pdf-dir $(INPUT) \
		--output-dir $(OKF_OUTPUT) \
		--annotations-dir knowledge/annotations \
		--source-file $(OKF_SOURCE_FILE) \
		--threshold $(OKF_THRESHOLD)

export-okf-sample:
	@if [ -z "$(OKF_JSONL)" ]; then echo "❌ No hay output/analisis_*.jsonl"; exit 1; fi
	uv run python $(PYTHON_SOURCE)/export_okf_batch.py \
		--jsonl $(OKF_JSONL) \
		--pdf-dir $(INPUT) \
		--output-dir $(OKF_SAMPLE_OUTPUT) \
		--annotations-dir knowledge/annotations \
		--manifest $(OKF_SAMPLE_MANIFEST) \
		--threshold $(OKF_THRESHOLD)

export-verbatim:
	uv run python $(PYTHON_SOURCE)/export_verbatim.py \
		--pdf $(VERBATIM_PDF) \
		--document-id $(VERBATIM_DOCUMENT_ID) \
		--source-file $(VERBATIM_SOURCE_FILE) \
		--output $(VERBATIM_OUTPUT) \
		--project-root .

export-case-v3:
	uv run python $(PYTHON_SOURCE)/export_jurisprudence_case.py \
		--proposal $(CASE_PROPOSAL) \
		--verbatim $(CASE_VERBATIM) \
		--evaluation $(CASE_EVALUATION) \
		--output $(CASE_OUTPUT) \
		--report $(CASE_REPORT) \
		--project-root .

export-case-v3-derivatives:
	uv run python $(PYTHON_SOURCE)/export_jurisprudence_case_derivatives.py \
		--case $(CASE_OUTPUT) \
		--verbatim $(CASE_VERBATIM) \
		--markdown $(CASE_MARKDOWN_OUTPUT) \
		--retrieval $(CASE_RETRIEVAL_OUTPUT) \
		--report $(CASE_DERIVATIVES_REPORT) \
		--project-root .

export-case-v3-sample:
	uv run python $(PYTHON_SOURCE)/export_jurisprudence_sample.py \
		--manifest $(CASE_SAMPLE_MANIFEST) \
		--output-root $(CASE_SAMPLE_OUTPUT) \
		--project-root .
	uv run python $(PYTHON_SOURCE)/export_jurisprudence_sample_evaluation.py \
		--manifest $(CASE_SAMPLE_MANIFEST) \
		--pilot $(CASE_QUESTION_PILOT) \
		--retrieval-root $(CASE_SAMPLE_OUTPUT)/retrieval \
		--output-root $(CASE_SAMPLE_OUTPUT) \
		--project-root .
	uv run python $(PYTHON_SOURCE)/jurisprudence_sample_quality.py \
		--cases-root $(CASE_SAMPLE_OUTPUT)/cases \
		--manifest $(CASE_SAMPLE_MANIFEST) \
		--output $(CASE_SAMPLE_OUTPUT)/reports/sample-5.quality.json \
		--project-root .
	uv run python $(PYTHON_SOURCE)/jurisprudence_legacy_citations.py \
		--dispositions $(CASE_SAMPLE_OUTPUT)/evaluations/legacy-citation-dispositions.json \
		--legacy-reports-root knowledge/jurisprudencia-muestra-5/reports \
		--cases-root $(CASE_SAMPLE_OUTPUT)/cases

evaluate-retrieval-phase-d:
	uv run python $(PYTHON_SOURCE)/export_jurisprudence_phase_d.py \
		--corpus $(CASE_SAMPLE_OUTPUT)/retrieval/corpus.json \
		--pilot $(CASE_QUESTION_PILOT) \
		--paraphrases $(CASE_PARAPHRASES) \
		--output $(CASE_PHASE_D_REPORT)

evaluate-holdout-e0:
	uv run python $(PYTHON_SOURCE)/jurisprudence_holdout_evaluation.py \
		--corpus $(CASE_SAMPLE_OUTPUT)/retrieval/corpus.json \
		--lock $(CASE_HOLDOUT_LOCK) \
		--output $(CASE_HOLDOUT_REPORT) \
		--project-root .

file-search-prepare:
	@test "$(CONFIRM_PAID)" = "1" || \
		(echo "CONFIRM_PAID=1 es obligatorio: indexar genera coste" >&2; exit 2)
	uv run python $(PYTHON_SOURCE)/gemini_file_search_cli.py prepare-store \
		--state $(FILE_SEARCH_STATE) \
		--confirm-paid

compare-chat-strategies:
	@test "$(CONFIRM_PAID)" = "1" || \
		(echo "CONFIRM_PAID=1 es obligatorio: consultar genera coste" >&2; exit 2)
	@test -n "$(CHAT_QUESTION)" || \
		(echo "CHAT_QUESTION es obligatorio" >&2; exit 2)
	uv run python $(PYTHON_SOURCE)/gemini_file_search_cli.py compare \
		"$(CHAT_QUESTION)" \
		--state $(FILE_SEARCH_STATE) \
		--log $(FILE_SEARCH_LOG) \
		--model $(FILE_SEARCH_MODEL) \
		--confirm-paid

build-chat-f03-review:
	uv run python $(PYTHON_SOURCE)/chat_blind_review.py \
		--project-root . \
		--manifest $(CHAT_F03_MANIFEST) \
		--package-json $(CHAT_F03_PACKAGE_JSON) \
		--package-markdown $(CHAT_F03_PACKAGE_MD) \
		--review-form $(CHAT_F03_REVIEW_FORM) \
		--reveal-key $(CHAT_F03_REVEAL_KEY)

file-search-delete:
	@test "$(CONFIRM_DELETE)" = "1" || \
		(echo "CONFIRM_DELETE=1 es obligatorio" >&2; exit 2)
	uv run python $(PYTHON_SOURCE)/gemini_file_search_cli.py delete-store \
		--state $(FILE_SEARCH_STATE) \
		--confirm-delete

rollout-init:
	@test -n "$(CASE_ROLLOUT_MANIFEST)" || \
		(echo "CASE_ROLLOUT_MANIFEST es obligatorio" >&2; exit 2)
	uv run python $(PYTHON_SOURCE)/jurisprudence_rollout_cli.py init \
		--manifest $(CASE_ROLLOUT_MANIFEST) \
		--state $(CASE_ROLLOUT_STATE)

rollout-status:
	uv run python $(PYTHON_SOURCE)/jurisprudence_rollout_cli.py status \
		--state $(CASE_ROLLOUT_STATE)

rollout-next:
	@test -n "$(CASE_ROLLOUT_MANIFEST)" || \
		(echo "CASE_ROLLOUT_MANIFEST es obligatorio" >&2; exit 2)
	uv run python $(PYTHON_SOURCE)/jurisprudence_rollout_cli.py run-next \
		--manifest $(CASE_ROLLOUT_MANIFEST) \
		--state $(CASE_ROLLOUT_STATE) \
		--output-root $(CASE_ROLLOUT_OUTPUT) \
		--project-root . $(if $(ROLLOUT_RETRY),--retry-failed,)

# Solo hay que relanzarlo cuando el BOE actualice una norma: el XML descargado
# está versionado, así que `make export-normativa` funciona sin red.
descargar-normativa:
	uv run python $(PYTHON_SOURCE)/descargar_normativa.py \
		--output-dir $(NORMATIVA_SOURCES)/$(NORMATIVA_JURISDICCION)

export-normativa:
	uv run python $(PYTHON_SOURCE)/export_normativa.py \
		--jurisdiccion $(NORMATIVA_JURISDICCION) \
		--sources-root $(NORMATIVA_SOURCES) \
		--output-root $(NORMATIVA_OUTPUT)

enlazar-normativa:
	@if [ -z "$(NORMATIVA_JSONL)" ]; then echo "❌ No hay output/analisis_*.jsonl"; exit 1; fi
	uv run python $(PYTHON_SOURCE)/enlazar_normativa.py \
		--jsonl $(NORMATIVA_JSONL) \
		--jurisdiccion $(NORMATIVA_JURISDICCION) \
		--corpus-root $(NORMATIVA_OUTPUT)

# =============================================================================
# 3. CALIDAD
# =============================================================================
fast-check: lint format-check typecheck test

lint:
	uv run ruff check .

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

fix:
	uv run ruff format . && uv run ruff check . --fix

typecheck:
	uv run mypy .

test:
	uv run pytest -q

test-llm: test-single

test-single:
	uv run python tests/test_single_pdf.py

# =============================================================================
# 4. DEPS
# =============================================================================
lock:
	uv lock

upgrade:
	uv lock --upgrade && uv sync

export-requirements:
	uv export --no-hashes --no-dev --format requirements-txt -o requirements.txt
	@echo "✅ requirements.txt regenerado desde uv.lock (no editar a mano)"

# =============================================================================
# 5. LIMPIEZA
# =============================================================================
# -prune corta la recursión en .venv/.git/node_modules en vez de recorrerlos enteros
# para descartarlos después: frontend/node_modules son decenas de miles de ficheros.
clean:
	find . -type d \( -name .venv -o -name .git -o -name node_modules \) -prune -o \
		-type d -name __pycache__ -print0 | xargs -0 -r rm -rf
	rm -rf .ruff_cache .pytest_cache .mypy_cache
	@echo "✅ Caches eliminadas"

clean-output:
	rm -f $(OUTPUT)/*.jsonl $(OUTPUT)/*.csv $(OUTPUT)/*.xlsx
	@echo "✅ Artefactos de $(OUTPUT) eliminados"

env-print:
	@echo "PY=$(PY)  VENV=$(UV_PROJECT_ENVIRONMENT)  HOST=$(HOST)  PORT=$(PORT)"
	@echo "INPUT=$(INPUT)  OUTPUT=$(OUTPUT)"
	uv run python -V
