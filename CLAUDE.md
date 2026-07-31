# CLAUDE.md

Guía para Claude Code en el proyecto **Residencia Fiscal** — [residenciafiscal.org](https://residenciafiscal.org).

## Quick Start

El proyecto usa **uv** (no pip/venv a mano) y un **Makefile** como interfaz única.

```bash
# Instalar dependencias (crea .venv con Python 3.13 e instala desde uv.lock)
make setup

# Ver todos los comandos disponibles
make help

# Regenerar el piloto offline (sin llamadas LLM)
make export-verbatim
make export-case-v3

# Levantar API + frontend (API en http://127.0.0.1:8010/docs,
# frontend en http://127.0.0.1:5174)
make dev
```

> Cualquier comando suelto se lanza con `uv run` (p. ej. `uv run python src/export_jurisprudence_case.py --help`).
> Nunca hace falta activar el entorno: `uv run` lo resuelve solo.
>
> **Frontera obligatoria:** las sentencias se preparan offline mediante
> Python + agente. El gateway solo responde preguntas del chat. No añadas un
> analizador LLM de PDF ni un endpoint `/analizar`. El corpus v3 sigue limitado
> a la muestra congelada de cinco; no listar ni procesar las 106 como casos v3
> hasta superar sus gates y recibir autorización expresa.

La documentación se navega desde [`docs/README.md`](docs/README.md). La
arquitectura vigente y las reglas de ubicación de archivos están en
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) y
[`docs/REPOSITORY_STRUCTURE.md`](docs/REPOSITORY_STRUCTURE.md).

## Resumen del Proyecto

Corpus verificable construido desde **106 sentencias judiciales españolas**
sobre residencia fiscal (Art. 9 LIRPF). El workflow híbrido representa:

- **Criterios de residencia** aplicados (183 días, centro de intereses, familia, CDI)
- **Pruebas aportadas** por AEAT y contribuyente (aceptadas/rechazadas)
- **Razonamiento judicial** (doctrina, carga de prueba, motivación)
- **Resultado** (GANA_AEAT / GANA_CONTRIBUYENTE / PARCIAL y 4 más; catálogo
  canónico de 7 valores en `VALID_RESULTADO_FINAL`, `src/config.py`)

**Usuarios objetivo**: Investigadores fiscales, abogados tributaristas, compliance.

## Arquitectura

El corpus y el chat son dos contextos separados. Python extrae texto literal,
calcula hashes, valida propuestas del agente y compila el corpus v3. Solo el
chat recupera evidencia y llama al gateway para redactar una respuesta.
Arquitectura, capas de autoridad, comparador A/B y handoff:
[`docs/jurisprudence/CHAT_SYSTEM_ARCHITECTURE.md`](docs/jurisprudence/CHAT_SYSTEM_ARCHITECTURE.md).

### Llamadas a modelos: el paquete `llm_gateway`

Las respuestas del chat pasan por **`neutral-llm-gateway`**, fijado a una
referencia inmutable. `src/chat_model_policy.py` declara Luna + `high`, y
`src/gateway_setup.py` construye el gateway bajo demanda con las credenciales,
uso, alertas y coste. Preparar o validar el corpus nunca importa este gateway.

El comparador A usa `GatewayChatWriter(get_gateway())`; B conserva Gemini File
Search directo porque el paquete no ofrece tools ni ficheros. Los límites y
tests del composition root están en
[`docs/development/LLM_GATEWAY.md`](docs/development/LLM_GATEWAY.md).

**No hay tabla de precios ni de enrutado local**: las tarifas y el proveedor de
cada modelo salen del catálogo versionado del paquete, que es el mismo que
consulta su registro. Tampoco se reimplementan aquí el esquema estricto de
OpenAI ni la exclusión de `temperature` en modelos de razonamiento: desde la
`v0.7.0` los resuelve el paquete.

