# Pruebas

La suite de Python vive en `tests/` y se ejecuta con pytest. Por defecto es
determinista, no llama a proveedores LLM y no necesita secrets.

## Comandos

```bash
make test          # pytest sin llamadas LLM reales
make fast-check    # lint + formato + mypy + pytest
make test-single   # smoke end-to-end con 1 PDF; realiza una llamada de pago
make test-llm      # alias de make test-single
```

Los scripts que usan un proveedor real llevan el marker
`manual_real_llm`. `pyproject.toml` los excluye de la ejecución ordinaria.

## Organización

| Grupo | Cobertura |
|---|---|
| `test_api.py`, `test_sentry_config.py` | API FastAPI, validación de entradas y telemetría |
| `test_citation_*.py`, `test_verify_citations_cli.py` | Matching, fidelidad literal y CLI de citas |
| `test_jurisprudence_*.py` | Caso v3, retrieval, evaluaciones y rollout |
| `test_okf_*.py` | Normalización, anotaciones, bundles y renderizado OKF |
| `test_normativa_*.py` | Fidelidad del XML del BOE y enlaces a preceptos |
| `test_verbatim_*.py` | Extracción por páginas, hashes, schemas y artefactos |
| `fixtures/` | Entradas mínimas válidas e inválidas |
| `test_outputs/` | Resultados locales de pruebas; ignorados por Git |

Las factories compartidas permanecen en `tests/` para que pytest las encuentre a
través del `pythonpath` configurado.

## Smoke test con un PDF

`make test-single`:

1. crea directorios temporales;
2. copia una sentencia de `sentencias/`;
3. ejecuta `src/residenciafiscal.py`;
4. comprueba que se generen JSONL y CSV;
5. muestra un resumen y elimina el entorno temporal.

Requisitos:

```bash
make setup
cp .env.example .env  # configura al menos un proveedor
make test-single
```

El equivalente directo es:

```bash
uv run python tests/test_single_pdf.py
```

## Comparación de reasoning effort

El comparador procesa el mismo PDF varias veces y tiene un coste mayor:

```bash
uv run python tests/test_reasoning_effort_comparison.py
uv run python tests/test_reasoning_effort_comparison.py \
  --pdf sentencias/STS_4220_2024.pdf
```

No incorpores estos scripts a la suite predeterminada. Cualquier test con red o
coste debe ser explícito y quedar fuera del CI ordinario.

## Añadir una prueba

- Usa `test_<área>.py` y nombres `test_<comportamiento>`.
- Prefiere fixtures mínimas y deterministas.
- Guarda artefactos efímeros en `tmp_path` o `tests/test_outputs/`.
- Si cambias un contrato JSON, añade un caso válido, mutaciones inválidas y una
  comprobación del schema versionado en `schemas/`.
- Ejecuta `make fast-check` antes de abrir un PR.
