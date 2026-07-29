# Roadmap del corpus jurisprudencial v3

**Estado:** decisión de arquitectura documentada; implementación pendiente.
**Siguiente unidad de trabajo:** una sentencia, `SAN 1210/2023`.
**Rollout obligatorio:** 1 → 5 → 106.

## 1. Contexto

El objetivo del proyecto no es resumir sentencias de forma aislada. El caso de
uso principal es que un abogado describa un supuesto de residencia fiscal y
pueda investigar:

- qué cuestiones jurídicas aparecen en casos comparables;
- qué hechos y pruebas aportó cada parte;
- qué aceptó, rechazó o consideró decisivo el tribunal;
- qué resultado tuvo cada cuestión;
- qué casos apuntan en una dirección y cuáles sirven de contraste;
- en qué página y pasaje exacto puede comprobarse cada afirmación.

El contrato funcional completo está en
[`CHAT_JURISPRUDENCE_USE_CASE.md`](CHAT_JURISPRUDENCE_USE_CASE.md). El
[`piloto manual de 40 preguntas`](experiments/CHAT_QUESTION_PILOT_5.md) demuestra
que el perfil `residenciafiscal-okf/2` es útil para lectura y trazabilidad, pero
no basta como modelo canónico de recuperación.

Estado medido de la muestra:

| Elemento | Estado |
|---|---:|
| Sentencias preparadas | 5 |
| Citas candidatas | 98 |
| Citas literales publicables | 81 |
| Citas pendientes | 17 |
| Cuestiones propuestas | 12 |
| Cuestiones aprobadas por una persona | 0 |
| Preguntas del piloto manual | 40 |

Por ello no se autoriza todavía transformar las 106 con el schema v2 ni
construir el chat sobre el JSONL histórico.

## 2. Decisión ejecutiva

La siguiente fase crea un modelo de dominio canónico,
`residenciafiscal-case/3`, orientado a recuperar **cuestiones jurídicas dentro
de sentencias**.

Las decisiones asociadas son:

1. El PDF permanece como fuente de máxima autoridad e inmutable.
2. El texto íntegro extraído se persiste por páginas en JSON canónico.
3. El schema v3 representa cuestiones, hechos, pruebas, razonamiento, resultados
   y anclajes de fuente.
4. El Markdown OKF pasa a ser una vista regenerable del modelo v3.
5. Python conserva autoridad sobre extracción, hashes, IDs, validación y
   renderizado.
6. El agente propone y revisa la estructura jurídica, sin modificar el texto de
   la sentencia.
7. Una persona es la única que puede otorgar aprobación jurídica humana.
8. La recuperación se valida primero con búsqueda estructurada y léxica.
9. Los embeddings se añaden solo si mejoran de forma medida el banco de
   evaluación.
10. El chat recibe únicamente las unidades relevantes; nunca las 106 sentencias
    completas en cada llamada.

## 3. Objetivos y no objetivos

### Objetivos

- Recuperar por cuestión, patrón de hechos y tipo de prueba.
- Explicar la aplicación concreta en cada caso.
- Relacionar prueba → hecho → cuestión → conclusión.
- Separar alegaciones, análisis derivado y razonamiento judicial.
- Ofrecer casos principales, apoyos y contracasos.
- Resolver cada cita a PDF, página y fragmento exacto.
- Regenerar todos los derivados sin llamadas LLM.
- Detectar automáticamente cuándo faltan datos o cobertura.

### No objetivos de esta fase

- Predecir dónde reside fiscalmente el usuario.
- Generar una estrategia procesal o asesoramiento personalizado.
- Implementar ya el backend productivo del chat.
- Elegir una base vectorial antes de medir la recuperación.
- Procesar las 106 sentencias antes de congelar v3.
- Corregir ortografía, ligaduras o maquetación del texto extraído.
- Presentar resúmenes del agente como citas judiciales.

## 4. Arquitectura de datos

```text
PDF CENDOJ inmutable
  │
  ├── manifest + source_sha256
  │
  └── residenciafiscal-verbatim/1
        ├── páginas crudas + hashes
        └── chunks derivados + offsets
                 │
                 ▼
       residenciafiscal-case/3
        ├── judgment
        ├── legal_issues[]
        ├── facts[]
        ├── evidence_findings[]
        ├── holdings[]
        ├── burden_of_proof_steps[]
        ├── treaty_analysis[]
        ├── source_anchors[]
        └── review_status
                 │
         ┌───────┴────────┐
         ▼                ▼
  Markdown OKF       índice del chat
  para lectura       por cuestiones
```

### Fuentes de verdad