En el chat, un coste no calculable nunca se presenta como cero y la medición
distingue `ACTUAL`, `ESTIMATED` y `UNAVAILABLE`.

El paquete no tiene tools, ficheros ni streaming, y es deliberado; por eso el
chat B sigue usando Gemini File Search por su cuenta. Rige la **regla de los dos
consumidores**: nada entra en su API pública hasta que dos proyectos distintos
lo necesiten, y lo que solo necesita este repositorio se resuelve con un puerto.
Corte, trampas del contrato con OpenAI, evidencia de paridad y cómo subir de
versión: [`docs/development/LLM_GATEWAY.md`](docs/development/LLM_GATEWAY.md).

### Extracción de texto de los PDF (no hay OCR)

Los PDF del CENDOJ son digitales con capa de texto embebida. El corpus verbatim
se extrae con **pypdf** en `src/verbatim_extraction.py`: Python puro,
determinista y sin LLM. Conserva texto crudo por página, índices físicos y
hashes; el agente trabaja después sobre ese artefacto.

No hay OCR en el proyecto: un PDF escaneado (imagen, sin capa de texto) devuelve
texto vacío y no se procesa. Si algún día llega uno, las opciones son OCR
clásico (`ocrmypdf`/Tesseract) o un modelo de visión — no añadirlo antes de que
exista el caso real.

## Contrato del corpus

Los catálogos compartidos de criterios, categorías y resultados permanecen en
`src/config.py`; el modelo canónico del chat es
`residenciafiscal-case/3`, documentada en
[`docs/jurisprudence/JURISPRUDENCE_CASE_SCHEMA_V3.md`](docs/jurisprudence/JURISPRUDENCE_CASE_SCHEMA_V3.md).

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
[`docs/jurisprudence/CITATION_VERIFICATION.md`](docs/jurisprudence/CITATION_VERIFICATION.md).

```bash
make verify-citations  # hoy: SAN_1071_2025.pdf, 4 citas, umbral provisional 85
```

### Exportación jurisprudencial OKF

El ciclo JSONL → perfil jurídico → verificación de todas las citas anidadas →
sidecars → Markdown OKF está implementado para el piloto y para la muestra fija
de cinco definida en `sentencias/okf_muestra_5.json`. El enfoque es híbrido:
el agente propone cuestiones con anclajes literales y Python valida fuentes,
hashes, modelos, citas y renderizado. No editar `knowledge/jurisprudencia/` ni
`knowledge/jurisprudencia-muestra-5/` a mano: se regeneran con el pipeline. Las
revisiones viven en `knowledge/annotations/` y nunca pueden alterar el texto
legal. Arquitectura, contrato, resultado y gates:
[`docs/jurisprudence/OKF_PIPELINE.md`](docs/jurisprudence/OKF_PIPELINE.md).

El bundle OKF/2 legado usa `knowledge/jurisprudencia/`. El caso, perfiles e
índices v3 usan exclusivamente `knowledge/jurisprudencia-v3/`; no mezclar ambos
árboles, porque tienen contratos y manifiestos distintos.

El contrato campo por campo y el orden de secciones están en
[`docs/jurisprudence/OKF_MARKDOWN_CONTRACT.md`](docs/jurisprudence/OKF_MARKDOWN_CONTRACT.md). La
representación íntegra por páginas recomendada para un futuro RAG se especifica
en [`docs/jurisprudence/VERBATIM_CORPUS.md`](docs/jurisprudence/VERBATIM_CORPUS.md). Su contrato, extractor
crudo, JSON Schema y artefacto piloto de `SAN 1210/2023` ya están implementados
y validados. `src/pdf_page_extraction.py` produce texto saneado para matching y no
debe usarse como fuente verbatim; esa responsabilidad pertenece exclusivamente
a `src/verbatim_extraction.py`.

