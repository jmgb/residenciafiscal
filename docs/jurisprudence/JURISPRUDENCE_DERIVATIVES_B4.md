# Derivados B4: perfil OKF e índice de recuperación

## Decisión

B4 genera dos vistas desde `residenciafiscal-case/3`:

1. un perfil Markdown legible `residenciafiscal-okf/3`;
2. un índice JSON `residenciafiscal-retrieval/1`, con una unidad por cuestión.

Ninguna vista lee el JSONL ni el análisis legado. Ambas se regeneran desde el
mismo caso canónico y se rechazan si el caso, el verbatim o el PDF dejan de
coincidir.

## Artefactos del piloto

```text
knowledge/jurisprudencia-v3/
├── cases/san-1210-2023.case.json
├── perfiles/san-1210-2023.md
├── retrieval/san-1210-2023.issues.json
└── reports/san-1210-2023.derivatives-validation.json
```

El JSON Schema del índice vive en
`schemas/residenciafiscal-retrieval-v1.schema.json`. El Markdown conserva OKF
v0.2 como formato externo y usa `schema_version: residenciafiscal-okf/3` para
su perfil jurídico.

Para regenerar el schema:

```bash
PYTHONPATH=src uv run python -c 'from pathlib import Path; from jurisprudence_case_retrieval_schema import write_retrieval_json_schema; write_retrieval_json_schema(Path("schemas/residenciafiscal-retrieval-v1.schema.json"))'
```

## Perfil `residenciafiscal-okf/3`

El frontmatter incluye:

- identidad, órgano, fecha, ejercicios y países;
- hash del PDF y del caso v3;
- rutas al PDF, caso y corpus verbatim;
- criterios detectados;
- resultado separado por cuestión;
- estado técnico y jurídico;
- generador y versión del perfil.

El cuerpo contiene, para cada cuestión:

1. tipo, criterios y revisión;
2. hechos relacionados;
3. pruebas de cada parte, valoración, función y motivo;
4. normas y doctrina;
5. secuencia de carga de la prueba;
6. cronología y CDI, o ausencia declarada;
7. holding y consecuencias;
8. todos los anclajes relacionados.

Los extractos se escriben en bloques `text` sin corregir caracteres ni saltos.
El marcador editorial `[…]`, cuando exista un anclaje con varios fragmentos,
se coloca fuera de los bloques literales.

El perfil permanece `draft` mientras el caso no sea `HUMAN_APPROVED`.
`VALIDATED` solo acredita conformidad técnica.

## Índice `residenciafiscal-retrieval/1`

La unidad primaria es `RetrievalUnit`, no la sentencia completa. Contiene:

| Campo | Uso |
|---|---|
| `unit_id` | Identidad sentencia + cuestión |
| `issue` | Pregunta, tipo, criterios y relaciones |
| `holding` | Resultado, conclusión y razonamiento decisivo |
| `facts` | Hechos de esa cuestión |
| `evidence_findings` | Pruebas y valoración de esa cuestión |
| `legal_rules` | Normas y doctrina relacionadas |
| `burden_of_proof_steps` | Secuencia procesal aplicable |
| `presence_events/periods` | Cronología disponible |
| `treaty_analyses` | Pasos de CDI relacionados |
| `source_anchors` | Extractos literales resolubles |
| `facets` | Filtros jurídicos y editoriales |
| `search_text` | Campo léxico derivado para el baseline |

`search_text` concatena únicamente datos de la misma cuestión. Sirve para
búsqueda léxica y no se presenta como cita ni como texto del tribunal. El chat
deberá inyectar solo las unidades recuperadas y los anclajes necesarios, no el
índice completo.

Facetas iniciales:

- tipo de cuestión y criterios;
- países y ejercicios;
- categorías y partes de la prueba;
- resultado por cuestión;
- presencia de análisis CDI;
- estado técnico y jurídico.

No hay embeddings en B4. La fase D comparará el baseline estructurado/léxico
contra embeddings usando el mismo banco de preguntas.

## Corpus agregado de la muestra

La fase C agrega los cinco índices sin cambiar sus unidades en
`residenciafiscal-retrieval-corpus/1`. Cada fuente conserva ruta y SHA-256 y el
contrato rechaza sentencias o `unit_id` duplicados. El JSON Schema versionado
vive en `schemas/residenciafiscal-retrieval-corpus-v1.schema.json`.

Los perfiles de la muestra se escriben en `perfiles/`. El árbol v3 completo es
hermano de `knowledge/jurisprudencia/`, que pertenece al bundle OKF/2 legado;
mezclarlos rompería sus contratos y manifiestos.

El ranker normaliza acentos, elimina palabras vacías, aplica un vocabulario
jurídico pequeño y ordena con BM25 normalizado por longitud. Una referencia
explícita `SAN/STS número/año` recibe prioridad determinista. El TF-IDF anterior
se conserva solo como comparación de desarrollo. El resultado de las 40
preguntas y sus límites se documenta en
[`JURISPRUDENCE_SAMPLE_PHASE_C.md`](JURISPRUDENCE_SAMPLE_PHASE_C.md).

## Gates

`make export-case-v3-derivatives`:

1. reproduce el verbatim desde el PDF;
2. valida hashes de todas las entradas del caso;
3. verifica los offsets y textos literales;
4. exige una unidad por cada cuestión y en el mismo orden;
5. exige que el índice cubra todos los anclajes del caso;
6. comprueba que el Markdown contiene cada fragmento sin alterarlo;
7. valida frontmatter, versiones y hashes;
8. publica Markdown, índice e informe mediante reemplazo atómico.

Dos ejecuciones con las mismas entradas producen los mismos bytes.

## Resultado

| Métrica | Piloto |
|---|---:|
| Perfiles OKF/3 | 1 |
| Cuestiones / unidades | 3 / 3 |
| Anclajes literales | 17/17 |
| Fragmentos literales | 17/17 |
| Estado técnico | `VALIDATED` |
| Estado jurídico | `AGENT_REVIEWED` |

La muestra de cinco ya se regeneró por este camino. No se autoriza todavía la
integración del chat; antes debe completarse la evaluación de recuperación de
la fase D.