| Capa | Fuente canónica | Derivados |
|---|---|---|
| Documento oficial | PDF y su SHA-256 | Inventario |
| Texto extraído | JSON por páginas | Markdown verbatim, chunks |
| Análisis jurídico | JSON `residenciafiscal-case/3` + sidecars | Perfil OKF, índices |
| Recuperación | Índice reconstruible desde v3 | Tarjetas de contexto |
| Respuesta | No es fuente canónica | Conversación y fuentes mostradas |

El Markdown nunca es la única ubicación de un dato necesario para el chat.

## 5. Contrato preliminar de `residenciafiscal-case/3`

El contrato definitivo se escribirá campo por campo y tendrá modelos Pydantic,
JSON Schema y ejemplos versionados. Como mínimo debe cubrir:

### `judgment`

- identificador interno estable;
- archivo, ROJ y ECLI;
- órgano, sección y fecha;
- ejercicios y países;
- tipo de procedimiento y pretensiones, cuando consten;
- `source_sha256`;
- versiones de extractor, schema, prompt y modelo;
- estado global técnico y jurídico.

### `legal_issues[]`

Cada cuestión debe tener:

- `issue_id` estable;
- pregunta jurídica legible;
- tipo canónico;
- normas y criterios aplicados;
- IDs de hechos y pruebas relacionados;
- `holding_id`;
- razonamiento decisivo;
- anclajes de fuente;
- estado de revisión propio.

Ejemplos: residencia, permanencia, centro económico, presunción familiar, CDI,
liquidación, ganancia patrimonial, sanción o tipo aplicable.

### `facts[]`

Cada hecho debe distinguir:

- sujeto;
- categoría;
- país y lugar;
- fecha, intervalo o ejercicio;
- valor estructurado y descripción derivada;
- quién lo afirma;
- si es pacífico, controvertido o considerado probado;
- cuestiones a las que afecta;
- anclajes que permiten verificarlo.

### `evidence_findings[]`

Cada hallazgo probatorio debe incluir:

- prueba o documento;
- parte que lo aporta;
- categoría y subtipo;
- finalidad: qué pretende demostrar;
- hechos y cuestiones relacionados;
- valoración judicial: aceptada, rechazada, parcial o no resuelta;
- motivo de esa valoración;
- papel: decisiva, corroboradora, contradictoria o contextual;
- anclajes de fuente.

No se usa el peso `1–5` del análisis como autoridad jurídica.

### `holdings[]`

Debe separar el resultado global de cada cuestión:

- conclusión judicial;
- resultado canónico por cuestión;
- ratio o paso decisivo;
- consecuencias;
- anclajes literales;
- estado de revisión.

Esto permite encontrar, por ejemplo, una sentencia que mantiene la residencia
pero anula la sanción.

### `burden_of_proof_steps[]`

La etiqueta `AEAT`, `CONTRIBUYENTE` o `AMBOS` es insuficiente. Se representa:

- qué hecho debía probarse;
- quién tenía inicialmente la carga;
- qué indicios se consideraron aportados;
- si y cuándo se desplazó;
- qué debía desvirtuar la otra parte;
- conclusión y anclajes.

### `treaty_analysis[]`

Debe separar:

1. análisis bajo ley interna;
2. existencia de doble residencia;
3. convenio y versión aplicable;
4. pasos de desempate en orden;
5. hechos usados en cada paso;
6. paso decisivo y conclusión;
7. anclajes de fuente.

### `source_anchors[]`

Cada proposición atribuida a la sentencia debe enlazar:

- `anchor_id`;
- `source_sha256`;
- índice físico de página;
- etiqueta impresa, si existe;
- offsets sobre `raw_page_text`;
- fragmentos exactos;
- fidelidad `exact` o `exact_with_ellipsis`;
- finalidad del anclaje;
- estado técnico y jurídico.

Un match fuzzy puede ayudar a localizar una revisión, pero nunca genera una
cita publicable.

### `review_status`

Debe existir por elemento, no solo por documento:

- `generated`;
- `technically_validated`;
- `agent_reviewed`;
- `human_approved`;
- `rejected`;
- `needs_review`.

`stable` técnico no significa aprobación jurídica.

## 6. Corpus verbatim

La representación canónica será JSON por páginas:

```json
{
  "schema_version": "residenciafiscal-verbatim/1",
  "document_id": "san-1210-2023",
  "source_file": "sentencias/SAN_1210_2023.pdf",
  "source_sha256": "...",
  "extractor": {
    "name": "pypdf",
    "version": "..."
  },
  "page_count": 10,
  "pages_sha256": "...",
  "status": "COMPLETE",
  "pages": [
    {
      "page_index": 1,
      "printed_page": null,
      "raw_page_text": "...",
      "text_sha256": "...",
      "extraction_status": "TEXT_EXTRACTED"
    }
  ]
}
```