El caso de uso rector del corpus es la investigación jurisprudencial
conversacional: ante los hechos y preguntas de un abogado, recuperar por
cuestión jurídica los casos comparables, explicar hechos, pruebas, valoración y
resultado por cuestión, y respaldarlo con sentencia, página y extracto literal.
No es un predictor del caso del usuario. El contrato funcional y la auditoría de
adecuación del perfil v2 están en
[`docs/jurisprudence/CHAT_JURISPRUDENCE_USE_CASE.md`](docs/jurisprudence/CHAT_JURISPRUDENCE_USE_CASE.md).
El piloto manual de 40 preguntas sobre las cinco sentencias demuestra que no se
debe ampliar el schema actual a 106 sin modelar primero cuestiones, hechos,
relaciones prueba→hecho→cuestión y anclajes por proposición.
El orden operativo, el contrato preliminar, las responsabilidades
Python/agente/persona y los gates 1 → 5 → 106 están en
[`docs/jurisprudence/JURISPRUDENCE_DATA_V3_ROADMAP.md`](docs/jurisprudence/JURISPRUDENCE_DATA_V3_ROADMAP.md).
El caso v3 híbrido de `SAN 1210/2023` ya está compilado: 17 anclajes literales,
3 cuestiones y 18 preguntas aplicables validadas. Su pipeline, reparto de
responsabilidades y artefactos se documentan en
[`docs/jurisprudence/JURISPRUDENCE_CASE_PIPELINE.md`](docs/jurisprudence/JURISPRUDENCE_CASE_PIPELINE.md).
El mismo flujo ya regenera la muestra fija de cinco: 12 unidades, 62 anclajes
exactos, evaluación ejecutable de 40 preguntas y las 17 citas heredadas
clasificadas. Ese baseline de fase C sigue siendo `RETRIEVAL_ONLY`:
[`docs/jurisprudence/JURISPRUDENCE_SAMPLE_PHASE_C.md`](docs/jurisprudence/JURISPRUDENCE_SAMPLE_PHASE_C.md).
La fase D añade recuperación estructurada, diversificación, 20 paráfrasis y las
conductas `preguntar`/`abstenerse`; supera sus gates y aplaza embeddings para el
piloto. Método, métricas y límites:
[`docs/jurisprudence/JURISPRUDENCE_RETRIEVAL_PHASE_D.md`](docs/jurisprudence/JURISPRUDENCE_RETRIEVAL_PHASE_D.md).
E0 añade determinación residencial tipada, regenera las cinco sin regresión,
congela un holdout independiente y prepara estado reanudable y gates por lote.
El holdout obtiene 75 % de conducta y no puede usarse para ajustar fase D.
Contrato operativo, política de revisión y límite expreso de no listar/procesar
todavía las 106:
[`docs/jurisprudence/JURISPRUDENCE_PHASE_E0.md`](docs/jurisprudence/JURISPRUDENCE_PHASE_E0.md).
El Markdown OKF/3 y las unidades de recuperación por cuestión se derivan de
cada caso canónico. Su contrato está en
[`docs/jurisprudence/JURISPRUDENCE_DERIVATIVES_B4.md`](docs/jurisprudence/JURISPRUDENCE_DERIVATIVES_B4.md).
E0 deja preparado el rollout controlado de fase E. El siguiente trabajo
—crear el manifiesto real y ejecutar sus lotes— requiere autorización expresa;
no conectar directamente el chat ni transformar las 106 sin revisión humana.

