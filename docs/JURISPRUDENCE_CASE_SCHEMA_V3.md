# Contrato `residenciafiscal-case/3`

**Estado:** contrato implementado y validado con el caso piloto
`SAN 1210/2023`.
**Ámbito:** análisis jurídico estructurado de una sentencia.
**No incluye:** extracción del PDF ni almacenamiento verbatim por páginas.

## 1. Finalidad

Este contrato define la fuente canónica del análisis jurídico que utilizarán:

- el perfil Markdown OKF;
- el índice de recuperación del chat;
- la comparación de casos;
- las fuentes mostradas al usuario;
- la evaluación de las respuestas.

El caso de uso y el orden de implementación se encuentran en
[`CHAT_JURISPRUDENCE_USE_CASE.md`](CHAT_JURISPRUDENCE_USE_CASE.md) y
[`JURISPRUDENCE_DATA_V3_ROADMAP.md`](JURISPRUDENCE_DATA_V3_ROADMAP.md).

La unidad principal de recuperación es una **cuestión jurídica dentro de una
sentencia**, no la sentencia completa.

## 2. Autoridad y tipos de contenido

| Contenido | Autoridad | Puede mostrarse como texto judicial |
|---|---|:---:|
| PDF original | Fuente oficial de máxima autoridad | Sí, al abrir la fuente |
| Fragmento verbatim validado | Subcadena exacta del texto extraído | Sí, con sus límites |
| Descripción o conclusión estructurada | Análisis derivado | No |
| Revisión del agente | Propuesta o comprobación asistida | No |
| Aprobación humana | Decisión editorial sobre el dato | No convierte una paráfrasis en cita |

Ningún modelo puede corregir, completar o reconstruir el texto de un fragmento.
La normalización se utiliza para localizar candidatos, nunca para escribir la
cita publicada.

## 3. Serialización

- Formato: JSON UTF-8.
- Versión: `residenciafiscal-case/3`.
- Fechas: ISO 8601.
- IDs: minúsculas ASCII, números y guiones.
- Colecciones ordenadas: arrays JSON; el orden debe ser determinista.
- Campos desconocidos: prohibidos.
- Modelos: inmutables después de validar.
- Ausencia: `null` solo donde el contrato lo permita; no se usan cadenas
  ambiguas como `"NO CONSTA"` para representar valores nulos.

El JSON Schema generado vive en:

```text
schemas/residenciafiscal-case-v3.schema.json
```

Los modelos Pydantic son la fuente ejecutable del schema. El JSON Schema
versionado debe coincidir exactamente con su exportación determinista.

Para regenerarlo:

```bash
uv run python -c 'from pathlib import Path; from jurisprudence_case_schema import write_case_json_schema; write_case_json_schema(Path("schemas/residenciafiscal-case-v3.schema.json"))'
```

Los modelos están separados por responsabilidad en
`jurisprudence_case_{source,entities,evidence,timeline,analysis,reference_validation,validation}.py`;
`jurisprudence_case_models.py` contiene únicamente el agregado raíz.

La compilación, los artefactos y el reparto agente/Python/persona están
documentados en
[`JURISPRUDENCE_CASE_PIPELINE.md`](JURISPRUDENCE_CASE_PIPELINE.md).

## 4. Raíz `JurisprudenceCase`

| Campo | Tipo | Obligatorio | Semántica |
|---|---|:---:|---|
| `schema_version` | literal | Sí | Siempre `residenciafiscal-case/3` |
| `judgment` | `JudgmentIdentity` | Sí | Identidad y procedencia de la resolución |
| `legal_issues` | array | Sí | Cuestiones jurídicas recuperables |
| `facts` | array | Sí | Hechos alegados, controvertidos o probados |
| `evidence_findings` | array | Sí | Pruebas y valoración judicial |
| `legal_rules` | array | Sí | Normas y doctrina aplicadas |
| `holdings` | array | Sí | Resultado y ratio por cuestión |
| `burden_of_proof_steps` | array | Sí | Secuencia de carga de la prueba |
| `presence_events` | array | Sí | Eventos fechados de presencia, ausencia o viaje |
| `presence_periods` | array | Sí | Periodos y cómputos aplicables a los 183 días |
| `treaty_analyses` | array | Sí | Análisis de CDI, cuando exista |
| `source_anchors` | array | Sí | Fragmentos exactos que respaldan proposiciones |
| `review` | `ReviewStatus` | Sí | Estado global del caso |

