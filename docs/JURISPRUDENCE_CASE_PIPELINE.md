# Pipeline híbrido del caso jurisprudencial v3

## Finalidad

Este pipeline transforma el corpus verbatim de una sentencia en un caso
`residenciafiscal-case/3` preparado para recuperar por cuestión jurídica,
hechos, pruebas, valoración y resultado. El caso v3 es análisis derivado: el PDF
y el corpus verbatim siguen siendo la autoridad para el texto judicial.

El primer piloto es `SAN 1210/2023`. La misma ruta deberá usarse para 5 y 106
sentencias; no se crea un segundo pipeline para el lote.

## Artefactos y autoridad

| Artefacto | Función | Edición |
|---|---|---|
| `sentencias/<archivo>.pdf` | Fuente oficial conservada | Nunca |
| `knowledge/jurisprudencia/verbatim/<slug>.pages.json` | Texto íntegro por páginas | Generado por Python |
| `knowledge/jurisprudence-case-proposals/<slug>.proposal.json` | Aporte jurídico del agente | Revisable |
| `knowledge/annotations/<slug>.yaml` | Decisiones humanas separadas | Solo sidecar |
| `knowledge/jurisprudencia/cases/<slug>.case.json` | Caso v3 canónico compilado | Nunca a mano |
| `knowledge/jurisprudencia/evaluations/<slug>.questions.json` | Cobertura de preguntas del chat | Revisable |
| `knowledge/jurisprudencia/reports/<slug>.case-validation.json` | Resultado de gates | Generado por Python |

La propuesta omite deliberadamente todos los datos mecánicos que podrían
inventarse o quedar obsoletos: hash del PDF, hash de entradas, extractor,
número de páginas, etiqueta impresa y offsets. El compilador los deriva.

## Reparto de responsabilidades

El agente:

- identifica cuestiones jurídicas separadas;
- estructura hechos, pruebas, normas, carga y holdings;
- relaciona cada elemento con su cuestión;
- selecciona extractos copiados literalmente de una página concreta;
- declara límites y deja el estado en `AGENT_REVIEWED`.

Python:

- revalida el verbatim contra el PDF;
- exige que cada extracto aparezca exactamente una vez en la página declarada;
- calcula `start_offset`, `end_offset` y `printed_page`;
- calcula hashes del PDF, verbatim, análisis legado y sidecar;
- valida el JSON Schema y las relaciones internas y recíprocas;
- comprueba que las preguntas seleccionadas llegan a datos y anclajes existentes;
- publica el caso y el informe mediante reemplazo atómico.

Una persona:

- puede corregir el análisis derivado en la propuesta o el sidecar;
- aprueba jurídicamente con identidad `human:<identidad>` y fecha;
- nunca corrige el extracto judicial dentro de un anclaje.

## Ejecución

```bash
make export-verbatim
make export-case-v3
```

`make export-case-v3` no llama a un LLM. Compila una propuesta ya existente,
reproduce el texto desde el PDF y falla antes de publicar si una fuente, hash,
relación, cita o pregunta no valida.

Las variables permiten repetir el mismo comando para otra sentencia:

```text
CASE_PROPOSAL
CASE_VERBATIM
CASE_EVALUATION
CASE_OUTPUT
CASE_REPORT
```

## Gates ejecutables

1. El verbatim reproduce el PDF con el extractor y versión declarados.
2. Todas las entradas del análisis existen dentro del repositorio y conservan su
   SHA-256.
3. Cada anclaje pertenece al mismo PDF y página.
4. Cada fragmento es exactamente
   `raw_page_text[start_offset:end_offset]`.
5. Un extracto propuesto debe aparecer una sola vez en su página.
6. IDs y referencias existen y las relaciones
   cuestión↔hecho/prueba/norma son recíprocas.
7. Cada cuestión tiene su propio holding.
8. Las valoraciones judiciales y hechos probados tienen anclaje.
9. Las preguntas aplicables referencian cuestiones, datos y citas existentes.
10. Dos builds con las mismas entradas producen los mismos bytes.

## Resultado del piloto B3

| Métrica | Resultado |
|---|---:|
| Cuestiones jurídicas | 3 |
| Hechos | 8 |
| Hallazgos probatorios | 9 |
| Normas/doctrina | 5 |
| Holdings | 3 |
| Anclajes exactos | 17/17 |
| Preguntas aplicables validadas | 18 |
| Estado técnico | `VALIDATED` |
| Estado jurídico | `AGENT_REVIEWED` |

Las cuestiones son residencia fiscal, ganancias patrimoniales no justificadas
y sanción tributaria. No se crean eventos o periodos de presencia porque el
pasaje analizado no proporciona fechas o un cómputo diario con precisión
suficiente. Tampoco se crea análisis de CDI: la sentencia no aplica un convenio.
Estas colecciones vacías representan ausencia de datos, no un fallo de
extracción.

El hash del caso piloto es
`c8a4fd3e7702833d22789fa7427479ff9416b919708dee12f2bcbe17c8f245b6`.
El resultado reproducible vive en
`knowledge/jurisprudencia/reports/san-1210-2023.case-validation.json`.

## Siguiente fase

B4 debe derivar del caso v3 el perfil Markdown OKF y una unidad de recuperación
por cuestión. Ningún renderizador volverá a leer el análisis legado ni a
reformular citas: consumirá exclusivamente el caso v3 validado.