El baseline histórico F0.2 redactó A sobre el corpus v3 y B con Gemini File
Search sobre los PDF usando el mismo modelo y fuentes independientes. La
política vigente ya no comparte modelo: A usa Luna + `high` y B un modelo Gemini
permitido por File Search. Por tanto, las siguientes ejecuciones comparan dos
stacks de producto y no aíslan por sí solas el efecto de la recuperación. Ocho
consultas reales del baseline detectaron una rúbrica heredada no neutral y
falta de cobertura estructurada sobre ausencias esporádicas; por eso no deben
ejecutarse todavía las 40 ni promoverse a 3.6. La arquitectura vigente, los
aprendizajes y el orden autorizado están en
[`docs/jurisprudence/CHAT_SYSTEM_ARCHITECTURE.md`](docs/jurisprudence/CHAT_SYSTEM_ARCHITECTURE.md);
las cifras están en
[`docs/experiments/CHAT_STRATEGY_F02_RESULTS.md`](docs/experiments/CHAT_STRATEGY_F02_RESULTS.md).
F0.3 ya congeló la rúbrica y generó el paquete X/Y; la siguiente intervención
es una revisión jurídica ciega por un abogado especialista, sin abrir la clave.
El revisor debe recibir solo el ZIP reproducible generado por
`make build-chat-f03-legal-bundle`. La propuesta sobre ausencias esporádicas ya
está validada, pero permanece aislada y no aplicada hasta revisión humana. El
compilador post-revelado también está preparado y exige
`CONFIRM_REVEAL=1`; no se ejecuta antes de cerrar el formulario. Protocolo,
rúbrica, paquete, plantilla y gap:
[`docs/experiments/CHAT_STRATEGY_F03_LEGAL_REVIEW_PROTOCOL.md`](docs/experiments/CHAT_STRATEGY_F03_LEGAL_REVIEW_PROTOCOL.md),
[`docs/experiments/CHAT_STRATEGY_F03_RUBRIC.md`](docs/experiments/CHAT_STRATEGY_F03_RUBRIC.md),
[`docs/experiments/CHAT_STRATEGY_F03_BLIND_REVIEW.md`](docs/experiments/CHAT_STRATEGY_F03_BLIND_REVIEW.md) y
[`docs/experiments/CHAT_STRATEGY_F03_REVIEW_FORM_TEMPLATE.md`](docs/experiments/CHAT_STRATEGY_F03_REVIEW_FORM_TEMPLATE.md);
[`docs/experiments/CHAT_DATA_GAP_ABSENCES.md`](docs/experiments/CHAT_DATA_GAP_ABSENCES.md).

```bash
make export-okf  # hoy: genera y valida exactamente 1 sentencia
make export-okf-sample OKF_SAMPLE_OUTPUT=knowledge/jurisprudencia-muestra-5-nueva
make export-case-v3  # compila y valida el caso canónico de SAN 1210/2023
make export-case-v3-derivatives  # deriva OKF/3 e índice por cuestión
make export-case-v3-sample  # regenera 5, evalúa 40 preguntas y ejecuta gates
make evaluate-retrieval-phase-d  # mide router, paráfrasis y recuperación @3
make evaluate-holdout-e0  # observación congelada; nunca ajusta el router
```

### Corpus normativo

`normativa/es/` guarda el XML del BOE de las 104 normas que deciden la
residencia fiscal (LIRPF, LGT, reglamentos y los 96 CDI de España), versionado
igual que los PDF de `sentencias/` y con su propio `AVISO_LEGAL.md`.
`knowledge/normativa/es/preceptos/` contiene un Markdown **por artículo**, no por
ley: se publica el precepto que decide o prueba la residencia, no las 270
secciones de la LIRPF.

No hay LLM en este pipeline y por eso tampoco hay verificación de citas: el
texto se copia de un XML ya estructurado por el BOE, y hay tests —verificados
por mutación— de que cada párrafo publicado es idéntico al de origen. Rige el
mismo invariante que en las sentencias: el articulado no se reescribe. **No
normalizar a NFKC**: convierte los ordinales `1.º` en `1.o` y eso es reescribir
la norma.

Cuatro preceptos son de normas **derogadas** (TR del IRPF de 2004 y los CDI con
Argentina de 1992 y Reino Unido de 1975). Están porque rigen ejercicios que el
corpus enjuicia, y se rotulan como tales para que nadie los lea como derecho
vigente.

