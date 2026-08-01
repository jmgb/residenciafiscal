# Recuperación jurisprudencial — fase D

## Estado y alcance

La fase D queda implementada y medida sobre la muestra congelada de cinco
sentencias. No conecta aún el chat, no transforma las 106 sentencias y no
sustituye la revisión jurídica humana.

Su objetivo es contestar una pregunta de investigación jurídica con pocas
unidades por cuestión, casos de apoyo y de contraste, o bien decidir que antes
hay que preguntar o abstenerse. El PDF sigue siendo la autoridad y los
extractos literales proceden de los anclajes validados del caso v3.

## Flujo

```text
consulta
  → análisis determinista de facetas y hechos ausentes
  → conducta: responder | parcial | preguntar | abstenerse
  → si se puede responder:
       BM25 + expansión léxica + identificador judicial explícito
       + coincidencia de criterio, prueba, país y periodo
       + cobertura temporal estructurada
       → una unidad como máximo por sentencia
       → inclusión de una conclusión residencial contraria
  → unidades con puntuación desglosada y anclajes
```

`preguntar` y `abstenerse` producen deliberadamente cero fuentes. La abstención
cubre tanto una faceta jurídica no representada como una consulta ajena al
dominio de residencia fiscal. Esto evita que una capa posterior redacte una
respuesta jurídica pese a que falten hechos materiales o cobertura.

La diversificación distingue la conclusión residencial del vencedor procesal.
Por ejemplo, `SAN 1136/2016` da la razón a la contribuyente, pero concluye
residencia en España; no es un contracaso residencial equivalente a una
sentencia que concluya residencia en el extranjero.

## Componentes

| Componente | Responsabilidad |
|---|---|
| `jurisprudence_query_analysis.py` | Extrae criterios, pruebas, países, años, carácter personal, hechos ausentes y cobertura |
| `jurisprudence_phase_d_retrieval.py` | Puntúa, reordena, diversifica y devuelve fuentes o una conducta segura |
| `jurisprudence_phase_d_evaluation.py` | Evalúa después de recuperar; las etiquetas esperadas no entran en el router |
| `export_jurisprudence_phase_d.py` | Genera el informe reproducible con huellas de sus tres entradas |
| `CHAT_QUESTION_PARAPHRASES_5.json` | Conserva 20 reformulaciones sin duplicar sus etiquetas |

Cada puntuación conserva por separado señal léxica y boosts de criterio,
prueba, país y periodo. No es una probabilidad, ni mide fuerza jurídica, ni
puede citarse como valoración del tribunal: solo ordena candidatos de
recuperación.

## Evaluación

El banco consta de las 40 preguntas originales y 20 paráfrasis separadas. Las
paráfrasis heredan conducta, casos esperados y contrastes desde la pregunta
original únicamente al ejecutar la evaluación. El informe declara
`GOLD_USED_ONLY_AFTER_RETRIEVAL`.

Resultados del 30 de julio de 2026, medidos sobre las 45 consultas cuya
conducta esperada permite aportar fuentes:

| Métrica @3 | Baseline léxico | Candidato estructurado |
|---|---:|---:|
| Recall de casos esperados | 78,84 % | 83,37 % |
| Precisión de casos relevantes | 71,32 % | 73,64 % |
| Recall de contrastes | 70,37 % | 85,19 % |

Además:

- exactitud de conducta: 100 % en 40 preguntas originales;
- exactitud de conducta: 100 % en 20 paráfrasis;
- seguridad de cero fuentes al preguntar o abstenerse: 100 %;
- resultado de gates: `PASSED`.

Estas cifras validan una implementación piloto, no generalización. Las reglas
y las paráfrasis se desarrollaron dentro de este mismo ciclo y solo hay cinco
sentencias. Antes de producción hace falta un banco independiente, más casos y
revisión jurídica humana.

La fase E0 posterior congeló ese banco independiente y obtuvo resultados
inferiores, sin reajustar este sistema. Véase
[`JURISPRUDENCE_PHASE_E0.md`](JURISPRUDENCE_PHASE_E0.md).

## Decisión sobre embeddings

El informe registra `NOT_REQUIRED_FOR_PILOT`: el candidato determinista supera
al baseline en las tres métricas sin una base vectorial, llamadas externas ni
coste por consulta. Esto aplaza los embeddings; no demuestra que carezcan de
valor.

Se reabre la comparación si un banco independiente o la expansión del corpus
incumplen los gates. En ese caso, facetas y diversificación permanecen iguales
y solo se compara el generador de candidatos sobre el mismo banco.

## Ejecución reproducible

```bash
make evaluate-retrieval-phase-d
uv run pytest -q tests/test_jurisprudence_phase_d.py
```

Entradas:

- `knowledge/jurisprudencia-v3/retrieval/corpus.json`;
- `docs/experiments/CHAT_QUESTION_PILOT_5.md`;
- `docs/experiments/CHAT_QUESTION_PARAPHRASES_5.json`.

Salida:

- `knowledge/jurisprudencia-v3/reports/phase-d-retrieval-evaluation.json`.

El informe incorpora hashes canónicos del corpus y de ambos bancos. Cambiar una
entrada obliga a regenerarlo.

## Límites y siguiente gate

No debe reutilizarse el router determinista como asesor jurídico ni como
clasificador definitivo. En particular:

- las reglas lingüísticas cubren el dominio y redacción del piloto;
- los casos siguen en estado `AGENT_REVIEWED`, no `HUMAN_APPROVED`;
- aún no se evalúan respuestas redactadas ni fidelidad afirmación→fuente;
- no existe prueba con consultas independientes de usuarios reales;
- la muestra no representa la diversidad de las 106 sentencias;
- la dirección residencial ya es una faceta tipada desde E0; una unidad antigua
  sin ella se clasifica como `mixed`, nunca interpretando texto libre.

El siguiente trabajo es definir la revisión y el rollout de fase E: planificar
la ejecución reanudable de las 106 en lotes operativos, manteniendo el gate
obligatorio 1 → 5 → 106. La integración del chat continúa aplazada hasta que el
corpus ampliado preserve estos gates.
