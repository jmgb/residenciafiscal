# Guía de contribución

Gracias por el interés. Este documento explica cómo levantar el entorno, qué
comprueba el CI y qué se espera de una contribución.

## Aportar la jurisprudencia de otro país

Hoy solo España tiene corpus, y no por una limitación del código: el pipeline es
agnóstico de la jurisdicción, pero el criterio jurídico no lo es. La jurisprudencia
española se delimitó con criterio tributario —qué resoluciones importan, qué
criterios del art. 9 LIRPF se aplican, en qué doce categorías se clasifica la
prueba—, y abrir otro país exige lo mismo.

Cualquier jurisdicción puede entrar, no solo las que ya tienen ruta en la web.
**No hace falta saber programar**: la aportación que falta es jurídica, no
técnica, y por eso el proyecto se dirige a **profesionales de la fiscalidad y la
tributación internacional**.

Empieza abriendo una issue con la plantilla
[**Aportar la jurisprudencia de un país**](https://github.com/jmgb/residenciafiscal/issues/new?template=aportar_pais.yml).
Ahí se acuerda la fuente y sus condiciones antes de mover ningún documento. Si no
usas GitHub, escribe a **info@residenciafiscal.org**: es el mismo canal, no un
plan B. La versión pública de esta guía está en
[residenciafiscal.org/colaborar](https://residenciafiscal.org/colaborar).

### Quién puede colaborar

El cuello de botella no es técnico, es saber qué resolución importa y por qué. El
proyecto se nutre de la contribución de expertos:

| Perfil | Qué aporta |
|---|---|
| **Abogados y asesores fiscales** | Revisar que el análisis dice lo que dice la resolución, y señalar qué criterio pesa de verdad ante sus tribunales frente al que solo figura en la ley |
| **Académicos e investigadores** de fiscalidad internacional | Delimitar qué preceptos y convenios deciden la residencia en su jurisdicción, y en qué punto está la doctrina |
| **Documentalistas y bibliotecarios jurídicos** | Localizar y catalogar las resoluciones en el buscador oficial: la parte que más tiempo consume |
| **Traductores jurídicos** | Adaptar la terminología del análisis a la del país sin falsear el concepto. Hoy el schema está en español, y eso limita a las jurisdicciones no hispanohablantes |
| **Economistas y peritos** | Valorar la prueba económica —centro de intereses económicos, vínculos patrimoniales—, donde se decide buena parte de los litigios |
| **Desarrolladores y científicos de datos** | Pipeline, recuperación y frontend. Es lo único que ya existe, así que aquí se mejora, no se arranca |

La fuente de esta lista es `EXPERT_PROFILES` en
`frontend/src/lib/contribution.ts`, de donde la leen `/colaborar` y las páginas
de país. Si añades o quitas un perfil, cámbialo ahí y actualiza esta tabla:
`tests/test_contribucion_perfiles.py` compara las dos y falla si divergen.

### Qué se necesita

1. **Una fuente pública oficial de resoluciones**, con URL y con sus condiciones
   de reutilización. Sin licencia clara el corpus no se publica. Los documentos
   deben tener capa de texto: el pipeline extrae con `pypdf` y **no hace OCR**,
   así que un PDF escaneado hoy no se procesa.
2. **El precepto nacional que decide la residencia fiscal** de una persona
   física —el equivalente al art. 9 LIRPF— más el artículo de desempate de los
   convenios de doble imposición del país, con enlace a su texto oficial.
3. **Validación por un especialista.** El análisis lo redacta un modelo de
   lenguaje y puede equivocarse; ningún país se publica sin que un profesional
   del derecho tributario de esa jurisdicción compruebe que el análisis dice lo
   que dice la resolución. Es el requisito que hoy limita el proyecto a un solo
   país, y no se relaja.

### Reglas que no se negocian

Valen para cualquier corpus, no solo el español:

- **El texto de una resolución no se reescribe**: ni se corrige, ni se completa,
  ni se parafrasea. Puede formatearse, pero una cita solo se publica desde una
  subcadena exacta del texto extraído del documento oficial. Toda corrección o
  interpretación vive en metadatos o sidecars separados.
- **No se suben documentos al repositorio antes de resolver su reutilización.**
  Cada corpus de fuente lleva su propio `AVISO_LEGAL.md` y su inventario
  `readme.txt`, y hay que actualizarlos al añadir ficheros. Referencia: el
  criterio aplicado a [`sentencias/AVISO_LEGAL.md`](sentencias/AVISO_LEGAL.md) y
  a [`normativa/es/AVISO_LEGAL.md`](normativa/es/AVISO_LEGAL.md).
- **Los corpus están aislados entre sí.** Una consulta de un país no puede
  devolver una cita de otro, y un corpus nuevo tiene que traer sus tests de
  aislamiento.

### Qué pasa después de proponer un país

Se responde en la propia issue, y lo primero que se acuerda es la fuente y sus
condiciones de reutilización. El criterio para arrancar el siguiente país **no es
el orden de llegada**: es el primero que reúna una fuente reutilizable y un
revisor comprometido.

El proyecto lo mantiene una persona en su tiempo libre, así que no hay plazos
prometidos y una propuesta sin revisor puede quedarse abierta mucho tiempo.
Decirlo es más honesto que dar una fecha que no se va a cumplir.

### Cómo se publica una página de país

El circuito completo, con sus gates, está en
[`docs/product/COUNTRY_PAGES.md`](docs/product/COUNTRY_PAGES.md). En resumen: la ruta y la página
de invitación ya existen para 20 países; se sustituyen por la experiencia real
cuando el corpus está verificado, se pone `indexable: true` en
`frontend/src/data/countryRoutes.json` y el prerender y el sitemap se actualizan
solos en el build.

## Entorno

El proyecto usa [uv](https://docs.astral.sh/uv/) para Python y `npm` para el
frontend. El `Makefile` de la raíz es la interfaz única de la parte Python.
Consulta [`docs/REPOSITORY_STRUCTURE.md`](docs/REPOSITORY_STRUCTURE.md) antes de
añadir archivos nuevos.

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

**Los tests no llaman a ningún LLM y no cuestan dinero.** La preparación del
corpus tampoco envía PDF a proveedores.

| Comando | Coste |
|---------|-------|
| `make test` | 0 |
| `make export-verbatim` / `make export-case-v3` | 0 |
| `make compare-chat-strategies CONFIRM_PAID=1 ...` | Variable; dos respuestas del chat |

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

- Un cambio en el schema de extracción se refleja en `src/prompt.py`, en la tabla de
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
  (`make export-normativa` y `make enlazar-normativa`). El texto legal publicado
  tiene que ser idéntico al de su fuente y hay tests que lo comprueban. Cada
  jurisdicción vive en su propio subdirectorio (`normativa/es/`). Ver
  [`normativa/es/AVISO_LEGAL.md`](normativa/es/AVISO_LEGAL.md) y
  [`docs/normativa/NORMATIVA.md`](docs/normativa/NORMATIVA.md).
- No edites `frontend/public/favicon.ico`, `apple-touch-icon.png` ni
  `og-image.png` a mano: son artefactos generados (`npm run favicon` / `npm run og`).

## Reportar un fallo

Abre una issue con la plantilla correspondiente. Si el fallo implica una clave,
un dato personal o una vulnerabilidad, **no abras una issue pública**: sigue
[`SECURITY.md`](SECURITY.md).
