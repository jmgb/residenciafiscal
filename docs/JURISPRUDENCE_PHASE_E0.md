# Fase E0 — preparación del rollout jurisprudencial

## Alcance y decisión

E0 prepara la expansión del corpus sin crear el listado de las 106 sentencias
ni ejecutar ese lote. Quedan implementados:

- resultado residencial tipado y proyectado al índice;
- regeneración y validación de las cinco sentencias;
- banco holdout congelado y primera medición sin ajuste;
- contrato de manifiesto para el futuro rollout;
- estado reanudable por documento;
- reintentos explícitos, ejecución por lotes y gates separados;
- política de revisión técnica y jurídica.

No existe todavía un manifiesto real de fase E. Ningún PDF fuera de la muestra
de cinco se ha transformado a v3.

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
[`CHAT_QUESTION_HOLDOUT_E.json`](experiments/CHAT_QUESTION_HOLDOUT_E.json)
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
`schemas/residenciafiscal-rollout-v1.schema.json` describe un manifiesto futuro.
No contiene ni genera el listado real.

Cada entrada deberá fijar:

- `judgment_id`;
- PDF y SHA-256;
- propuesta y banco de evaluación;
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

## Operación futura

Medir el holdout:

```bash
make evaluate-holdout-e0
```

Cuando se autorice crear el manifiesto real:

```bash
make rollout-init CASE_ROLLOUT_MANIFEST=<manifiesto>
make rollout-status
make rollout-next CASE_ROLLOUT_MANIFEST=<manifiesto>
make rollout-next CASE_ROLLOUT_MANIFEST=<manifiesto> ROLLOUT_RETRY=1
```

`rollout-init` no sobrescribe un estado existente. `rollout-status` es de solo
lectura. `rollout-next` procesa únicamente el primer lote incompleto declarado
en el manifiesto.

## Próximo paso bloqueado deliberadamente

Falta crear y revisar el manifiesto completo de las 106 sentencias, asignar sus
lotes y riesgos, e iniciar la ejecución. E0 no realiza ninguna de esas acciones
por instrucción expresa. El holdout indica además que el router aún no debe
conectarse al chat productivo.