`knowledge/normativa/es/enlaces/` resuelve las citas de las sentencias al
precepto, declarando la certeza y la redacción aplicable al ejercicio. El
directorio lleva el **código de jurisdicción** (ISO 3166-1 alfa-2) para que un
segundo país no exija migrar nada.

Selección de preceptos, detección del artículo de residencia de cada CDI,
vigencia por ejercicio, normas derogadas, enlace con la jurisprudencia y el
contrato para añadir un país están en [`docs/normativa/NORMATIVA.md`](docs/normativa/NORMATIVA.md).

```bash
make descargar-normativa  # solo si el BOE actualiza algo (~3 min, con red)
make export-normativa     # regenera los 108 preceptos (sin red, sin LLM)
make enlazar-normativa    # resuelve las citas de las sentencias a los preceptos
```

## Artefactos históricos

`output/analisis_*.jsonl` y los perfiles OKF/2 proceden del analizador retirado.
Pueden alimentar verificadores y migraciones reproducibles, pero no existe un
comando vigente que reprocese los PDF mediante una API LLM. Git conserva el
código anterior si alguna investigación histórica necesita consultarlo.

## Comandos Útiles

Todo pasa por el Makefile (`make help` los lista todos). Los no evidentes:

- `make fast-check` — el gate obligatorio antes de commitear (lint + tipos + tests).
- `make test` no llama a ningún LLM ni necesita secrets.
- `make build-chat-f03-review` — regenera el paquete ciego y su plantilla desde
  los ocho artefactos locales, sin LLM; valida todos sus hashes.
- `make build-chat-f03-legal-bundle` — genera el único ZIP que debe recibir el
  abogado, sin clave X/Y ni resultados previos.
- `make validate-chat-f03-review` — comprueba mecánicamente que el formulario
  jurídico cerrado no deja casillas, puntuaciones ni declaraciones pendientes.
- `make validate-chat-absences-candidate` — comprueba hashes, páginas y
  literalidad de la propuesta aislada `DAY-05`; no la aplica al corpus.
- `make compile-chat-f03-results CONFIRM_REVEAL=1
  CHAT_F03_REVIEW_COMMIT=<commit>` — revela X/Y únicamente después de cerrar y
  versionar la revisión jurídica.
- `make export-requirements` — solo para consumidores externos; el repo no versiona
  `requirements.txt`.

## API HTTP

`make dev` levanta FastAPI en `127.0.0.1:8010` y el frontend Vite en
`127.0.0.1:5174` (el puerto 8010 evita chocar con el backend de presupuestor).
Para levantar solo la API, usa `make dev-api`. Las rutas y esquemas están en `/docs`.

La API no expone `/analizar`. `GET /config` publica la política del chat y los
catálogos jurídicos. `POST /chat` implementa la comparación A/B por SSE, pero
falla cerrado salvo activación y autenticación explícitas. Es el prototipo local
y se conserva como posible arquitectura futura para peticiones de más de 60 s;
no es el target de la V1. El runtime conversacional ya está portado a una
Netlify Function TypeScript: ejecuta A y B en paralelo, usa un deadline global,
reserva presupuesto y persiste mensajes/costes mediante RPC atómicas en
Supabase, y mantiene Luna `high`. El schema es privado y el navegador no accede
directamente; contrato y operación:
[`docs/operations/SUPABASE_CHAT.md`](docs/operations/SUPABASE_CHAT.md). Producción
conserva el stub hasta completar configuración, privacidad y Deploy Preview;
decisión, despliegue y rollback:
[`docs/operations/CHAT_DEPLOYMENT.md`](docs/operations/CHAT_DEPLOYMENT.md).

## Backups de la base de datos

`scripts/backup/` respalda a diario el proyecto Supabase en el bucket R2
`residenciafiscal-backup` mediante tres `systemd timer` del VPS `alfredo`:
backup, check de frescura independiente y simulacro mensual no destructivo. Los
scripts **no** llevan credenciales y **nunca** hacen `source` del `.env` —lo
parsean con `lib-read-env.sh`—, y las units ejecutan `/bin/bash <script>` para no
depender del bit executable del checkout.

