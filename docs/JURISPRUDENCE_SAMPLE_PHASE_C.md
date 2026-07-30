# Fase C: muestra funcional de cinco sentencias

**Estado:** completada el 2026-07-29.
**Decisión:** congelar `residenciafiscal-case/3` para la siguiente fase; no
integrar todavía el chat productivo.

## Qué valida esta fase

La muestra comprueba que un único flujo híbrido puede representar resoluciones
con estructuras y resultados distintos, conservar literalmente el texto
judicial y producir unidades recuperables para preguntas de un abogado.

Python tiene autoridad sobre extracción, hashes, offsets, contratos,
relaciones, renderizado y gates. El agente prepara la propuesta jurídica y
selecciona fragmentos copiados del verbatim. Ninguna propuesta del agente se
convierte en texto judicial: solo los fragmentos exactos validados pueden
publicarse como cita. La aprobación jurídica sigue reservada a una persona.
Todos los artefactos resultantes viven en `knowledge/jurisprudencia-v3/`.
`knowledge/jurisprudencia/` se reserva al bundle OKF/2 legado para que ambos
contratos y manifiestos no se contaminen.

## Ejecución

```bash
make export-case-v3-sample
```

El comando no llama a ningún LLM. Regenera las propuestas ya preparadas mediante
el manifiesto
[`jurisprudence_v3_sample_5.json`](../sentencias/jurisprudence_v3_sample_5.json),
construye el corpus agregado, ejecuta las 40 preguntas, mide la cola de revisión
y valida la disposición de las citas heredadas.

```text
5 PDF + 5 propuestas + 5 evaluaciones
  → 5 verbatim por páginas
  → 5 casos residenciafiscal-case/3
  → 5 perfiles OKF/3 + 12 unidades por cuestión
  → corpus agregado
  → banco e informe de 40 preguntas
  → informe de calidad + gate de 17 citas heredadas
```

Dos ejecuciones consecutivas con las mismas entradas produjeron los mismos
bytes en verbatim, casos, Markdown, índices y reportes.

## Cobertura obtenida

| Sentencia | Cuestiones | Resultado de residencia | Rasgo diferencial |
|---|---:|---|---|
| SAN 1071/2025 | 3 | Gana AEAT | residencia y sanción con resultados distintos |
| SAN 1136/2016 | 2 | Gana contribuyente | carga de la prueba y sucesiones |
| SAN 1210/2023 | 3 | Gana AEAT | indicios, ganancias y sanción |
| SAN 1226/2021 | 1 | Gana contribuyente | cómputo expreso de 214 días |
| SAN 1386/2017 | 3 | Gana contribuyente | traslado a Suiza, familia y análisis CDI |
| **Total** | **12** | — | — |

Los cinco casos suman 62 anclajes y 62 fragmentos literales. Todos tienen
fidelidad `EXACT`; el pipeline no ha corregido ortografía, ligaduras ni saltos
del PDF.

## Evaluación de recuperación

El Markdown humano
[`CHAT_QUESTION_PILOT_5.md`](experiments/CHAT_QUESTION_PILOT_5.md) se convierte
de forma determinista en un banco machine-readable de 40 preguntas. El baseline
es léxico, auditable y sin embeddings.

| Métrica por sentencia | Top 5 unidades | Top 12 unidades |
|---|---:|---:|
| Recall medio de casos esperados | 91,71 % | 100 % |
| Recall medio de casos de contraste | 89,13 % | 100 % |

El informe completo está en
`knowledge/jurisprudencia-v3/reports/chat-question-pilot-5.retrieval-evaluation.json`.
El 100 % a 12 no es un resultado productivo: el corpus contiene exactamente 12
unidades y, por tanto, recuperar todas garantiza cobertura. La medida a 5 es
más informativa. El banco también comparte formulaciones con la preparación
manual del corpus; la fase D debe añadir paráfrasis no vistas, precisión,
diversificación y pruebas de abstención antes de elegir embeddings o conectar
el chat.

