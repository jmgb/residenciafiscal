# Guía de contribución

Gracias por el interés. Este documento explica cómo levantar el entorno, qué
comprueba el CI y qué se espera de una contribución.

## Entorno

El proyecto usa [uv](https://docs.astral.sh/uv/) para Python y `npm` para el
frontend. El `Makefile` de la raíz es la interfaz única de la parte Python.

```bash
make setup                 # instala Python 3.13 + dependencias en .venv
cp .env.example .env       # y rellena OPENAI_API_KEY
make help                  # lista todos los comandos

cd frontend && npm install # solo si vas a tocar el frontend
```

No hace falta activar el entorno virtual: todo se lanza con `uv run` o vía
`make`.

## Antes de abrir un PR

Los dos gates tienen que estar en verde:

```bash
make fast-check                     # Python: ruff + ruff format + mypy + pytest
cd frontend && npm run fast-check   # frontend: biome + tsc + vitest
cd frontend && npm run build        # solo frontend: el gate de CI también compila
```

`make fast-check` cubre los mismos pasos que `.github/workflows/ci.yml`. En el
frontend, en cambio, **`npm run fast-check` no basta**: `frontend.yml` añade un
paso `npm run build`, que arrastra los hooks `prebuild`/`postbuild` de npm
(entre ellos la regeneración del corpus). Un cambio puede pasar `fast-check` en
local y romper CI en el build, así que si tocas `frontend/` compila antes de
abrir el PR.

## Coste de las pruebas

**Los tests por defecto no llaman a ningún LLM y no cuestan dinero.** Los que sí
gastan llevan el marker `manual_real_llm` y están excluidos vía `addopts` en
`pyproject.toml`.

| Comando | Coste |
|---------|-------|
| `make test` | 0 |
| `make test-single` / `make test-llm` | ~$0.01–0.04 (1 PDF) |
| `uv run python test/test_reasoning_effort_comparison.py` | 3 llamadas de pago sobre el mismo PDF (ver `TEST_CONFIGURATIONS`) |
| `make run` | ~$2.80 (106 PDFs) |

Nunca añadas a la suite por defecto un test que llame a un proveedor real, ni un
job de CI que consuma secrets. Si hace falta, va en un workflow aparte con
`workflow_dispatch`.

## Estilo

- **Python**: ruff con `line-length = 100`, reglas `E W F I B C4 UP`. Formatea
  con `make format` (o `make fix` para aplicar autofixes de lint).
- **Frontend**: Biome. `npm run format`.
- **Tipos**: mypy con `check_untyped_defs`. No hace falta anotar todo, pero lo
  que anotes debe pasar.
- **Idioma**: comentarios, docstrings y documentación en español; los
  identificadores de código, en el idioma que ya use el módulo que tocas.
- **Ficheros**: mantén los `.py` por debajo de ~2000 líneas.

## Commits y ramas

- Trabaja en una rama, no en `main`.
- Mensajes en formato [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `docs:`, `test:`, `chore:`, `ci:`), en imperativo y en
  español o inglés de forma coherente con el historial.
- Un PR, un cambio conceptual. Si tocas pipeline y frontend por motivos
  distintos, sepáralos.

## Qué documentar

- Un cambio en el schema de extracción se refleja en `prompt.py`, en la tabla de
  campos de `CLAUDE.md` y, si afecta al frontend, en `frontend/scripts/build-corpus.mjs`.
- Un cambio de comportamiento del CLI o de la API se refleja en `README.md` y en
  `CLAUDE.md`.
- Cualquier pieza visual o de copy debe respetar
  [`docs/brand/brand-guidelines.md`](docs/brand/brand-guidelines.md); el gate
  `frontend/tests/brand-tokens.test.ts` lo comprueba.

## Qué no hacer

- No subas `.env`, claves de API ni ficheros de `output/`.
- No añadas PDFs a `sentencias/` sin comprobar antes
  [`sentencias/AVISO_LEGAL.md`](sentencias/AVISO_LEGAL.md).
- No edites a mano ni `normativa/` ni `knowledge/normativa/`: la primera se baja
  del BOE (`make descargar-normativa`) y la segunda se regenera de la primera
  (`make export-normativa`). El texto legal publicado tiene que ser idéntico al
  de su fuente y hay un test que lo comprueba. Ver
  [`normativa/AVISO_LEGAL.md`](normativa/AVISO_LEGAL.md).
- No edites `frontend/public/favicon.ico`, `apple-touch-icon.png` ni
  `og-image.png` a mano: son artefactos generados (`npm run favicon` / `npm run og`).

## Reportar un fallo

Abre una issue con la plantilla correspondiente. Si el fallo implica una clave,
un dato personal o una vulnerabilidad, **no abras una issue pública**: sigue
[`SECURITY.md`](SECURITY.md).
