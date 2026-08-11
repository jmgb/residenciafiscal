# CLAUDE.md

Guía para Claude Code en el proyecto **Residencia Fiscal** — [residenciafiscal.org](https://residenciafiscal.org).

## Dominio canónico de producción

El dominio público y canónico de producción es **`https://residenciafiscal.org`**.
Toda ruta, enlace, comprobación HTTP, canonical, sitemap, JSON-LD y referencia
al sitio en producción debe usar ese origen. `www.residenciafiscal.org` solo
redirige al dominio canónico.

`residenciafiscal.netlify.app`, `main--residenciafiscal.netlify.app` y
`deploy-preview-*--residenciafiscal.netlify.app` son direcciones técnicas de
Netlify: no son URLs de producción y no deben presentarse ni enlazarse como
tales. Las dos primeras pueden usarse únicamente para diagnosticar el origen,
dejándolo explícito; las de `deploy-preview-*` son previews privados. Si
Cloudflare impide una comprobación automatizada del dominio canónico, se informa
del bloqueo y no se sustituyen las rutas reales de producción por el origen de
Netlify.

## Arquitectura SEO por jurisdicción

España es la primera instancia de una plantilla común, no un caso especial. La
arquitectura cerrada para cualquier jurisdicción es:

```text
/<pais>
├── /fuentes
├── /normativa
│   └── /<precepto>
├── /convenios
│   └── /<otro-pais>
├── /sentencias
│   └── /<sentencia>
└── /doctrina
    └── /<tema>
```

El slug sale siempre de `src/jurisdiction_catalog.json` mediante los
constructores compartidos; no se concatena `"/espana"` dentro de código
reutilizable. Norma, sentencia y doctrina pertenecen a su jurisdicción fuente
—fuente oficial u órgano judicial—, aunque mencionen otros países. La plantilla
define el futuro, pero no crea thin content: una sección o ficha sin corpus,
revisión o contenido diferencial suficiente no se materializa y devuelve 404.
Contrato y fases: [`docs/product/INTERNATIONAL_ARCHITECTURE.md`](docs/product/INTERNATIONAL_ARCHITECTURE.md).

## Quick Start

El proyecto usa **uv** (no pip/venv a mano) y un **Makefile** como interfaz única:
`make help` lista y describe todos los comandos.

> Cualquier comando suelto se lanza con `uv run` (p. ej. `uv run python src/export_jurisprudence_case.py --help`).
> Nunca hace falta activar el entorno: `uv run` lo resuelve solo.
>
> **Frontera obligatoria:** las sentencias se preparan offline mediante
> Python + agente. El gateway solo responde preguntas del chat. No añadas un
> analizador LLM de PDF ni un endpoint `/analizar`. El rollout autorizado de las
> 106 ya está procesado como borrador interno `AGENT_REVIEWED_ONLY`: no lo
> presentes como revisado por una persona ni lo conectes al chat sin una decisión
> posterior basada en sus evaluaciones.

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

### Llamadas a modelos: V1 Node y prototipo Python

La V1 de producción es la Netlify Function TypeScript autosuficiente. Sus
adaptadores Node llaman directamente a OpenAI Responses para A y a Gemini
Interactions + File Search para B. A se ejecuta una sola vez; B permite un
segundo y último intento con el mismo modelo únicamente cuando una respuesta
sustantiva no aporta ninguna cita verificable. No existe fallback de modelo ni
`gpt_request` en este runtime Node legado.

El prototipo Python conservado fuera del despliegue V1 sí usa la fachada
funcional `gpt_request` de `src/llm_gateway_facade.py`: mantiene el contrato de
entrada y traduce a **`neutral-llm-gateway`**, fijado a una referencia
inmutable. `src/chat_model_policy.py` declara `gpt-5.6-luna` + `high` por
defecto y `gemini-3.6-flash` como fallback cross-provider explícito; el gateway registra el
modelo efectivo, uso, alertas y coste. Los límites y tests de ambos composition
roots están en
[`docs/development/LLM_GATEWAY.md`](docs/development/LLM_GATEWAY.md).

En el prototipo Python no hay tabla de precios ni de enrutado local: las tarifas
y el proveedor salen del catálogo versionado del paquete. En la V1 Node, los
adaptadores mínimos y sus esquemas pertenecen al runtime del producto; no deben
crecer con routing ni fallback.

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
E0 añadió determinación residencial tipada, regeneró las cinco sin regresión,
congeló un holdout independiente y preparó estado reanudable y gates por lote.
La fase E autorizada se ejecutó el 1 de agosto de 2026: 106/106 builds pasan,
67 casos entran en recuperación, 39 quedan marcados fuera de ámbito y el corpus
agregado contiene 74 unidades. Todo el contenido nuevo sigue
`AGENT_REVIEWED_ONLY`; el holdout obtiene 75 % de conducta y no puede usarse
para ajustar el retriever. Solo etiqueta 5 de 106 fuentes, por lo que su
precisión sobre el corpus completo no es válida. El banco de desarrollo de
lookup, la auditoría de los 42 casos HIGH y la verificación reproducible están
separados del holdout. Contrato operativo, resultados y política de revisión:
[`docs/jurisprudence/JURISPRUDENCE_PHASE_E0.md`](docs/jurisprudence/JURISPRUDENCE_PHASE_E0.md).
El Markdown OKF/3 y las unidades de recuperación por cuestión se derivan de
cada caso canónico. Su contrato está en
[`docs/jurisprudence/JURISPRUDENCE_DERIVATIVES_B4.md`](docs/jurisprudence/JURISPRUDENCE_DERIVATIVES_B4.md).
El manifiesto real, los borradores, los 11 lotes y los informes de fase E ya
están materializados. El siguiente gate es jurídico y de producto: no registrar
aprobación humana inexistente ni conectar el corpus completo directamente al
chat, porque su holdout de recuperación no justifica esa promoción.
La retención de derivados y sus límites se rige por
[`docs/jurisprudence/JURISPRUDENCE_ARTIFACT_POLICY.md`](docs/jurisprudence/JURISPRUDENCE_ARTIFACT_POLICY.md).

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

### Catálogo de jurisdicciones y relaciones bilaterales

`src/jurisdiction_catalog.json` es la **única clave de cruce** entre el corpus
normativo, el jurisprudencial y la web: cada jurisdicción declara su `code` ISO,
su nombre y su `slug`. `src/treaty_relations_es.json` dice qué convenio rige
entre España y cada una de las 92 contrapartes, con el rango de ejercicios y la
cláusula que lo sostiene. Ambos tienen schema generado desde su modelo Pydantic.

El frontend **no** guarda copia: recibe proyecciones generadas y versionadas
(`make export-frontend-projections`), y `countryRoutes.json` ya no contiene
`name` ni `treatyBoeId`. `CONVENIOS_POR_PAIS` es también una proyección.

Checoslovaquia y la URSS entran con código **ISO 3166-3** porque sus convenios
siguen en el corpus y el Estado firmante ya no existe; no se declara sucesión.
Tres normas que el filtro del BOE traía como `cdi` no son convenio general de
renta y están reclasificadas en `descargar_normativa.py`.

`knowledge/jurisprudencia-v3/jurisdicciones/` guarda, por sentencia, qué papel
juega cada jurisdicción —`residence_claimed`, `treaty_applied`,
`evidence_location`, `mentioned_only`— derivado de campos tipados del caso y con
la procedencia anotada. **`judgment.countries` es texto libre y no debe usarse
para cruzar nada**: 78 apariciones son menciones sin papel jurídico, y la saga
de becarios del ICEX convertiría el país de destino de la beca en «sentencias
sobre ese país».

### Publicación de sentencias como páginas

`src/public_judgment_projection.py` proyecta cada caso v3 a lo que puede salir a
la web, campo a campo. Es una **allowlist**: añadir un campo al schema canónico
no lo publica, y el estado de publicación se **calcula** desde la revisión
jurídica de lo proyectado. Hoy los 67 candidatos son `internal_preview` y
`LOTES_PUBLICADOS` está vacío; declarar ahí un caso sin aprobación humana rompe
el build.

El renderer existe pero **no publica nada**: un build de producción no
materializa ninguna ficha y las rutas devuelven 404 real. El Deploy Preview las
construye con `SENTENCIAS_PREVIEW=1`, con `noindex` en el HTML y
`X-Robots-Tag` en la cabecera. Contrato y estado:
[`docs/product/INTERNATIONAL_ARCHITECTURE.md`](docs/product/INTERNATIONAL_ARCHITECTURE.md).

```bash
make export-frontend-projections  # catálogo y relaciones -> frontend
make export-jurisdiction-roles    # papel de cada jurisdicción por sentencia
make export-public-judgments      # proyección pública + manifiesto con hashes
make verify-public-judgments      # 897 extractos contra sus 67 PDF (~50 s)
```

### Corpus normativo

`normativa/es/` guarda el XML del BOE de las 106 normas que deciden la
residencia fiscal (LIRPF, LGT, reglamentos y los 98 CDI de España), versionado
igual que los PDF de `sentencias/` y con su propio `AVISO_LEGAL.md`. Dos
convenios en vigor —Venezuela y Paraguay— no salen del índice consolidado del
BOE y están declarados a mano en `CDI_NO_CONSOLIDADO`; se bajan del diario, pero
**no están derogados**, y el manifiesto separa por eso la `fuente` del grupo.
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

El artículo de residencia de cada CDI es además el contenido público de las
páginas de país: `/francia` publica el convenio España-Francia con su enlace
oficial al BOE. Por eso esas rutas ya no son `noindex` y entran en el sitemap;
el contrato está en [`docs/product/COUNTRY_PAGES.md`](docs/product/COUNTRY_PAGES.md).

Selección de preceptos, detección del artículo de residencia de cada CDI,
vigencia por ejercicio, normas derogadas, enlace con la jurisprudencia y el
contrato para añadir un país están en [`docs/normativa/NORMATIVA.md`](docs/normativa/NORMATIVA.md).

```bash
make descargar-normativa  # solo si el BOE actualiza algo (~3 min, con red)
make export-normativa     # regenera los 110 preceptos (sin red, sin LLM)
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
Netlify Function TypeScript: ejecuta las estrategias activas en paralelo, usa un
deadline global y persiste consultas, mensajes, estados y coste observado mediante RPC atómicas
en Supabase, y mantiene Luna `high`. El chat sostiene conversación: el servidor
reconstruye hasta seis turnos y 12 KiB desde el ledger —nunca desde el cuerpo de la
petición— y da a cada estrategia **solo su propio hilo**, para no contaminar la
comparación A/B. Una pregunta autosuficiente recupera exactamente igual que
antes; una referencia explícita como «ese caso» se contextualiza aunque contenga
términos jurídicos, y el resto usa contexto en recuperación solo cuando no se
sostiene solo; «el año anterior» no se trata como referencia conversacional.
Leer el hilo exige además un secreto local de 256 bits: Supabase
guarda únicamente su SHA-256 y el UUID visible de `/c/...` no autoriza nada. El
rollout admite bundles antiguos sin secreto solo en un hilo efímero y sin
contexto, ignorando su UUID. Al migrar historiales locales se invalidan los
`comparisonId` y jobs activos ligados al ledger anterior; los resultados
profundos ya terminados se conservan.
El coste nunca decide la admisión; el schema es privado y el navegador no accede
directamente. Contrato y operación:
[`docs/operations/SUPABASE_CHAT.md`](docs/operations/SUPABASE_CHAT.md). Producción
conserva el stub hasta completar configuración, privacidad y Deploy Preview;
decisión, despliegue y rollback:
[`docs/operations/CHAT_DEPLOYMENT.md`](docs/operations/CHAT_DEPLOYMENT.md).

## Privacidad y marco legal

`/privacidad` es la única página legal del sitio: declara el responsable
—Intangible Land LLC, titularidad estadounidense—, la base jurídica por
finalidad, los ocho encargados con su ubicación, las transferencias fuera del
EEE, los 15 días de conservación del chat, los derechos y las cookies. Cumple
además la identificación del art. 10 LSSI-CE, así que **no hay ni debe crearse
una página de aviso legal separada**.

Cada afirmación de esa página corresponde a algo verificable en el código; si
cambias el `store: false` de la estrategia A, el rate limit, la región de
Supabase, el plazo de retención o un proveedor, la página deja de ser cierta y
hay que actualizarla en el mismo cambio.

**No se designa representante en la UE (art. 27 RGPD) y no es un pendiente**: es
una decisión tomada el 1 de agosto de 2026. No publiques uno inexistente ni
afirmes en la página que no hace falta; el silencio actual es deliberado. Mapa
afirmación→código, riesgo asumido y lo que sigue abierto —consentimiento previo
de la analítica, contratos de encargo y validación jurídica del texto— en
[`docs/operations/PRIVACY_AND_LEGAL.md`](docs/operations/PRIVACY_AND_LEGAL.md).

## Operación: backups, tráfico y Netlify

Estas tres guías se cargan solo donde aplican, no en cada sesión:

- **Backups de Supabase en R2** (tres `systemd timer` del VPS `alfredo`, schema
  `private`, checkout que no se actualiza solo): [`scripts/backup/CLAUDE.md`](scripts/backup/CLAUDE.md)
  y [`docs/operations/BACKUPS.md`](docs/operations/BACKUPS.md).
- **Informe semanal de tráfico a Telegram** (una línea por analítica, GA4 y
  PostHog nunca se promedian): [`scripts/CLAUDE.md`](scripts/CLAUDE.md) y
  [`docs/operations/WEEKLY_TRAFFIC_REPORT.md`](docs/operations/WEEKLY_TRAFFIC_REPORT.md).
- **Configurar Netlify por CLI** (variables por contexto, redeploy desde git,
  **nunca `netlify deploy --prod` desde local**):
  [`docs/operations/NETLIFY.md`](docs/operations/NETLIFY.md).

## Errores en producción (Sentry)

Los **tres** runtimes mandan a Sentry, cada uno a su proyecto: la API FastAPI
(`src/api/sentry_config.py`), la SPA React (`frontend/src/lib/sentry-runtime.ts`)
y, desde el 1 de agosto de 2026, la Netlify Function del chat
(`frontend/netlify/functions/chat/observability.ts` → `residencia-fiscal-chat`).

Los tres fallan cerrado —sin `*_ENABLED` y sin DSN no arrancan— y borran
cabeceras, cookies y cuerpo antes de enviar el evento, con
`send_default_pii=False`. Es deliberado: una pregunta del chat es dato fiscal y
no puede acabar en un servicio de errores. `init_sentry()` además se desactiva
bajo pytest, porque la suite provoca excepciones a propósito.

**La Function no usa el SDK de Sentry, y es deliberado.** Construye el envelope a
mano con `fetch` porque `@sentry/node` captura breadcrumbs de consola y contexto
del runtime por defecto, y este runtime loguea eventos estructurados por consola;
desactivar cada captura automática es más frágil que escribir el payload. Lo que
sale hacia Sentry es exactamente lo que se lee en `buildEnvelope`: código de
fallo, etapa, `request_id` y nombre de clase del error, **nunca** la pregunta, la
respuesta ni el `message` de la excepción del proveedor, que puede traer el
prompt incrustado. `error.name` se sanea contra `[A-Za-z][A-Za-z0-9_]{0,39}` y
cualquier otra cosa se descarta como `unknown`. El coste **no** va a Sentry: no
es un error y su canal es el resumen diario sobre el ledger de Supabase.

Variables en `.env.example` y tabla en [`README.md`](README.md#errores-en-producción-sentry).
Dos trampas: todo `VITE_*` viaja **público** en el bundle (el DSN puede, un token
no), y `SENTRY_TOKEN`/`SENTRY_ORG_SLUG` son solo del build de sourcemaps y nunca
llevan ese prefijo. El token de Sentry filtrado en la historia de git el
2026-03-19 está revocado; la variable canónica vigente es `SENTRY_TOKEN`.

Los tres proyectos alimentan el autofix compartido con Presupuestor. El contrato
repo-local, los gates de publicación y los guardrails operativos están en
[`docs/operations/AUTOFIX.md`](docs/operations/AUTOFIX.md). Si se añade un cuarto
runtime de Sentry, hay que declararlo también en `.autofix.yml` y en el registro
del control plane; instrumentarlo por sí solo no lo hace resoluble.

## Costes del chat

Cada respuesta real del chat debe registrar por separado tokens, modelo
efectivo, coste marginal en USD, medición y latencia. **El coste no se muestra
en la interfaz**: es una cifra operativa, no información para quien consulta.
Vive en el ledger de Supabase y, para diagnóstico local, en la consola del
navegador (`[chat] respuesta`). La tarjeta de investigación profunda conserva su
propia línea de coste. Las antiguas cifras por PDF son históricas y no se usan
para presupuestar: ya no se analizan sentencias mediante el gateway.

## Gestión de dependencias (uv)

La fuente de verdad es `pyproject.toml`; `uv.lock` fija las versiones exactas y **se
versiona en git**. No hay `requirements.txt` en el repo (se genera bajo demanda con
`make export-requirements` si algún consumidor externo lo necesita).

## Calidad de código

ruff, mypy y pytest están configurados en `pyproject.toml`. La suite ordinaria
no realiza llamadas LLM. Los experimentos conversacionales de pago exigen
`CONFIRM_PAID=1` y no forman parte de pytest.

Gate antes de commitear: `make fast-check`.

En CI hay tres workflows (`ci.yml`, `frontend.yml`, `gitleaks.yml`), todos en push
y PR contra `main`.

**Ninguno usa secrets configurados, a propósito**: la suite Python por defecto no
llama a ningún LLM. La única credencial que aparece es el `secrets.GITHUB_TOKEN`
que GitHub inyecta solo en `gitleaks.yml` para comentar en el PR; no se declara
en la configuración del repositorio ni sale de él. Si algún día hace falta un job
con API real, va en un workflow aparte con `workflow_dispatch`, nunca en estos.
`uv sync --locked` además falla si `uv.lock` se queda desincronizado de
`pyproject.toml`.

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
    los corpus vive en [`NOTICE.md`](NOTICE.md), que es donde se amplía.
- **Nada de rutas absolutas** (`/home/ubuntu/...`) en código ni en documentación
  pública: usa rutas relativas a la raíz del repositorio. La única excepción son
  las units de systemd de `scripts/backup/`, `scripts/agentic/` y
  `scripts/privacy/`, donde `WorkingDirectory` y `ExecStart` **exigen** una ruta
  absoluta; ahí la ruta describe el checkout operativo del VPS, no el de nadie
  más. Los scripts y tests que comprueban esas units repiten la misma ruta y
  entran en la excepción por lo mismo. Los dos checkouts del VPS conviven a
  propósito: los timers de backup y retención cuelgan de `~/residenciafiscal` y
  los de `scripts/agentic/` de `~/ai_projects/residenciafiscal`.
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

## Frontend (residenciafiscal.org)

SPA React en `frontend/`, desplegada en Netlify: chatbot que consulta el corpus
de sentencias en lenguaje natural. Trampas del stack, marca, estado del motor de
chat y despliegue están en [`frontend/CLAUDE.md`](frontend/CLAUDE.md), que se
carga solo al trabajar dentro de ese directorio.

La disponibilidad la vigila **UptimeRobot** desde fuera: dos monitores de palabra
clave cada 5 minutos, uno sobre la home y otro sobre `data/corpus.json`. El
fallback actual devuelve 404, pero la palabra clave comprueba además que la home
y el corpus contienen el artefacto esperado. Monitores, credenciales y la trampa
de la API v2 (que rechaza toda escritura en este plan) están en
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
pública del circuito es `/colaborar`. Las páginas de país sin corpus también son
indexables desde que publican contenido bilateral propio y verificable; eso no
significa que tengan jurisprudencia nacional. El recuento no se escribe en
prosa: sale de `countryRoutes.json` y cambia al reservar una ruta. El formulario es
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

## Reglas transversales

- Puede haber varias sesiones de agentes trabajando a la vez en este repo: comprueba `git status` y que el HEAD es tuyo antes de stagear, commitear o reescribir historia.
- Aplica siempre KISS: la solución más pequeña y simple que resuelva el caso actual.
