# Fase E0 y E — preparación y ejecución del rollout jurisprudencial

## Estado actual

El rollout técnico autorizado se ejecutó el 1 de agosto de 2026. El manifiesto
`sentencias/jurisprudence_v3_rollout_106.json` fija PDF, propuesta y evaluación
por SHA-256. Los 11 lotes terminaron con 106/106 documentos `BUILD_PASSED`:

- 42 documentos de riesgo `HIGH` y 64 `STANDARD`;
- 106 casos y perfiles v3 trazables;
- 67 documentos dentro del ámbito de recuperación y 39 fuera de ámbito;
- 74 unidades de recuperación agregadas;
- 350 anclajes exactos, 243 anclajes exactos con elipsis y 936 fragmentos de
  fuente;
- 1.620 elementos jurídicos `AGENT_REVIEWED` y 0 `HUMAN_APPROVED`.

La publicación del build es `AGENT_REVIEWED_ONLY`. Es un corpus interno
procesado, no una aprobación jurídica humana ni una autorización para sustituir
la estrategia del chat.

## Alcance y decisión

E0 preparó la expansión del corpus, antes de que se autorizara crear el listado
de las 106 sentencias y ejecutar sus lotes. Dejó implementados:

- resultado residencial tipado y proyectado al índice;
- regeneración y validación de las cinco sentencias;
- banco holdout congelado y primera medición sin ajuste;
- contrato de manifiesto para el futuro rollout;
- estado reanudable por documento;
- reintentos explícitos, ejecución por lotes y gates separados;
- política de revisión técnica y jurídica.

Ese límite histórico terminó con la autorización del 1 de agosto. La fase E
posterior usó el mismo contrato y los mismos gates para materializar el corpus
completo descrito en «Estado actual».

## Resultado residencial tipado

`IssueHolding.residence_determination` es opcional para conservar
compatibilidad con casos v3 anteriores. Solo puede aparecer en cuestiones
`TAX_RESIDENCE` y contiene:

| Campo | Significado |
|---|---|
| `spanish_residence` | `RESIDENT_IN_SPAIN`, `NON_RESIDENT_IN_SPAIN`, `PARTIAL_YEAR_IN_SPAIN` o `NOT_DECIDED` |
| `tax_years` | Ejercicios a los que se refiere la conclusión |
| `other_country` | País extranjero cuando la conclusión no es residencia española íntegra |
| `non_resident_from` | Fecha desde la que deja de existir residencia española en un año parcial |

No sustituye `holding.outcome`: este último expresa quién gana la cuestión,
mientras que `residence_determination` expresa dónde y para qué periodo queda
situada la residencia. Tampoco sustituye el texto del holding ni sus anclajes.

Las cinco determinaciones actuales son:

| Sentencia | Determinación |
|---|---|
| SAN 1071/2025 | Residente en España, 2010–2011 |
| SAN 1136/2016 | Residente en España, 2007 |
| SAN 1210/2023 | Residente en España, 2011–2013 |
| SAN 1226/2021 | No residente en España, 2011; Reino Unido |
| SAN 1386/2017 | Año parcial; no residente desde 2009-04-01; Suiza |

La faceta se copia al índice. Fase D ya no interpreta palabras del holding para
decidir apoyo o contraste: si una unidad residencial antigua carece de esta
faceta, su dirección es `mixed`.

## Regeneración de las cinco

`make export-case-v3-sample` reconstruyó verbatim, casos, perfiles, índices e
informes desde las entradas versionadas, sin llamadas LLM. Los gates técnicos
pasaron y las métricas de fase D permanecen sin regresión:

| Métrica @3 | Antes | Después |
|---|---:|---:|
| Recall de casos esperados | 83,37 % | 83,37 % |
| Precisión de casos relevantes | 73,64 % | 73,64 % |
| Recall de contrastes | 85,19 % | 85,19 % |
| Conducta, banco de desarrollo | 100 % | 100 % |

El contenido jurídico sigue en `AGENT_REVIEWED`; regenerar no equivale a
aprobación humana.

## Holdout congelado