Una colección puede estar vacía si la sentencia no trata esa materia, salvo
`legal_issues`, `holdings` y `source_anchors`, que deben contener al menos un
elemento en un caso publicable.

## 5. Estado de revisión

`ReviewStatus` separa dos dimensiones:

| Campo | Valores |
|---|---|
| `technical` | `GENERATED`, `VALIDATED`, `NEEDS_REVIEW`, `REJECTED` |
| `legal` | `UNREVIEWED`, `AGENT_REVIEWED`, `HUMAN_APPROVED`, `REJECTED` |
| `reviewed_by` | Identidad o `null` |
| `reviewed_at` | Fecha ISO o `null` |
| `notes` | Nota derivada opcional |

Reglas:

- `HUMAN_APPROVED` exige `reviewed_by` con prefijo `human:` y fecha.
- `AGENT_REVIEWED` no puede utilizar una identidad `human:`.
- `VALIDATED` significa conformidad técnica, no aprobación jurídica.
- Cada elemento relevante conserva su propio estado; el estado raíz no sustituye
  esa granularidad.

## 6. Identidad de la sentencia

`JudgmentIdentity` contiene:

| Campo | Tipo | Regla |
|---|---|---|
| `judgment_id` | ID | Estable y derivado de la resolución |
| `source_file` | string | Nombre exacto del PDF |
| `roj` | string | Identificador ROJ |
| `ecli` | string | Identificador ECLI |
| `court` | string | Órgano |
| `chamber` | string o `null` | Sala o sección |
| `decision_date` | date | Fecha de resolución |
| `tax_years` | array[int] | Sin duplicados, ordenado |
| `countries` | array[string] | Sin duplicados |
| `is_tax_residence_case` | boolean | Alcance material |
| `source_sha256` | SHA-256 | Hash binario del PDF |
| `page_count` | int | Páginas físicas, mayor que cero |
| `extractor` | `ExtractorIdentity` | Nombre y versión |
| `analysis_provenance` | `AnalysisProvenance` | Modelo, prompt y ejecución |
| `review` | `ReviewStatus` | Estado de esta identidad |

`AnalysisProvenance` no reconstruye datos históricos ausentes. Modelo, hash del
prompt o ID de ejecución pueden ser `null`, pero deben explicar esa ausencia en
`notes`. `input_artifacts` contiene exactamente una entrada `VERBATIM` y puede
añadir entradas `LEGACY_ANALYSIS`, `ANNOTATIONS` u `OTHER`, todas con ruta
relativa portable y SHA-256. De esta forma el análisis queda ligado a los bytes
concretos que lo produjeron.

## 7. Anclajes de fuente

`SourceAnchor` identifica uno o varios fragmentos exactos:

| Campo | Tipo | Regla |
|---|---|---|
| `anchor_id` | ID | Único dentro del caso |
| `source_sha256` | SHA-256 | Debe coincidir con el PDF del caso |
| `fragments` | array[`SourceFragment`] | Uno o más fragmentos |
| `fidelity` | enum | `EXACT` o `EXACT_WITH_ELLIPSIS` |
| `purpose` | enum | `FACT`, `EVIDENCE`, `HOLDING`, `REASONING`, `LEGAL_RULE`, `BURDEN_OF_PROOF`, `TREATY` |
| `review` | `ReviewStatus` | Estado del anclaje |

`SourceFragment` contiene:

- `page_index`: índice físico 1-indexado;
- `printed_page`: etiqueta impresa opcional;
- `start_offset`: inicio sobre `raw_page_text`;
- `end_offset`: final exclusivo;
- `verbatim_text`: subcadena exacta.

Invariantes:

- `end_offset > start_offset`;
- la página existe en `judgment.page_count`;
- `EXACT` contiene exactamente un fragmento;
- `EXACT_WITH_ELLIPSIS` contiene al menos dos;
- los fragmentos permanecen en orden de página y offset;
- la validación contra el texto por páginas exige que `verbatim_text` sea
  exactamente `raw_page_text[start_offset:end_offset]`.

## 8. Cuestiones jurídicas

`LegalIssue`:

| Campo | Tipo | Semántica |
|---|---|---|
| `issue_id` | ID | Identidad estable |
| `question` | string | Pregunta jurídica legible |
| `issue_type` | enum | Tipo canónico |
| `criterion_ids` | array[`CRIT_*`] | Criterios de residencia relacionados |
| `fact_ids` | array[ID] | Hechos relevantes |
| `evidence_ids` | array[ID] | Hallazgos probatorios |
| `legal_rule_ids` | array[ID] | Normas y doctrina |
| `holding_id` | ID | Resultado de esta cuestión |
| `anchor_ids` | array[ID] | Pasajes de contexto o razonamiento |
| `review` | `ReviewStatus` | Estado de la cuestión |

Tipos iniciales:

- `TAX_RESIDENCE`;
- `PHYSICAL_PRESENCE_183_DAYS`;
- `SPORADIC_ABSENCES`;
- `ECONOMIC_INTERESTS`;
- `VITAL_INTERESTS`;
- `FAMILY_PRESUMPTION`;
- `HOUSING_AND_EFFECTIVE_USE`;
- `FOREIGN_TAX_DOCUMENTATION`;
- `TREATY_TIEBREAKER`;
- `BURDEN_OF_PROOF`;
- `TAX_ASSESSMENT`;
- `UNEXPLAINED_CAPITAL_GAIN`;
- `PENALTY`;
- `OTHER`.

## 9. Hechos

`CaseFact`:

| Campo | Tipo | Semántica |
|---|---|---|
| `fact_id` | ID | Identidad estable |
| `subject_role` | enum | Contribuyente, familia, entidad u otro |
| `category` | enum | Presencia, vivienda, familia, actividad, etc. |
| `description` | string | Descripción derivada, nunca cita |
| `country` | string o `null` | País relacionado |
| `place` | string o `null` | Lugar relacionado |
| `start_date` | date o `null` | Inicio conocido |
| `end_date` | date o `null` | Fin conocido |
| `tax_years` | array[int] | Ejercicios relacionados |
| `asserted_by` | enum | Quién introduce el hecho |
| `procedural_status` | enum | Alegado, discutido, probado, no probado o pacífico |
| `issue_ids` | array[ID] | Cuestiones relacionadas |
| `anchor_ids` | array[ID] | Fuente dentro de la sentencia |
| `review` | `ReviewStatus` | Estado del hecho |

Categorías iniciales:

- `PRESENCE`;
- `TRAVEL`;
- `HOUSING`;
- `FAMILY`;
- `EMPLOYMENT`;
- `ECONOMIC_ACTIVITY`;
- `INCOME`;
- `ASSETS`;
- `BANKING`;
- `CONSUMPTION`;
- `HEALTH`;
- `ADMINISTRATIVE_LINK`;
- `FOREIGN_TAX`;
- `PROCEDURAL`;
- `OTHER`.

Un hecho probado atribuido al tribunal debe tener al menos un anclaje. El
periodo puede ser incompleto, pero `end_date` nunca puede preceder a
`start_date`.

### 9.1. Cronología de presencia

`PresenceEvent` representa un evento fechado y tipado:

- entrada, salida, presencia o ausencia observada, viaje, transacción,
  localización documental u otro evento;
- fecha y precisión exacta o aproximada;
- país, lugar y sujeto;
- quién lo afirma y su estado procesal;
- hechos, pruebas, cuestiones y anclajes relacionados;
- estado de revisión.

`PresencePeriod` representa un tramo utilizado en el cómputo:

- presencia, ausencia, ausencia esporádica o periodo desconocido;
- inicio, fin, país y número de días conocido;
- método de cálculo;
- si computa para la regla de 183 días;
- quién fija el cómputo;
- hechos, pruebas, cuestiones y anclajes relacionados;
- estado de revisión.

Un periodo admite fechas incompletas cuando la sentencia solo ofrece un número
de días, pero siempre exige fechas o `day_count`. Las fechas no se infieren ni
se completan por el agente.

## 10. Hallazgos probatorios

`EvidenceFinding`:

