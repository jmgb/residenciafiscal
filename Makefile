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
.PHONY: help setup dev dev-public serve \
	run run-sample run-resume run-resume-from run-list \
	test test-llm test-single \
	lint format fix typecheck fast-check \
	lock upgrade export-requirements \
	clean clean-output env-print

# Mantener sincronizado con .python-version
PY ?= 3.13
export UV_PROJECT_ENVIRONMENT := .venv

HOST ?= 127.0.0.1
PORT ?= 8010

INPUT ?= ./sentencias
OUTPUT ?= ./output
MODEL ?=
EFFORT ?=
MAX_FILES ?=

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
	@echo "  make dev                  Levanta la API con reload en $(HOST):$(PORT)"
	@echo "  make dev-public           Igual pero accesible desde la red local (0.0.0.0)"
	@echo "  make serve                API sin reload (modo producción local)"
	@echo ""
	@echo "=== PIPELINE ==="
	@echo "  make run                  Procesa todos los PDFs de $(INPUT)"
	@echo "  make run-sample           Procesa 1 PDF (prueba rápida, ~\$$0.01)"
	@echo "  make run-resume           Continúa sobre el JSONL más reciente de $(OUTPUT)"
	@echo "  make run-resume-from JSONL=x.jsonl  Continúa sobre un JSONL concreto"
	@echo "  make run-list LIST=x.txt  Procesa solo los PDFs listados en un .txt"
	@echo "  Variables: INPUT= OUTPUT= MODEL= EFFORT=low|medium|high MAX_FILES="
	@echo ""
	@echo "=== CALIDAD ==="
	@echo "  make fast-check           Lint + typecheck + tests (gate pre-commit)"
	@echo "  make lint                 Ruff check"
	@echo "  make format               Ruff format"
	@echo "  make fix                  Ruff format + check --fix"
	@echo "  make typecheck            Mypy"
	@echo "  make test                 Pytest (sin tests de LLM real)"
	@echo "  make test-llm             Pytest incluyendo llamadas LLM reales (con coste)"
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
	uv run python -m fastapi dev api/main.py --host $(HOST) --port $(PORT)

dev-public:
	@echo "⚠️  Escuchando en 0.0.0.0: /analizar gasta dinero en cada llamada."
	@echo "   Define RESIDENCIAFISCAL_API_TOKEN en .env para exigir la cabecera X-API-Token."
	$(MAKE) HOST=0.0.0.0 dev

serve:
	uv run uvicorn api.main:app --host $(HOST) --port $(PORT)

# =============================================================================
# 2. PIPELINE
# =============================================================================
run:
	uv run python residenciafiscal.py $(RUN_FLAGS)

run-sample:
	uv run python residenciafiscal.py --input $(INPUT) --output $(OUTPUT) --max-files 1

run-resume:
	uv run python residenciafiscal.py $(RUN_FLAGS) --skip-existing

run-resume-from:
	@if [ -z "$(JSONL)" ]; then echo "❌ Falta JSONL=. Ej: make run-resume-from JSONL=./output/analisis_01012026_120000.jsonl"; exit 1; fi
	uv run python residenciafiscal.py $(RUN_FLAGS) --resume-from $(JSONL)

run-list:
	@if [ -z "$(LIST)" ]; then echo "❌ Falta LIST=. Ej: make run-list LIST=./mi_lista.txt"; exit 1; fi
	uv run python residenciafiscal.py $(RUN_FLAGS) --pdf-list $(LIST)

# =============================================================================
# 3. CALIDAD
# =============================================================================
fast-check: lint typecheck test

lint:
	uv run ruff check .

format:
	uv run ruff format .

fix:
	uv run ruff format . && uv run ruff check . --fix

typecheck:
	uv run mypy .

test:
	uv run pytest -q

test-llm:
	uv run pytest -q -m manual_real_llm

test-single:
	uv run python test/test_single_pdf.py

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
