# Arquitectura

Residencia Fiscal transforma documentos jurídicos oficiales en datos
estructurados y corpus consultables. El sistema separa las fuentes originales,
la lógica Python, los artefactos derivados y las interfaces de usuario.

Conviven un analizador legado capaz de recorrer 106 PDF y un corpus v3
verificable para el chat, validado únicamente sobre cinco. Son pipelines
relacionados, pero no equivalentes ni intercambiables.

## Vista general

```mermaid
flowchart LR
    PDF["sentencias/<br/>PDF del CENDOJ"] --> PIPELINE
    BOE["normativa/<br/>XML del BOE"] --> NORM
    PDF --> FILESEARCH["Gemini File Search<br/>store piloto de 5 PDF"]

    subgraph PYTHON["src/"]
        PIPELINE["Pipeline LLM<br/>residenciafiscal.py"]
        API["API FastAPI<br/>api/main.py"]
        CITES["Verificación literal<br/>citation_*"]
        CASES["Caso canónico y retrieval<br/>jurisprudence_*"]
        OKF["Publicación OKF<br/>okf_*"]
        VERBATIM["Corpus por páginas<br/>verbatim_*"]
        NORM["Transformación normativa<br/>normativa_*"]
        CHAT["Comparador F0.2<br/>chat_strategy_*"]
    end

    API --> PIPELINE
    PIPELINE --> RUNS["output/<br/>JSONL · CSV · XLSX"]
    RUNS --> CITES
    PDF --> CITES
    CITES --> OKF
    PDF --> VERBATIM
    VERBATIM --> CASES
    CASES --> CHAT
    FILESEARCH --> CHAT
    CHAT --> CHATOUT["output/file-search/<br/>respuestas y logs locales"]
    CASES --> KNOWLEDGE["knowledge/<br/>corpus versionados"]
    OKF --> KNOWLEDGE
    NORM --> KNOWLEDGE
    KNOWLEDGE --> WEB["frontend/<br/>React + Netlify"]
```

## Componentes

| Área | Ubicación | Responsabilidad |
|---|---|---|
| Pipeline principal | `src/residenciafiscal.py` | Extraer texto de PDF, llamar al proveedor LLM y escribir exports |
| Configuración de dominio | `src/config.py`, `src/prompt.py` | Modelos, catálogos, campos y prompt de extracción |
| Proveedores LLM | `src/ai_service_adapter.py`, `src/gateway_setup.py` | Traducir al paquete `llm_gateway` y conectar sus efectos por puertos |
| API HTTP | `src/api/` | Exponer el pipeline para un PDF sin persistir resultados |
| Citas | `src/citation_*.py`, `src/legal_text_matching.py` | Localizar y verificar extractos literales |
| Jurisprudencia v3 | `src/jurisprudence_*.py` | Compilar casos, validar referencias, recuperar y evaluar |
| OKF | `src/okf_*.py` | Normalizar, renderizar y validar perfiles publicables |
| Verbatim | `src/verbatim_*.py` | Representar el texto íntegro por páginas con hashes |
| Normativa | `src/normativa_*.py` y CLIs relacionados | Convertir XML oficial del BOE y enlazar preceptos |
| Chat experimental | `src/chat_*.py`, `src/current_structured_strategy.py`, `src/gemini_file_search_*.py` | Comparar A estructurada y B File Search con fuentes, coste y errores separados |
| Evaluación ciega | `src/chat_blind_review.py` | Sanear, equilibrar y materializar X/Y con hashes y clave separada |
| Contratos serializados | `schemas/` | JSON Schema versionados |
| Pruebas | `tests/` | Gates deterministas; las llamadas LLM reales están excluidas por defecto |

Los módulos Python conservan imports planos dentro de `src/`. Es una decisión de
compatibilidad: permite ordenar la raíz sin mezclar el cambio físico con una
migración pública de nombres. Una futura división en paquetes debe hacerse por
dominio y con una migración de imports independiente.

## Flujos principales

### Análisis LLM

1. `src/residenciafiscal.py` lee los PDF de `sentencias/`.
2. `pypdf` extrae la capa de texto; no hay OCR.
3. El adaptador selecciona el proveedor y aplica el prompt canónico.
4. El pipeline valida la respuesta y escribe los artefactos locales en
   `output/`.
5. `src/api/main.py` reutiliza el mismo proceso para una petición individual.

### Jurisprudencia verificable

1. La verificación contrasta cada cita con el texto extraído del PDF.
2. El corpus verbatim conserva páginas, hashes y procedencia.
3. Los módulos `jurisprudence_*` compilan el caso canónico y sus unidades de
   recuperación.
4. Los módulos `okf_*` producen perfiles Markdown e informes laterales.
5. Los derivados versionados se publican en `knowledge/`.

### Chat jurisprudencial F0.2

1. La pregunta entra en un comparador local, todavía no conectado al frontend.
2. A recupera unidades v3, limita el contexto y redacta mediante IDs de
   evidencia que se resuelven localmente.
3. B consulta de forma independiente un File Search Store con los cinco PDF
   originales y devuelve anotaciones del proveedor.
4. Ambas rutas verifican sus fuentes y retiran cualquier respuesta sustantiva
   que quede sin respaldo.
5. El comparador conserva respuesta, estado, fuentes, latencia y coste por
   estrategia, sin usar la salida de una como entrada de la otra.

Arquitectura, estado, aprendizajes y siguiente gate:
[`jurisprudence/CHAT_SYSTEM_ARCHITECTURE.md`](jurisprudence/CHAT_SYSTEM_ARCHITECTURE.md).

### Normativa

1. Los XML oficiales se guardan en `normativa/<jurisdicción>/`.
2. La selección de preceptos es explícita y jurídicamente delimitada.
3. La exportación copia el texto de la fuente, sin LLM ni reescritura.
4. Los preceptos y enlaces derivados se guardan en
   `knowledge/normativa/<jurisdicción>/`.

## Invariantes

- Una cita judicial o un precepto legal publicado debe proceder de una
  subcadena exacta de la fuente oficial.
- La normalización ayuda a localizar texto, nunca a reconstruirlo.
- Los corpus de jurisdicciones distintas permanecen aislados.
- Los artefactos de `output/` son locales y regenerables; no son fuente de
  verdad.
- Los schemas, modelos, validadores, tests y documentación contractual deben
  evolucionar juntos.
- Los tests ordinarios no realizan llamadas LLM ni requieren secrets.

## Límites actuales

- Los PDF escaneados sin capa de texto no se procesan porque no hay OCR.
- La API local no tiene rate limiting.
- El frontend conversacional sigue usando un motor simulado. F0.2 existe como
  comparador local, pero no implementa el backend ni el streaming productivos.
- El rollout 1 → 5 → 106 exige gates y revisión humana; no se amplía el corpus
  automáticamente.

Los contratos detallados están indexados en la
[documentación de jurisprudencia](README.md#jurisprudencia) y en la
[documentación normativa](normativa/NORMATIVA.md).