El dump cubre `private`, `public`, `auth` y `supabase_migrations`: **el dato del
chat vive en `private`**, así que un dump de `public` saldría verde y vacío. Al
crear un schema nuevo hay que añadirlo a `BACKUP_SCHEMAS` en `vps-backup.sh`; el
guardián de cobertura del propio script y `tests/test_backup_scripts.py` avisan si
alguien lo olvida. El checkout del VPS no se actualiza solo: tras tocar un script
o una unit, `git pull` allí y relanzar `install-backup-timer.sh`. Arquitectura,
operativa, límites y consecuencias de privacidad:
[`docs/operations/BACKUPS.md`](docs/operations/BACKUPS.md).

## Costes del chat

Cada respuesta real del chat debe mostrar y registrar por separado tokens,
modelo efectivo, coste marginal en USD, medición y latencia. Las antiguas cifras
por PDF son históricas y no se usan para presupuestar: ya no se analizan
sentencias mediante el gateway.

## Gestión de dependencias (uv)

La fuente de verdad es `pyproject.toml`; `uv.lock` fija las versiones exactas y **se
versiona en git**. No hay `requirements.txt` en el repo (se genera bajo demanda con
`make export-requirements` si algún consumidor externo lo necesita).

```bash
uv add paquete         # añadir una dependencia (actualiza pyproject + lock)
uv add --dev pytest    # dependencia solo de desarrollo
uv remove groq         # quitarla
make lock              # regenerar el lock tras editar pyproject a mano
make upgrade           # subir versiones dentro de los rangos declarados
```

Runtime: Python **3.13** (fijado en `.python-version`; `uv` lo instala solo).

## Calidad de código

ruff, mypy y pytest están configurados en `pyproject.toml`. La suite ordinaria
no realiza llamadas LLM. Los experimentos conversacionales de pago exigen
`CONFIRM_PAID=1` y no forman parte de pytest.

Gate antes de commitear: `make fast-check`.

En CI hay dos workflows, uno por área, ambos en push y PR contra `main`:

| Workflow | Cubre | Pasos |
|----------|-------|-------|
| `.github/workflows/ci.yml` | Python (todo salvo `docs/`, `sentencias/`, `*.md`) | ruff → mypy → pytest |
| `.github/workflows/frontend.yml` | `frontend/**` | biome → tsc → vitest → build |

**Ninguno usa secrets, a propósito**: la suite Python por defecto no llama a ningún
LLM. Si algún día hace falta un job con API real, va en un workflow aparte con
`workflow_dispatch`, nunca en estos. `uv sync --locked` además falla si `uv.lock` se
queda desincronizado de `pyproject.toml`.

`ci.yml` **no ignora `frontend/**`** aunque el frontend tenga su propio workflow: hay
tests de pytest que leen ficheros del frontend (`test_frontend_seo_assets.py` valida
`frontend/public/robots.txt`, `sitemap.xml` y `llms.txt`). Ignorarlo dejaría esos
tests sin gate, porque `frontend.yml` no corre pytest. Si añades un test Python que
lea otra ruta, comprueba que no esté en `paths-ignore`.

El gate de CI del frontend cubre lint, tipos, tests y build, en ese orden. El
gate local `npm run fast-check` ejecuta los tres primeros; usa además
`npm run build` cuando cambien build, prerender, Edge o configuración de Vite:

- **Corre `npm run build`**, y con él los hooks `prebuild`/`postbuild` de npm. No
  necesita `output/`, que no se versiona: sin JSONL del pipeline,
  `frontend/scripts/build-corpus.mjs` conserva el `frontend/public/data/corpus.json`
  versionado y avisa por stderr.
