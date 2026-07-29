# Residencia Fiscal

Pipeline Python que analiza sentencias judiciales españolas sobre **residencia fiscal
(Art. 9 LIRPF)** con LLMs, y extrae criterios aplicados, pruebas aportadas por cada
parte, razonamiento judicial y resultado del fallo.

## Requisitos

- [uv](https://docs.astral.sh/uv/) (gestiona Python y dependencias)
- Una API key del proveedor que uses (`OPENAI_API_KEY` por defecto) en `.env`

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # si no tienes uv
```

## Puesta en marcha

```bash
make setup                  # instala Python 3.13 + dependencias en .venv
cp .env.example .env        # y rellena OPENAI_API_KEY
make help                   # lista todos los comandos
```

## Uso

```bash
# API HTTP (Swagger en http://127.0.0.1:8010/docs)
make dev

# Pipeline por lotes
make run-sample             # 1 PDF, prueba rápida
make run                    # los 106 PDFs de ./sentencias
make run-resume             # continúa sobre el JSONL más reciente de ./output

# Calidad
make fast-check             # lint + typecheck + tests
```

Variables útiles en los targets de pipeline: `INPUT=`, `OUTPUT=`, `MODEL=`,
`EFFORT=low|medium|high`, `MAX_FILES=`.

## API

| Método | Ruta        | Descripción                                     |
|--------|-------------|-------------------------------------------------|
| GET    | `/health`   | Estado y API keys detectadas                    |
| GET    | `/config`   | Modelos, criterios y categorías vigentes        |
| POST   | `/analizar` | Sube un PDF y devuelve el análisis estructurado |
| GET    | `/docs`     | Swagger UI                                      |

```bash
curl -X POST -F "archivo=@sentencias/SAN_1226_2021.pdf" \
  http://127.0.0.1:8010/analizar | jq .
```

La API reutiliza `process_pdf_async()` del pipeline, así que devuelve exactamente el
mismo objeto que una línea del JSONL. Si el nombre del fichero está en
`sentencias/sentencias_CLAVE.txt` se usa automáticamente el modelo premium.

`POST /analizar` gasta dinero en cada llamada. Si defines `RESIDENCIAFISCAL_API_TOKEN`
en `.env`, la ruta exige la cabecera `X-API-Token`; hazlo siempre que uses
`make dev-public` (escucha en `0.0.0.0`). Ver los detalles en `CLAUDE.md`.

## Salidas del pipeline

Cada ejecución de `make run` genera en `./output/` (con timestamp):
`analisis_*.jsonl`, `analisis_*.csv`, `sentencias_*.csv`, `pruebas_*.csv` y
`analisis_*.xlsx`.

## Documentación

- `CLAUDE.md` — guía completa: arquitectura, schema de campos, costes, troubleshooting
- `docs/` — notas sobre reasoning effort y tests
- `docs/tasks.md` — backlog de tareas pendientes del proyecto
