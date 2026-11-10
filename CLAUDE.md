> **Acceso SSH de los agentes desde este equipo (2026-11-02).** Para los agentes de trabajo que Jesús lance en su Ubuntu/WSL, con el usuario local `ubuntu`: `ssh alfredo-admin` y `ssh finanzas-admin` conectan como `prod-admin`, con `sudo -n` disponible.
>
> El acceso es permanente, sin passphrase ni caducidad de cuatro horas: SSH carga las claves locales automáticamente, también tras reiniciar. No pedir desbloqueos, ejecutar `ssh-add` ni buscar credenciales SSH en `.env`. Comprobación sin cambios: `ssh -o BatchMode=yes -o ConnectTimeout=10 alfredo-admin 'sudo -n true'` (o `finanzas-admin`).
>
> Esta nota prevalece sobre referencias SSH antiguas de esta guía para **esas sesiones locales**. En otros equipos, Javier y los demás colaboradores necesitan su propia cuenta/clave. No compartir privadas ni copiarlas a CI. Se conservan las restricciones de CI, runners y jobs autónomos; disponer de acceso no valida un comando de deploy ni autoriza publicaciones o reactivaciones. Seguir el procedimiento vigente del proyecto.

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


### Cómo encontrar la documentación

Este archivo solo trae lo que aplica a casi cualquier tarea; el detalle vive en su `.md`. Si el tema tiene línea-disparador aquí, sigue su enlace; si no, empieza por el índice [`docs/README.md`](docs/README.md) o busca antes de actuar: `grep -ril "<tema>" docs/ CONTRIBUTING.md frontend/CLAUDE.md scripts/CLAUDE.md`.

### Llamadas a modelos y extracción de texto