- **Vitest corre sin `--passWithNoTests`**: ya hay suites en `frontend/tests/`, así que
  borrarlas accidentalmente vuelve a poner el gate rojo.

La configuración de biome tiene sus propias trampas: ver
[`frontend/CLAUDE.md`](frontend/CLAUDE.md).

## Troubleshooting

| Problema | Solución |
|----------|----------|
| Falta una API key al probar el chat | Rellenar solo la credencial del proveedor usado en `.env` |
| `uv: command not found` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Entorno desincronizado | `uv sync` (o `make setup` para recrearlo) |
| `Address already in use` en `make dev` | `make dev PORT=9000` |
| PDF sin texto | El workflow verbatim solo admite PDF con capa de texto; no hay OCR |
| Una propuesta no compila | Corregir el sidecar del agente; nunca el verbatim ni el caso generado |

## Ficheros públicos del repositorio

El repo está preparado para ser público. Al tocar estas piezas, ten en cuenta:

- **`LICENSE` (MIT) cubre código y documentación, no los documentos jurídicos.**
  Hay dos corpus de fuente con condiciones propias, cada uno con su aviso legal
  y su inventario `readme.txt`: las sentencias del CENDOJ en `sentencias/` y los
  textos del BOE en `normativa/`. Si añades ficheros a cualquiera de los dos,
  actualiza su inventario y comprueba su `AVISO_LEGAL.md`. El del BOE recuerda
  además que la única versión con valor jurídico es la edición oficial.
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

La disponibilidad la vigila **UptimeRobot** desde fuera: dos monitores de palabra
clave cada 5 minutos, uno sobre la home y otro sobre `data/corpus.json` —el
fallback SPA de Netlify devuelve 200 para cualquier ruta, así que un monitor HTTP
simple no detectaría un corpus perdido. Monitores, credenciales y la trampa de la
API v2 (que rechaza toda escritura en este plan) están en
[`docs/operations/UPTIMEROBOT.md`](docs/operations/UPTIMEROBOT.md).

## Un país, un corpus

El proyecto es colaborativo. Solo España tiene corpus, y no por una limitación
del código —el pipeline es agnóstico de la jurisdicción—, sino porque abrir un
país exige criterio jurídico-tributario. La invitación se dirige por eso a
**expertos en fiscalidad y tributación internacional**, y pide tres cosas: una
fuente pública oficial con condiciones de reutilización claras, el precepto
nacional equivalente al art. 9 LIRPF y **un especialista que valide** el análisis
del modelo. El criterio para arrancar el siguiente país no es el orden de llegada:
es el primero que reúna fuente reutilizable y revisor comprometido.

Al escribir copy sobre esto, dos límites:

- **No se afirma que el corpus español esté revisado por expertos.** Las
  anotaciones de `knowledge/annotations/` están en `status: proposed` y la web
  advierte de que el análisis lo genera un modelo. Lo que sí se afirma es que su
  jurisprudencia **se delimitó** con criterio tributario, y la validación se
  enuncia como requisito para publicar, no como hecho consumado.
- **El registro es profesional.** «Lo puede abrir cualquiera» abarata el trabajo y
  describe mal el requisito; hay un test que impide que esa fórmula reaparezca.

Canales, perfiles y ruta viven en `frontend/src/lib/contribution.ts`; la página
pública es `/colaborar`, la única indexable del circuito porque las páginas de
país sin corpus son `noindex` (el recuento no se escribe en prosa: sale de
`countryRoutes.json` y cambia cada vez que se reserva una ruta). El formulario es
[`.github/ISSUE_TEMPLATE/aportar_pais.yml`](.github/ISSUE_TEMPLATE/aportar_pais.yml).
Contrato operativo en [`CONTRIBUTING.md`](CONTRIBUTING.md) y estado de las páginas
en [`docs/product/COUNTRY_PAGES.md`](docs/product/COUNTRY_PAGES.md).

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