El banco
[`CHAT_QUESTION_HOLDOUT_E.json`](../experiments/CHAT_QUESTION_HOLDOUT_E.json)
contiene 20 preguntas nuevas con anotaciones propias. No hereda respuestas del
piloto. Su lock registra SHA-256, cardinalidad, fecha y la política
`NEVER_TUNE_PHASE_D_WITH_THIS_BANK`.

El banco se creó después de cerrar la implementación tipada y antes de su
primera ejecución. Desde ese momento no se cambiaron reglas ni pesos usando sus
resultados. La evaluación declara `OBSERVE_ONLY_NO_TUNING`.

Primera medición:

| Métrica | Resultado |
|---|---:|
| Exactitud de conducta | 75,00 % |
| Seguridad sin fuentes al preguntar/abstenerse | 83,33 % |
| Recall esperado @3 | 72,14 % |
| Precisión de casos relevantes @3 | 77,78 % |
| Recall de contraste @3 | 70,83 % |

El resultado confirma que el 100 % del banco de desarrollo no generaliza. Las
cinco discrepancias quedan registradas, pero no se corrigen contra el holdout:

- dos consultas cubiertas fueron clasificadas fuera de alcance;
- una consulta personal recibió fuentes sin pedir todos los hechos;
- dos consultas parciales fueron tratadas como respuestas completas.

Artefactos:

- lock: `docs/experiments/CHAT_QUESTION_HOLDOUT_E.lock.json`;
- informe:
  `knowledge/jurisprudencia-v3/reports/phase-e0-holdout-evaluation.json`.

## Contrato del rollout

El schema versionado
`schemas/residenciafiscal-rollout-v1.schema.json` describe el manifiesto. El
listado real está versionado en
`sentencias/jurisprudence_v3_rollout_106.json` y se genera de forma explícita a
partir del legado autorizado; no se descubren PDF implícitamente.

Cada entrada fija:

- `judgment_id`;
- PDF y SHA-256;
- propuesta y banco de evaluación, también bloqueados por hash;
- `batch_id` explícito y contiguo;
- riesgo `HIGH` o `STANDARD`.

El contrato impide IDs o PDFs duplicados. Al reanudar, el programa comprueba
que identificador, lote, riesgo y orden de todos los documentos coinciden
exactamente con el manifiesto bloqueado por hash. También rechaza que un build
devuelva artefactos asociados a un `judgment_id` distinto del que está
ejecutando.

El estado persistido conserva por documento:

- número de intentos;
- `PENDING`, `RUNNING`, `BUILD_PASSED` o `BUILD_FAILED`;
- error del último intento;
- hashes de verbatim, caso, Markdown e índice;
- peor estado de revisión jurídica encontrado en el caso.

El estado se escribe después de pasar a `RUNNING` y después de cada éxito o
fallo. Una interrupción permite reanudar sin repetir documentos
`BUILD_PASSED`. Un lote fallido bloquea el siguiente hasta usar explícitamente
`--retry-failed`.

## Política de revisión y gates

La ejecución técnica y la publicación jurídica son decisiones distintas:

| Gate | Requisito |
|---|---|
| Entrada | PDF, propuesta y evaluación existen; hash del PDF coincide |
| Build | Verbatim, caso, perfil e índice pasan contratos y citas exactas |
| Lote técnico | Todos los documentos del lote están `BUILD_PASSED` |
| Revisión | Todos los elementos jurídicos del caso están `HUMAN_APPROVED` |
| Publicación | Gate técnico y revisión humana superados |

`AGENT_REVIEWED` permite mantener un borrador interno, pero el gate devuelve
`AWAITING_HUMAN_REVIEW`. El estado del rollout no puede conceder aprobación:
solo agrega el estado contenido en el caso compilado. La aprobación sigue
requiriendo identidad `human:<identidad>`, fecha y el flujo editorial previsto.

Orden recomendado de revisión dentro de cada sentencia:

1. determinación residencial, holdings y anclajes de conclusión;
2. reglas aplicadas, carga de la prueba y valoración de evidencias;
3. hechos, cronología y relaciones entre entidades;
4. metadatos y presentación derivada.

Todos los niveles deben aprobarse antes de publicación; la prioridad solo
ordena el trabajo.

## Operación

Medir el holdout:

```bash
make evaluate-holdout-e0
```

Regenerar las entradas y el manifiesto determinista:

```bash
make rollout-bootstrap
```