- **Al tocar llamadas a modelos del chat:** la V1 de producción es la Netlify Function TypeScript autosuficiente (adaptadores Node directos a OpenAI Responses para A y Gemini Interactions + File Search para B); **no hay fallback de modelo ni `gpt_request` en ese runtime**, y los adaptadores no deben crecer con routing ni fallback. El prototipo Python usa `gpt_request` (`src/llm_gateway_facade.py`) sobre `neutral-llm-gateway` sin tabla de precios ni enrutado local. Un coste no calculable **nunca** se presenta como cero. Regla de los dos consumidores, política de modelos, límites y tests: [`docs/development/LLM_GATEWAY.md`](docs/development/LLM_GATEWAY.md#llamadas-a-modelos-v1-node-y-prototipo-python).
- **Al extraer texto de PDF:** el corpus verbatim sale de `src/verbatim_extraction.py` (pypdf, determinista, sin LLM). **No hay OCR**: un PDF escaneado no se procesa y no se añade OCR antes de que exista el caso real. Detalle: [`docs/jurisprudence/VERBATIM_CORPUS.md`](docs/jurisprudence/VERBATIM_CORPUS.md#extracción-de-texto-de-los-pdf-no-hay-ocr).

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


- **Al verificar citas:** las `frases_clave` se contrastan con los PDF mediante un pipeline determinista sin LLM; el resultado separa localización de evidencia y fidelidad literal. Comando `make verify-citations`, rollout, gates y umbral: [`docs/jurisprudence/CITATION_VERIFICATION.md`](docs/jurisprudence/CITATION_VERIFICATION.md#pipeline-de-verificación-de-citas-y-rollout).
- **Al exportar OKF o tocar `knowledge/`:** el agente propone y Python valida; **no editar `knowledge/jurisprudencia/` ni `knowledge/jurisprudencia-muestra-5/` a mano** (se regeneran con el pipeline); las revisiones viven en `knowledge/annotations/` y nunca alteran el texto legal; **no mezclar** el bundle OKF/2 legado (`knowledge/jurisprudencia/`) con el caso v3 (`knowledge/jurisprudencia-v3/`). `src/pdf_page_extraction.py` no es fuente verbatim (solo `src/verbatim_extraction.py`). Contrato y comandos: [`docs/jurisprudence/OKF_PIPELINE.md`](docs/jurisprudence/OKF_PIPELINE.md#exportación-jurisprudencial-okf), [`docs/jurisprudence/OKF_MARKDOWN_CONTRACT.md`](docs/jurisprudence/OKF_MARKDOWN_CONTRACT.md) y [`docs/jurisprudence/VERBATIM_CORPUS.md`](docs/jurisprudence/VERBATIM_CORPUS.md).
- **Al trabajar el corpus v3, fases C/D/E0/F0.2/F0.3 o el chat A/B:** las sentencias están en borrador interno `AGENT_REVIEWED_ONLY` (ya dicho arriba); **no registrar aprobación humana inexistente ni conectar el corpus completo al chat** (su holdout no lo justifica; el holdout nunca ajusta el retriever); la revisión jurídica F0.3 es ciega y `make compile-chat-f03-results` exige `CONFIRM_REVEAL=1` solo tras cerrar y versionar esa revisión. Historial de fases, cifras y comandos `make export-*`/`evaluate-*`: [`docs/jurisprudence/JURISPRUDENCE_DATA_V3_ROADMAP.md`](docs/jurisprudence/JURISPRUDENCE_DATA_V3_ROADMAP.md#historial-de-fases-del-corpus-v3-y-comandos-de-exportación); rutas de lectura en [`docs/README.md`](docs/README.md#jurisprudencia).
- **Al tocar jurisdicciones, convenios o publicación de sentencias:** `src/jurisdiction_catalog.json` es la única clave de cruce; **`judgment.countries` es texto libre y no se usa para cruzar nada**; el frontend no guarda copia (proyecciones generadas con `make export-frontend-projections`); la publicación de sentencias es una **allowlist** y `LOTES_PUBLICADOS` solo se declara con aprobación humana. Detalle: [`docs/product/INTERNATIONAL_ARCHITECTURE.md`](docs/product/INTERNATIONAL_ARCHITECTURE.md#catálogo-de-jurisdicciones-relaciones-bilaterales-y-publicación-de-sentencias).
- **Al tocar `normativa/` o `knowledge/normativa/`:** el articulado no se reescribe y **no se normaliza a NFKC** (convierte `1.º` en `1.o`); no hay LLM en ese pipeline. Reglas, normas derogadas y comandos `make descargar-normativa`/`export-normativa`/`enlazar-normativa`: [`docs/normativa/NORMATIVA.md`](docs/normativa/NORMATIVA.md#corpus-normativo-reglas-y-comandos).

## Artefactos históricos

`output/analisis_*.jsonl` y los perfiles OKF/2 proceden del analizador retirado.
Pueden alimentar verificadores y migraciones reproducibles, pero no existe un
comando vigente que reprocese los PDF mediante una API LLM. Git conserva el
código anterior si alguna investigación histórica necesita consultarlo.

## Comandos Útiles

Todo pasa por el Makefile (`make help` los lista todos). Los no evidentes:

- `make fast-check` — el gate obligatorio antes de commitear (lint + tipos + tests).
- `make ci-local` / `make ci-changed` — si GitHub Actions no tiene minutos, reproducen en local los checks bloqueantes de `ci.yml`, `frontend.yml` (lint + typecheck) y gitleaks (`scripts/ci-local.sh`; test: `bash scripts/tests/test-ci-local.sh`).
- `make test` no llama a ningún LLM ni necesita secrets.
- Evaluación F0.3 (`make build-chat-f03-review`, `build-chat-f03-legal-bundle`, `validate-chat-f03-review`, `validate-chat-absences-candidate`, `compile-chat-f03-results`): [`docs/experiments/CHAT_STRATEGY_F03_LEGAL_REVIEW_PROTOCOL.md`](docs/experiments/CHAT_STRATEGY_F03_LEGAL_REVIEW_PROTOCOL.md#comandos-make-de-la-evaluación-f03-y-ausencias). Al abogado solo se le entrega el ZIP de `build-chat-f03-legal-bundle`, sin clave X/Y ni resultados previos.
- `make export-requirements` — solo para consumidores externos; el repo no versiona
  `requirements.txt`.


## API HTTP

`make dev` levanta FastAPI en `127.0.0.1:8010` y el frontend Vite en `127.0.0.1:5174`; solo la API: `make dev-api`. La API no expone `/analizar`; `POST /chat` falla cerrado salvo activación y autenticación explícitas y es un prototipo local, no el target de la V1 (la V1 es la Netlify Function). El servidor reconstruye el hilo desde el ledger, **nunca desde el cuerpo de la petición**, y cada estrategia ve **solo su propio hilo**; el coste nunca decide la admisión y el navegador no accede directamente a Supabase. Producción conserva el stub hasta completar configuración, privacidad y Deploy Preview. Contrato: [`docs/operations/SUPABASE_CHAT.md`](docs/operations/SUPABASE_CHAT.md#api-http-y-runtime-del-chat); despliegue y rollback: [`docs/operations/CHAT_DEPLOYMENT.md`](docs/operations/CHAT_DEPLOYMENT.md).

## Privacidad y marco legal

`/privacidad` es la única página legal: **no hay ni debe crearse una página de aviso legal separada**. Cada afirmación de esa página corresponde a algo verificable en el código; si cambias `store: false` de la estrategia A, el rate limit, la región de Supabase, el plazo de retención o un proveedor, **actualiza la página en el mismo cambio**. **No se designa representante en la UE (art. 27 RGPD) y no es un pendiente**: decisión deliberada del 1 de agosto de 2026; no publiques uno inexistente ni afirmes en la página que no hace falta. Detalle y abiertos: [`docs/operations/PRIVACY_AND_LEGAL.md`](docs/operations/PRIVACY_AND_LEGAL.md#privacidad-y-marco-legal-reglas-del-sitio).

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

## Errores en producción (Sentry) y costes del chat

- **Sentry:** los tres runtimes (API FastAPI, SPA React y la Netlify Function del chat) mandan a Sentry, fallan cerrado (sin `*_ENABLED` y sin DSN no arrancan) y borran cabeceras, cookies y cuerpo antes de enviar: una pregunta del chat es dato fiscal y **nunca** debe llegar a Sentry. **La Function no usa el SDK de Sentry, deliberadamente** (envelope a mano). Todo `VITE_*` viaja **público** en el bundle; `SENTRY_TOKEN`/`SENTRY_ORG_SLUG` son solo del build de sourcemaps y nunca llevan ese prefijo. Si se añade un cuarto runtime, declararlo también en `.autofix.yml` y en el registro del control plane. Detalle: [`docs/operations/CHAT_OBSERVABILITY.md`](docs/operations/CHAT_OBSERVABILITY.md#errores-en-producción-sentry-y-costes-del-chat); autofix: [`docs/operations/AUTOFIX.md`](docs/operations/AUTOFIX.md); variables: [`README.md`](README.md#errores-en-producción-sentry).
- **Costes del chat:** cada respuesta real registra por separado tokens, modelo efectivo, coste marginal en USD, medición y latencia; **el coste no se muestra en la interfaz** (vive en el ledger de Supabase y en la consola local). Las cifras antiguas por PDF son históricas y no sirven para presupuestar. Detalle en el mismo documento.

## Gestión de dependencias (uv)

La fuente de verdad es `pyproject.toml`; `uv.lock` fija las versiones exactas y **se
versiona en git**. No hay `requirements.txt` en el repo (se genera bajo demanda con
`make export-requirements` si algún consumidor externo lo necesita).

## Calidad de código

ruff, mypy y pytest están configurados en `pyproject.toml`. La suite ordinaria
no realiza llamadas LLM. Los experimentos conversacionales de pago exigen
`CONFIRM_PAID=1` y no forman parte de pytest.

Gate antes de commitear: `make fast-check`.


- **CI:** tres workflows (`ci.yml`, `frontend.yml`, `gitleaks.yml`) en push y PR contra `main`. **Ninguno usa secrets configurados, a propósito, y debe seguir así** (un job con API real va en un workflow aparte con `workflow_dispatch`). `ci.yml` **no ignora `frontend/**`** (hay tests de pytest que leen ficheros del frontend; no lo añadas a `paths-ignore`). El gate local del frontend es `npm run fast-check`, más `npm run build` cuando cambien build, prerender, Edge o Vite; Vitest corre sin `--passWithNoTests`. Detalle: [`CONTRIBUTING.md`](CONTRIBUTING.md#ci-workflows-secrets-y-gate-del-frontend). Trampas de biome: [`frontend/CLAUDE.md`](frontend/CLAUDE.md).

## Troubleshooting

| Problema | Solución |
|----------|----------|
| Falta una API key al probar el chat | Rellenar solo la credencial del proveedor usado en `.env` |
| `uv: command not found` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Entorno desincronizado | `uv sync` (o `make setup` para recrearlo) |
| `Address already in use` en `make dev` | `make dev PORT=9000` |
| PDF sin texto | El workflow verbatim solo admite PDF con capa de texto; no hay OCR |
| Una propuesta no compila | Corregir el sidecar del agente; nunca el verbatim ni el caso generado |

## Ficheros públicos del repositorio y planes

El repo **es público** desde el 1 de agosto de 2026. Reglas que se rompen sin querer: `LICENSE` contiene el texto MIT y nada más (la salvedad de los corpus vive en [`NOTICE.md`](NOTICE.md)); si añades ficheros a `sentencias/` o `normativa/`, actualiza su inventario `readme.txt` y comprueba su `AVISO_LEGAL.md`; **nada de rutas absolutas** (`/home/ubuntu/...`) en código ni documentación pública (excepción: units de systemd); ningún workflow usa secrets; el correo personal no aparece en ficheros versionados; antes de tocar la visibilidad o purgar historia, escanear con gitleaks todas las refs y declarar excepciones con valor exacto en `.gitleaks.toml`. Detalle completo: [`docs/REPOSITORY_STRUCTURE.md`](docs/REPOSITORY_STRUCTURE.md#ficheros-públicos-del-repositorio).

`docs/superpowers/` (`plans/` y `specs/`) es scratch local en `.gitignore`: **nunca** se enlaza desde un fichero versionado ni se quita del `.gitignore`; un documento que haya que enlazar se promociona antes a `docs/` (comprobando que no tiene rutas absolutas, repos privados ni credenciales), y los planes de ejecución no se promocionan. Regla completa: [`docs/REPOSITORY_STRUCTURE.md`](docs/REPOSITORY_STRUCTURE.md#planes-y-diseños-de-trabajo-superpowers).

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

Solo España tiene corpus, y abrir un país exige un especialista que valide. Al escribir copy: **no se afirma que el corpus español esté revisado por expertos** (las anotaciones están en `status: proposed`) y el registro es profesional (un test impide «lo puede abrir cualquiera»). El recuento de países sale de `countryRoutes.json`, no se escribe en prosa. Canales y ruta en `frontend/src/lib/contribution.ts` (`/colaborar`); contrato en [`CONTRIBUTING.md`](CONTRIBUTING.md) y [`docs/product/COUNTRY_PAGES.md`](docs/product/COUNTRY_PAGES.md#un-país-un-corpus-copy-y-circuito-de-colaboración).

## Referencias

- [Art. 9 LIRPF](https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764) - Residencia habitual
- [Modelo OCDE Art. 4](https://www.oecd.org/tax/treaties/) - CDI tie-breaker rules
- [CENDOJ](https://www.poderjudicial.es/search/) - Fuente de sentencias
- [OpenAI API](https://platform.openai.com/docs)

## 🔍 Cross-review con Codex (segundo par de ojos)

Revisión manual **opcional** con `/codex:review --wait`: no es un requisito de commit ni un gate automático. Sugiérela al usuario antes de pedir push cuando el cambio sea una feature nueva, un refactor multi-archivo, lógica crítica/seguridad/auth, infra/deploy o migraciones DB; no para typos, comentarios, logging, formateo o cambios de una línea. En features con commits incrementales, una sola review al cerrar con `--scope branch --base main`; si hay hallazgos serios, `/codex:rescue --resume "aplica los fixes propuestos"` antes del commit de cierre.

## Reglas transversales

- Al terminar y superar las pruebas pertinentes, haz commit local sin pedir permiso, solo de los archivos de la tarea. Push solo con autorización explícita.
- Puede haber varias sesiones de agentes trabajando a la vez en este repo: comprueba `git status` y que el HEAD es tuyo antes de stagear, commitear o reescribir historia.
- Aplica siempre KISS: la solución más pequeña y simple que resuelva el caso actual.
- **Tablas nuevas en `public` (Supabase):** la migración que cree una tabla usada por el backend incluye `GRANT SELECT, INSERT, UPDATE, DELETE ON public.<tabla> TO service_role;` (solo lo que use) y `GRANT USAGE ON SEQUENCE` si hay `serial`/`bigserial`; nunca `GRANT ... ON ALL TABLES` ni grants a `anon`/`authenticated` fuera de lo documentado. Hoy `public` no tiene tablas (los datos viven en `private`, vía RPC con `REVOKE ALL` + `GRANT EXECUTE`). Contexto y red de seguridad: [`docs/operations/SUPABASE_CHAT.md`](docs/operations/SUPABASE_CHAT.md#tablas-nuevas-en-public-grant-a-service_role).

## Secretos

Leer o ver un secreto en una sesión no obliga a rotarlo. Se rotan cada 90 días para minimizar riesgos, salvo que se expongan en un sitio público o a terceros o queden invalidados: entonces, en el momento.