El posible `verbatim/<slug>.md` es únicamente una vista para personas. Los
chunks son otro derivado y conservan página, offsets, texto exacto, estrategia
de segmentación y hashes.

No se eliminan cabeceras, pies, firmas ni repeticiones en esta capa. La
selección de relevancia pertenece al modelo jurídico y al índice.

## 7. Flujo híbrido y responsabilidades

| Acción | Python | Agente | Persona |
|---|:---:|:---:|:---:|
| Extraer texto de cada página | Autoridad | No | Inspección |
| Calcular hashes e IDs | Autoridad | No | No |
| Proponer cuestiones y hechos | Validar | Autoría asistida | Revisar |
| Relacionar pruebas y cuestiones | Validar contrato | Proponer y revisar | Aprobar |
| Localizar anclajes candidatos | Buscar | Proponer | Revisar casos dudosos |
| Publicar cita literal | Validar exactitud | No altera | Puede aprobar contexto |
| Renderizar JSON/Markdown | Autoridad | No | No |
| Aprobar interpretación jurídica | Registrar | No | Autoridad exclusiva |

El agente produce datos estructurados o sidecars. No edita artefactos generados
ni texto legal.

## 8. Rollout

### Fase A — contrato y tests

**Estado (2026-07-29): completada.** El contrato campo por campo, los modelos,
el JSON Schema, los fixtures y los invariantes están implementados. La
cobertura de las familias del piloto se documenta en
[`JURISPRUDENCE_CASE_SCHEMA_V3.md`](JURISPRUDENCE_CASE_SCHEMA_V3.md#18-cobertura-del-piloto-de-40-preguntas).

Entregables:

- [x] `docs/JURISPRUDENCE_CASE_SCHEMA_V3.md`;
- [x] modelos Pydantic;
- [x] JSON Schema exportado;
- [x] catálogos y reglas de IDs;
- [x] fixtures válidos e inválidos;
- [x] tests de relaciones, anclajes e invariantes.

Gate superado a nivel de diseño: el contrato puede representar las 40 preguntas
sin recurrir a campos genéricos como única solución. La validación con contenido
real pertenece a las fases B y C.

### Fase B — una sentencia

**Estado (2026-07-29): en curso.** B1 —contrato, extractor crudo, JSON Schema,
fixtures y tests de `residenciafiscal-verbatim/1`— está completado. B2 debe
materializar y validar el JSON de `SAN 1210/2023` antes de iniciar el análisis
jurídico híbrido.

Se utilizará `SAN 1210/2023` porque combina permanencia, centro económico,
familia, vivienda, documentación extranjera, carga de la prueba, regularización
y sanción.

Entregables:

- [x] contrato y extractor verbatim;
- [ ] verbatim JSON de `SAN 1210/2023`;
- caso v3;
- perfil OKF derivado;
- informe de validación;
- sidecar de revisión;
- índice de recuperación unitario.

Gates:

- 100 % de citas publicadas son exactas;
- cada cuestión tiene holding propio;
- cada hecho y prueba relevante se relaciona con una cuestión;
- toda valoración atribuida al tribunal tiene anclaje;
- dos builds producen los mismos hashes;
- se responden desde v3 las preguntas aplicables del piloto.

### Fase C — cinco sentencias

Se regeneran las cinco ya preparadas sin crear un segundo camino.

Gates:

- se cubren resultados y estructuras heterogéneas;
- las 40 preguntas se ejecutan contra el índice;
- casos y contracasos esperados son recuperables;
- se clasifican las 17 citas pendientes;
- se miden campos ausentes, valores no canónicos y coste de revisión;
- se decide y congela v3 antes de ampliar.

### Fase D — recuperación

Baseline inicial:

1. facetas por cuestión, criterio, país, CDI, periodo y tipo de prueba;
2. búsqueda léxica sobre hechos, valoraciones y holdings;
3. reranking por cobertura de los hechos del usuario;
4. diversificación para incluir apoyo y contraste;
5. reagrupación por sentencia.

Se registra `recall@k`, precisión de fuentes, cobertura y comportamiento de
abstención. Los embeddings solo se incorporan si superan de forma reproducible
al baseline en el mismo banco.

### Fase E — 106 sentencias

Requisitos previos:

- schema v3 congelado;
- manifiesto explícito de PDFs y hashes;
- orquestación reanudable y publicación atómica;
- política de revisión humana;
- gates técnicos y jurídicos medidos con cinco;
- decisión de almacenamiento de verbatim e índice.

Los borradores pueden generarse automáticamente. Solo se publican como
revisados los elementos aprobados según la política editorial.

### Fase F — chat

El backend se implementa después de validar el índice:

- recupera cuestiones, no documentos completos;
- inyecta solo 6–12 unidades relevantes dentro del presupuesto;
- incluye casos principales y de contraste;
- usa `ChatSourceV2` con cuestión, anclaje, página, fidelidad y hash;
- exige una fuente válida por afirmación sustantiva;
- pregunta por hechos ausentes;
- se abstiene fuera del corpus;
- no predice el resultado del usuario.

## 9. Estrategia RAG y coste

Sí se adopta recuperación aumentada, pero no se inyecta todo el corpus.

```text
pregunta + historial relevante
  → extracción de hechos y cuestiones
  → filtros + búsqueda
  → 6–12 unidades por cuestión
  → casos y contracasos
  → respuesta con anclajes
```

El trabajo LLM costoso se concentra fuera de línea al preparar o revisar una
sentencia. En cada conversación solo se envían:

- la pregunta y el historial acotado;
- los hechos detectados;
- las unidades recuperadas;
- metadatos y citas necesarios.

Esto reduce tokens, latencia y riesgo de confusión frente a inyectar 106
sentencias, aunque cupieran en una ventana de un millón de tokens.

Antes de añadir infraestructura se compara:

1. facetas + búsqueda léxica;
2. la misma recuperación con embeddings;
3. opcionalmente reranking semántico.

Se elige la alternativa más simple que cumpla la evaluación.

## 10. Evaluación

El banco manual de 40 preguntas es la verdad de referencia inicial. Cada caso
machine-readable deberá conservar:

- pregunta y contexto;
- hechos presentes y ausentes;
- cuestiones y facetas requeridas;
- sentencias y cuestiones esperadas;
- casos de contraste;
- afirmaciones obligatorias y prohibidas;
- anclajes esperados;
- conducta: responder, preguntar, comparar o abstenerse.

Gates bloqueantes:

- cero identificadores o anclajes inventados;
- cero citas no literales presentadas como judiciales;
- cero afirmaciones sustantivas sin fuente válida;
- separación de resultados por cuestión;
- comportamiento correcto fuera del corpus;
- preservación exacta del texto legal.

Métricas de calidad:

- recall de cuestiones y sentencias;
- presencia de contracasos;
- precisión de páginas y extractos;
- cobertura de hechos relevantes;
- tasa de preguntas correctamente solicitadas;
- revisión jurídica humana de una muestra.

## 11. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Sobreajustar el schema a cinco casos | Validarlo contra 40 preguntas y permitir extensiones tipadas |
| Inventar precisión jurídica | Anclajes por proposición y revisión granular |
| Confundir resumen con sentencia | Tipos de contenido y UI diferenciados |
| Procesar 106 antes de descubrir gaps | Gates obligatorios 1 → 5 → 106 |
| Embeddings sin beneficio | Baseline común y comparación medida |
| Coste alto por llamada | Recuperación selectiva y análisis fuera de línea |
| Derivados divergentes | Un modelo canónico y renderizadores compartidos |
| Revisión humana inabarcable | Priorizar por estado, riesgo y citas pendientes |
| Texto extraído defectuoso | PDF como autoridad, hashes y defectos declarados |

## 12. Orden inmediato de ejecución

1. Escribir el contrato campo por campo de v3.
2. Implementar los modelos y tests antes del extractor jurídico.
3. Materializar el verbatim JSON de `SAN 1210/2023`.
4. Crear el caso v3 híbrido para esa sentencia.
5. Renderizar su Markdown desde v3.
6. Responder desde datos las preguntas del piloto que le corresponden.
7. Corregir el schema una sola vez con lo aprendido.
8. Regenerar las cinco.
9. Medir recuperación con las 40 preguntas.
10. Decidir si hacen falta embeddings.
11. Congelar v3 y autorizar, o no, las 106.
12. Retomar el backend del chat sobre el corpus validado.

## 13. Criterio de terminación

Esta iniciativa termina cuando:

- las 106 sentencias tienen fuente, verbatim y caso v3 trazables;
- los derivados se regeneran desde contratos y manifiestos;
- toda cita publicada es literal y localizable;
- el chat recupera por cuestión y presenta casos y contracasos;
- las respuestas distinguen hechos, alegaciones y conclusiones;
- el sistema pide información o se abstiene cuando corresponde;
- la evaluación y revisión jurídica tienen resultados versionados;
- ninguna respuesta necesita inyectar el corpus completo.
