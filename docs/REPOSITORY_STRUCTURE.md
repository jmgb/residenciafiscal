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
| `superpowers/` | Scratch local de planes y specs (en `.gitignore`, no se versiona); un diseño que fija decisiones vigentes se promociona a su área de `docs/` |

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

## Jurisdicciones: arquitectura lógica y ubicación física

La web usa una única arquitectura lógica para cualquier país:
`/<pais>/{fuentes,normativa,convenios,sentencias,doctrina}`. Código, nombre y
slug salen del catálogo compartido, y los constructores de frontend reciben el
código de jurisdicción; España es la primera instancia, no una rama especial.

La ubicación física todavía refleja el corpus disponible: `normativa/es/`,
`sentencias/` y `knowledge/jurisprudencia-v3/`. No se interpreta esa forma como
contrato de URL ni se deduce de ella la jurisdicción. Los manifiestos declaran
la clave explícitamente y las proyecciones públicas la conservan.

Al incorporar el primer corpus jurisprudencial no español, la fase E de
[`product/INTERNATIONAL_ARCHITECTURE.md`](product/INTERNATIONAL_ARCHITECTURE.md)
migrará las fuentes y derivados a un layout por jurisdicción antes de aceptar el
primer PDF. Esa migración física no altera la gramática pública, que ya queda
cerrada, y debe preservar hashes, manifiestos y reproducibilidad.

## Archivos que deben permanecer en la raíz

`README.md`, `LICENSE`, `NOTICE.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`,
`CLAUDE.md`, `.gitignore`, `.env.example`, `.python-version`, `pyproject.toml`,
`uv.lock`, `Makefile`, `package.json`, `netlify.toml` y la configuración de
automatización son puntos de entrada reconocibles por personas o herramientas.

Los secretos (`.env`), dependencias instaladas, caches y enlaces personales
pueden existir localmente en la raíz, pero están ignorados y no forman parte de
la estructura versionada.


## Ficheros públicos del repositorio

> Movido desde `CLAUDE.md` el 2026-11-10 (allí queda un resumen con enlace aquí).

## Ficheros públicos del repositorio

El repo **es público** desde el 1 de agosto de 2026. Al tocar estas piezas, ten
en cuenta:

- **`LICENSE` (MIT) cubre código y documentación, no los documentos jurídicos.**
  Hay dos corpus de fuente con condiciones propias, cada uno con su aviso legal
  y su inventario `readme.txt`: las sentencias del CENDOJ en `sentencias/` y los
  textos del BOE en `normativa/`. Si añades ficheros a cualquiera de los dos,
  actualiza su inventario y comprueba su `AVISO_LEGAL.md`. El del BOE recuerda
  además que la única versión con valor jurídico es la edición oficial.
  - **`LICENSE` contiene el texto MIT y nada más**, byte a byte igual a la
    plantilla canónica: cualquier nota añadida hace que GitHub clasifique el
    repositorio como `Other` y deje de mostrar la licencia. La salvedad sobre
    los corpus vive en [`NOTICE.md`](../NOTICE.md), que es donde se amplía.
- **Nada de rutas absolutas** (`/home/ubuntu/...`) en código ni en documentación
  pública: usa rutas relativas a la raíz del repositorio. La única excepción son
  las units de systemd de `scripts/backup/`, `scripts/agentic/` y
  `scripts/privacy/`, donde `WorkingDirectory` y `ExecStart` **exigen** una ruta
  absoluta; ahí la ruta describe un checkout operativo concreto, no el de nadie
  más. Los scripts y tests que comprueban esas units repiten la misma ruta y
  entran en la excepción por lo mismo. Las dos rutas que aparecen son **dos
  máquinas distintas, no dos checkouts del mismo host**: `~/residenciafiscal` es
  el único checkout del VPS `alfredo`, y de él cuelgan como units de *sistema*
  el backup, la retención del chat y el informe semanal de tráfico;
  `~/ai_projects/residenciafiscal` es el checkout de la máquina de informes,
  donde el resumen diario de coste del chat corre como unit de *usuario* para no
  llevar `SUPABASE_SECRET_KEY` al VPS.
- **Ningún workflow de CI usa secrets configurados**, y debe seguir así. Ver la
  sección de calidad de código.
- **Antes de tocar la visibilidad o de purgar historia**, el escaneo de
  referencia es `gitleaks git --log-opts="--all --remotes"` sobre todas las refs,
  no solo sobre `main`. Las excepciones se declaran en `.gitleaks.toml` con el
  valor exacto, nunca excluyendo un directorio.
- El correo personal no aparece en ningún fichero versionado: los canales de
  contacto de `SECURITY.md` y `CODE_OF_CONDUCT.md` son los avisos privados de
  GitHub. **Sí está en los metadatos de los commits anteriores al 2026-08-11**,
  que son igual de públicos; desde esa fecha se firma con la dirección
  `users.noreply.github.com` y no se reescribe la historia, porque cambiar los
  345 SHA rompería los enlaces a commits de la documentación sin despublicar
  nada de lo que ya está en forks y cachés.


## Planes y diseños de trabajo (superpowers)

> Movido desde `CLAUDE.md` el 2026-11-10 (allí queda un resumen con enlace aquí).

## Planes y diseños de trabajo (superpowers)

`docs/superpowers/` (`plans/` y `specs/`) está en `.gitignore` y es scratch
local: contiene rutas absolutas y referencias a otros proyectos privados, y no
se versiona ni se sanea retroactivamente. La regla de promoción:

- Un **diseño** que fija decisiones vigentes se gradúa al aprobarse: se mueve
  al área correspondiente de `docs/` (p. ej.
  `docs/product/INTERNATIONAL_ARCHITECTURE.md`), se enlaza desde
  `docs/README.md` y desde entonces se mantiene ahí, no en el scratch.
- **Un documento que haya que enlazar desde `TASKS.md` u otro fichero versionado
  se promociona siempre**, aunque todavía no esté aprobado: se mueve a `docs/`
  con su estado declarado en la cabecera («propuesta», «valoración»,
  «investigación»...) y se enlaza con ruta relativa normal. Nunca se enlaza
  desde un fichero versionado hacia `docs/superpowers/` —el enlace nacería roto
  para cualquiera que clone el repo— ni se quita ese directorio del
  `.gitignore`, que contiene material no saneado.
- Antes de promocionar, comprobar que no contiene rutas absolutas, referencias
  a repos privados ni credenciales: el repositorio es público.
- Los **planes de ejecución** (checklists paso a paso) no se promocionan nunca:
  su valor termina con la ejecución y el registro real es la historia de git.