El informe v2 declara explícitamente `evaluation_scope: RETRIEVAL_ONLY` y
`chat_behavior_gate: NOT_EVALUATED`. Conserva para cada pregunta la conducta
esperada —20 `responder`, 12 `parcial`, 7 `preguntar` y 1 `abstenerse`—, pero no
finge haber evaluado todavía un agente conversacional que la ejecute. Por tanto,
estas métricas no permiten aprobar un sistema que siempre responda: el gate de
conducta sigue abierto hasta probar la fase D extremo a extremo.

Antes de agregar los índices, el exportador comprueba su `judgment_id`, el hash
del PDF y el hash del caso contra el manifiesto y `sample-build.json`. El
informe de calidad selecciona también exactamente los cinco IDs del manifiesto,
por lo que restos de ejecuciones anteriores no alteran las métricas.

## Citas heredadas

Las 17 citas no publicables del perfil anterior ya no quedan pendientes:

| Disposición | Cantidad |
|---|---:|
| Sustituida por uno o más anclajes v3 exactos | 15 |
| Retirada como paráfrasis no necesaria | 2 |
| Sin clasificar | 0 |

La decisión de cada cita vive en
`knowledge/jurisprudencia-v3/evaluations/legacy-citation-dispositions.json` y se
valida contra los reportes heredados y los IDs reales de los casos v3.

## Calidad y coste de revisión

El informe `knowledge/jurisprudencia-v3/reports/sample-5.quality.json` registra:

- 0 fallos de campos obligatorios y 0 valores fuera de catálogo;
- 62 anclajes exactos;
- 193 elementos granulares en estado `AGENT_REVIEWED`;
- 0 elementos `HUMAN_APPROVED`;
- nulos explícitos por campo, que representan información no declarada y no
  fallos de extracción.

Los 193 elementos son una aproximación de cola editorial, no horas ni 193
conclusiones independientes. Incluyen caso, identidad, cuestiones, hechos,
pruebas, reglas, holdings, cronología, CDI y anclajes. Antes del lote de 106 se
debe definir una revisión por riesgo que priorice holdings, valoraciones
probatorias, CDI y citas mostradas al usuario.

## Decisiones aprendidas y freeze

La muestra no exigió campos genéricos nuevos ni cambios incompatibles. Sí
confirmó estas reglas:

1. La misma pieza documental puede tener valoraciones distintas por cuestión;
   se representa con hallazgos probatorios separados y anclados.
2. Una fecha o una doble residencia no se infieren por completar el esquema.
   Si la sentencia no las declara inequívocamente se conserva `null` y se
   explica en revisión.
3. Un resultado global nunca sustituye el holding por cuestión.
4. Cronología y CDI solo se materializan cuando el texto permite sostenerlos.
5. Los nulos y colecciones vacías son información explícita, no permiso para
   que el chat rellene huecos.

Quedan congelados los JSON Schema versionados. El contrato de caso v3 tiene
SHA-256
`141a82e20b9d8afdd530f68d454b730e3fcb2a060a23553408460319a81382b3`.
El JSON Schema del índice por caso v1 queda en
`7ea7002e102b8f6f07795ecea078e013e277a939025873ffaa6104a87758797c`
y el del corpus agregado v1 en
`08d6b88fcc034b077b630d5947dcbb50e29c497a320f843fa0ada5ccca54dc45`.

Estos hashes incorporan la extensión opcional `residence_determination`
añadida en E0. Durante la expansión solo se aceptan cambios compatibles y
opcionales. Un cambio de significado, obligatoriedad o catálogo requiere nueva
versión, migración, regeneración de la muestra y repetición de estos gates.

## Estado y siguiente paso

La fase D posterior ya mejoró y midió selección, diversificación
apoyo/contraste, extracción de hechos y abstención. Su informe conserva esta
fase C como baseline inmutable y aplaza los embeddings para el piloto:
[`JURISPRUDENCE_RETRIEVAL_PHASE_D.md`](JURISPRUDENCE_RETRIEVAL_PHASE_D.md).
El chat productivo sigue sin estar listo y los casos no pueden presentarse como
revisados jurídicamente.