| Campo | Tipo | Semántica |
|---|---|---|
| `evidence_id` | ID | Identidad estable |
| `offered_by` | enum | AEAT, contribuyente, tribunal u otro |
| `category` | enum | Catálogo de doce categorías vigente |
| `subtype` | string | Nombre específico |
| `description` | string | Descripción derivada |
| `probative_purpose` | string | Qué pretende demostrar |
| `fact_ids` | array[ID] | Hechos apoyados o contradichos |
| `issue_ids` | array[ID] | Cuestiones a las que afecta |
| `assessment` | enum | `ACCEPTED`, `REJECTED`, `PARTIAL`, `UNRESOLVED`, `NOT_ASSESSED` |
| `assessment_reason` | string o `null` | Motivo judicial |
| `role` | enum | `DECISIVE`, `CORROBORATIVE`, `CONTRADICTORY`, `CONTEXTUAL`, `UNKNOWN` |
| `foreign_document` | objeto o `null` | Detalle tipado de documentación extranjera |
| `anchor_ids` | array[ID] | Pasajes que documentan prueba y valoración |
| `review` | `ReviewStatus` | Estado |

Una valoración distinta de `UNRESOLVED` o `NOT_ASSESSED` exige motivo y anclaje.
El campo histórico de peso `1–5` no forma parte del contrato v3.

Cada hallazgo debe ser atómico: si una misma pieza apoya un hecho y contradice
otro, se crean dos hallazgos relacionados con la misma fuente. Así `role` no
resulta ambiguo.

Para la categoría `DOCUMENTACION_FISCAL_EXTRANJERA`, `foreign_document` es
obligatorio y conserva:

- tipo documental;
- autoridad emisora y jurisdicción;
- periodo;
- naturaleza fiscal, administrativa, privada u otra;
- alcance: renta mundial, renta de fuente, solo residencia, no indicado o no
  aplicable;
- defectos señalados;
- efecto probatorio atribuido por el tribunal.

Estos campos son análisis estructurado. La denominación y valoración literales
siguen respaldadas por `anchor_ids`.

## 11. Normas y doctrina

`LegalRule` contiene:

- `legal_rule_id`;
- tipo: `STATUTE`, `TREATY`, `CASE_LAW`,
  `ADMINISTRATIVE_GUIDANCE` u `OTHER`;
- referencia normalizada;
- proposición derivada aplicada en el caso;
- cuestiones relacionadas;
- anclajes donde la sentencia la cita o aplica;
- estado de revisión.

No sustituye el texto oficial de la norma ni de otra resolución.

## 12. Holdings y resultados

`IssueHolding`:

| Campo | Tipo | Semántica |
|---|---|---|
| `holding_id` | ID | Identidad estable |
| `issue_id` | ID | Cuestión resuelta |
| `outcome` | enum | Resultado por cuestión |
| `conclusion` | string | Conclusión derivada |
| `decisive_reasoning` | string | Ratio o paso decisivo |
| `consequences` | array[string] | Efectos |
| `residence_determination` | objeto o `null` | Resultado residencial tipado, solo para `TAX_RESIDENCE` |
| `anchor_ids` | array[ID] | Pasajes literales de apoyo |
| `review` | `ReviewStatus` | Estado |

Resultados:

- `GANA_AEAT`;
- `GANA_CONTRIBUYENTE`;
- `PARCIAL`;
- `RETROACCION`;
- `INADMISION`;
- `NO_RESUELTO`;
- `OTROS`.

Cada cuestión referencia exactamente un holding y cada holding pertenece
exactamente a una cuestión. Un holding siempre tiene al menos un anclaje.

`outcome` expresa el vencedor procesal de la cuestión y no debe reutilizarse
para inferir el país de residencia. Cuando exista conclusión residencial,
`residence_determination` conserva:

- estado respecto de España: `RESIDENT_IN_SPAIN`,
  `NON_RESIDENT_IN_SPAIN`, `PARTIAL_YEAR_IN_SPAIN` o `NOT_DECIDED`;
- ejercicios afectados;
- país extranjero, cuando proceda;
- fecha `non_resident_from` obligatoria para un año parcial.

El campo es opcional para cargar artefactos v3 anteriores, pero el pipeline de
expansión exige completarlo en toda nueva cuestión `TAX_RESIDENCE`. No contiene
texto judicial y no modifica `conclusion` ni sus anclajes.

## 13. Carga de la prueba

`BurdenOfProofStep` representa la secuencia:

- `step_id`;
- `sequence`;
- cuestiones relacionadas;
- hecho que debe probarse;
- parte con la carga inicial;
- pruebas que activan o alteran la carga;
- parte a la que se desplaza, si sucede;
- respuesta exigida;
- conclusión del tribunal;
- anclajes;
- estado de revisión.

Las secuencias son únicas y contiguas desde uno dentro de cada caso.

## 14. Convenios de doble imposición

`TreatyAnalysis` separa ley interna y CDI:

- `treaty_analysis_id`;
- países;
- referencia del convenio;
- cuestiones de ley interna relacionadas;
- si se estableció doble residencia;
- `steps`;
- `decisive_step_id`;
- país resultante;
- anclajes generales;
- estado de revisión.

Cada `TreatyTieBreakerStep` conserva:

- ID y secuencia;
- criterio del catálogo de desempate;
- si se aplicó;
- conclusión;
- hechos y pruebas utilizados;
- anclajes;
- estado de revisión.

El paso decisivo, cuando existe, debe pertenecer al mismo análisis. Las
secuencias son únicas y contiguas.

## 15. Invariantes relacionales

El modelo raíz rechaza:

1. IDs duplicados dentro de una colección.
2. Referencias a hechos, pruebas, cuestiones, reglas, holdings o anclajes
   inexistentes.
3. Un holding conectado a una cuestión diferente de la que lo referencia.
4. Holdings huérfanos o reutilizados por varias cuestiones.
5. Anclajes cuyo hash no coincide con el PDF.
6. Fragmentos fuera del rango de páginas.
7. Secuencias de carga o CDI duplicadas o no contiguas.
8. Criterios o categorías fuera de catálogo.
9. Datos jurídicamente aprobados sin identidad humana y fecha.
10. Campos no declarados en el contrato.
11. Referencias huérfanas desde eventos o periodos de presencia.
12. Documentación fiscal extranjera sin su detalle tipado.

La validación literal contra `raw_page_text` está implementada en
`jurisprudence_case_verbatim_validation.py` y bloquea los derivados B4.

## 16. Correspondencia con v2

| v2 | v3 |
|---|---|
| Frontmatter y metadatos | `judgment` |
| Sección de hechos narrativa | `facts[]` |
| Pruebas AEAT/contribuyente | `evidence_findings[]` |
| `carga_prueba` global | `burden_of_proof_steps[]` |
| `doctrina_citada` | `legal_rules[]` |
| `resultado_final` | Derivado de `holdings[]`, no fuente de recuperación |
| Sidecar `issues` | `legal_issues[]` + `holdings[]` |
| Citas verificadas | `source_anchors[]` |
| `status` / `human_reviewed` | `review` granular |
| Peso `1–5` | Eliminado |

No se migrará automáticamente un resumen v2 a un hecho probado ni una cuestión
propuesta a una cuestión aprobada.

## 17. Versionado

Cambios incompatibles exigen una versión nueva:

- eliminar o renombrar campos;
- cambiar la semántica de un enum;
- hacer obligatorio un campo antes opcional;
- relajar la literalidad de anclajes;
- cambiar las invariantes relacionales.

Añadir un valor tipado o un campo opcional compatible requiere actualizar
modelos, JSON Schema, fixtures, tests y esta documentación en el mismo commit.

## 18. Cobertura del piloto de 40 preguntas

El gate de diseño comprueba que ninguna familia de preguntas dependa únicamente
de un resumen narrativo:

| Área del piloto | Datos v3 principales |
|---|---|
| Criterios generales | `legal_issues`, `facts`, `evidence_findings`, `holdings` |
| Permanencia y 183 días | `presence_events`, `presence_periods`, hechos, pruebas y reglas |
| Centro económico | hechos de ingresos, activos, banca y actividad; pruebas y holdings |
| Familia | hechos por sujeto y país, estado procesal, pruebas y holdings |
| Vivienda y vida cotidiana | hechos de vivienda/consumo, pruebas tipadas y valoración |
| Documentación extranjera | `foreign_document`, valoración, efecto y anclajes |
| CDI | `treaty_analyses.steps`, hechos, pruebas, resultado y paso decisivo |
| Prueba y carga | `evidence_findings` y `burden_of_proof_steps` |
| Sanciones | cuestión y holding propios, reglas, consecuencias y anclajes |
| Comparación y fuentes | hechos normalizados, cuestiones, resultados y `source_anchors` |

Las conductas `preguntar`, `respuesta parcial` y `abstenerse` pertenecen al
protocolo del chat y al banco de evaluación, no a una sentencia. V3 aporta los
datos para detectar qué hechos del usuario faltan y qué límites tiene el
corpus. La siguiente fase debe confirmar la suficiencia al poblar
`SAN 1210/2023`; el contrato todavía puede corregirse antes de regenerar cinco
sentencias.
