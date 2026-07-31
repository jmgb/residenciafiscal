# Pruebas

La suite de Python vive en `tests/` y se ejecuta con pytest. Por defecto es
determinista, no llama a proveedores LLM y no necesita secrets.

## Comandos

```bash
make test          # pytest sin llamadas LLM reales
make fast-check    # lint + formato + mypy + pytest
```

Los experimentos conversacionales de pago se ejecutan desde targets que exigen
`CONFIRM_PAID=1`; nunca forman parte de pytest.

## Organización

| Grupo | Cobertura |
|---|---|
| `test_api.py`, `test_sentry_config.py` | API FastAPI de estado/contratos y telemetría |
| `test_llm_architecture_boundary.py` | Corpus offline sin gateway; política LLM exclusiva del chat |
| `test_citation_*.py`, `test_verify_citations_cli.py` | Matching, fidelidad literal y CLI de citas |
| `test_jurisprudence_*.py` | Caso v3, retrieval, evaluaciones y rollout |
| `test_okf_*.py` | Normalización, anotaciones, bundles y renderizado OKF |
| `test_normativa_*.py` | Fidelidad del XML del BOE y enlaces a preceptos |
| `test_verbatim_*.py` | Extracción por páginas, hashes, schemas y artefactos |
| `fixtures/` | Entradas mínimas válidas e inválidas |
| `test_outputs/` | Resultados locales de pruebas; ignorados por Git |

Las factories compartidas permanecen en `tests/` para que pytest las encuentre a
través del `pythonpath` configurado.

No añadas smoke tests que envíen PDF a un proveedor. La preparación del corpus
se prueba con fixtures, verbatim y compiladores deterministas. Las pruebas
reales del chat parten de preguntas y evidencia ya recuperada.

## Añadir una prueba

- Usa `test_<área>.py` y nombres `test_<comportamiento>`.
- Prefiere fixtures mínimas y deterministas.
- Guarda artefactos efímeros en `tmp_path` o `tests/test_outputs/`.
- Si cambias un contrato JSON, añade un caso válido, mutaciones inválidas y una
  comprobación del schema versionado en `schemas/`.
- Ejecuta `make fast-check` antes de abrir un PR.