Iniciar o reanudar los lotes:

```bash
make rollout-init
make rollout-status
make rollout-next
make rollout-next ROLLOUT_RETRY=1
```

`rollout-init` no sobrescribe un estado existente. `rollout-status` es de solo
lectura. `rollout-next` procesa únicamente el primer lote incompleto declarado
en el manifiesto.

Cerrar el agregado y ejecutar la evaluación técnica completa:

```bash
make rollout-finalize
make evaluate-rollout-development
make rollout-audit
make rollout-holdout-coverage
make rollout-verify
```

`rollout-finalize` comprueba de nuevo los hashes de cada caso y derivado antes
de agregar. No concede aprobación humana.

## Evaluación del corpus completo

El ajuste del recuperador se hace únicamente contra
`rollout-106.development.bank.json`. Este banco sintético mide lookup explícito
por identificador judicial; no pretende medir relevancia para consultas
genéricas. En 117 consultas, la línea base obtiene 20,51 % top-1 y 34,19 % de
recall @3, mientras que BM25 con reconocimiento de `SAN/STS número/año` obtiene
100 % en ambas métricas. La regresión de fase D continúa en `PASSED`.

El banco técnico de fase E contiene 117 preguntas. Su recall esperado es
52,14 % @5 y 77,78 % @12. No evalúa por sí solo la conducta conversacional.

El holdout E0 se volvió a ejecutar sin modificarlo ni ajustar el retriever:

| Métrica | Corpus de 106 |
|---|---:|
| Exactitud de conducta | 75,00 % |
| Seguridad sin fuentes | 83,33 % |
| Recall esperado @3 | 47,86 % |
| Precisión relevante @3 | 36,11 % (no válida para el corpus completo) |
| Recall de contraste @3 | 20,83 % |

El holdout solo etiqueta cinco sentencias. Las otras 101 aparecen como no
relevantes aunque nunca fueron anotadas; por eso su “precisión” no es una
medición válida del corpus completo. El recall y el contraste se conservan como
regresión histórica, no como objetivo de ajuste. El diagnóstico reproducible
queda en `rollout-106.holdout-coverage.json` y el holdout conserva la política
`OBSERVE_ONLY_NO_TUNING`.

La segunda pasada automática de los 42 casos HIGH no encontró fallos de
literalidad, pero sí 13 análisis CDI ausentes, 36 determinaciones residenciales
sin tipar, 6 casos con cobertura de anclajes baja y 5 resultados parciales o de
retroacción. Todos permanecen `NEEDS_HUMAN_REVIEW`; la revisión automática no
equivale a aprobación jurídica.

Artefactos principales:

- build: `knowledge/jurisprudencia-v3/rollout-build.json`;
- corpus completo aislado:
  `knowledge/jurisprudencia-v3/retrieval/rollout-106.corpus.json`;
- calidad: `knowledge/jurisprudencia-v3/reports/rollout-106.quality.json`;
- evaluación técnica:
  `knowledge/jurisprudencia-v3/reports/rollout-106.retrieval-evaluation.json`;
- holdout:
  `knowledge/jurisprudencia-v3/reports/rollout-106.holdout-evaluation.json`.
- desarrollo:
  `knowledge/jurisprudencia-v3/reports/rollout-106.development-evaluation.json`;
- auditoría HIGH:
  `knowledge/jurisprudencia-v3/reports/rollout-106.high-risk-audit.json`;
- cobertura de etiquetas:
  `knowledge/jurisprudencia-v3/reports/rollout-106.holdout-coverage.json`.

`knowledge/jurisprudencia-v3/retrieval/corpus.json` conserva la muestra
congelada de cinco usada por Fase D y el chat. El cierre del rollout no la
sobrescribe.

## Próximo gate

Falta revisión jurídica humana. No existe revisor disponible y el agente no
suplanta esa identidad, por lo que los 1.620 elementos siguen pendientes. En
paralelo, cualquier promoción al chat requiere mejorar y validar recuperación
con un banco de desarrollo separado; el holdout no se usa para afinarla.
La política de retención y sus límites está en
[`JURISPRUDENCE_ARTIFACT_POLICY.md`](JURISPRUDENCE_ARTIFACT_POLICY.md).
