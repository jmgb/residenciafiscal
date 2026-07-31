# Estructura del repositorio

La raíz contiene únicamente puntos de entrada del proyecto, configuración y
directorios con una responsabilidad clara. El código Python ya no vive mezclado
con esos archivos.

```text
.
├── .github/          # workflows, plantillas de issues y PR
├── docs/             # documentación por área e índice central
├── frontend/         # SPA React y funciones de Netlify
├── knowledge/        # corpus derivados y versionados
├── normativa/        # fuentes XML oficiales, por jurisdicción
├── output/           # ejecuciones locales y logs; ignorado por Git
├── schemas/          # contratos JSON Schema
├── scripts/          # operación fuera del runtime; hoy solo backups de la BD
├── sentencias/       # fuentes PDF oficiales y manifiestos de muestras
├── src/              # código Python y CLIs
│   └── api/          # aplicación FastAPI
├── tests/            # suite pytest, fixtures y scripts de humo
├── README.md         # presentación y quick start
├── CLAUDE.md         # guía operativa para desarrollo asistido
├── CONTRIBUTING.md   # proceso de contribución
├── Makefile          # interfaz estable de comandos
└── pyproject.toml    # dependencias y herramientas Python
```

## Qué pertenece en cada sitio

| Tipo de archivo | Destino |
|---|---|
| Lógica Python importable o CLI Python | `src/` |
| Rutas HTTP y configuración de FastAPI | `src/api/` |
| Tests, factories y fixtures | `tests/` |
| Guías de arquitectura o desarrollo | `docs/` en el área correspondiente |
| Fuente jurídica original | `sentencias/` o `normativa/<jurisdicción>/` |
| Corpus regenerable que se versiona | `knowledge/` |
| Resultado local, informe temporal o log | `output/` |
| Contrato JSON público | `schemas/` |
| Código de interfaz web | `frontend/` |
| Script de operación y units de systemd | `scripts/` |

## Organización de `docs/`

| Directorio | Alcance |
|---|---|
| `brand/` | Identidad y manifiesto |
| `development/` | Decisiones y guías para desarrollar |
| `examples/` | Entradas pequeñas de ejemplo |
| `experiments/` | Evidencia y evaluaciones reproducibles |
| `jurisprudence/` | Modelos, pipelines y contratos jurisprudenciales |
| `normativa/` | Diseño del corpus legal |
| `operations/` | Despliegue, DNS y plataforma |
| `product/` | Analítica, rutas y decisiones visibles para usuarios |
| `project/` | Backlog y coordinación |
| `superpowers/` | Planes y specs históricos; algunos nuevos pueden permanecer solo en local |

## Convenciones de rutas

- Los comandos de uso diario se ejecutan mediante `make`; el Makefile resuelve
  la ubicación de `src/`.
- Un CLI offline se ejecuta desde la raíz, por ejemplo:

  ```bash
  uv run python src/export_jurisprudence_case.py --help
  ```

- Para imports en una orden `python -c`, añade `src` al path:

  ```bash
  PYTHONPATH=src uv run python -c "from chat_model_policy import CHAT_MODEL; print(CHAT_MODEL)"
  ```

- Pytest y mypy reciben `src/` mediante `pyproject.toml`.
- Las rutas de documentación se escriben desde la raíz cuando aparecen como
  texto; los enlaces Markdown se expresan relativos al documento.

## Archivos que deben permanecer en la raíz

`README.md`, `LICENSE`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`,
`CLAUDE.md`, `.gitignore`, `.env.example`, `.python-version`, `pyproject.toml`,
`uv.lock`, `Makefile`, `package.json`, `netlify.toml` y la configuración de
automatización son puntos de entrada reconocibles por personas o herramientas.

Los secretos (`.env`), dependencias instaladas, caches y enlaces personales
pueden existir localmente en la raíz, pero están ignorados y no forman parte de
la estructura versionada.
