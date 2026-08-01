# Caso de uso principal: investigación jurisprudencial conversacional

## Decisión de producto

El caso de uso principal del corpus y del chat jurisprudencial es ayudar a un abogado a
investigar un caso particular de residencia fiscal mediante sentencias
comparables.

El usuario describe hechos o formula preguntas como «¿qué tiene en cuenta
Hacienda para demostrar la residencia fiscal en España?». El sistema no debe
resolver su residencia ni predecir el fallo. Debe permitirle:

1. encontrar rápidamente las sentencias que tratan la cuestión planteada;
2. entender qué hechos, pruebas y argumentos se valoraron en cada caso;
3. distinguir lo alegado por Hacienda y por el contribuyente de lo aceptado,
   rechazado o razonado por el tribunal;
4. comparar casos favorables y desfavorables, explicando coincidencias y
   diferencias relevantes;
5. comprobar cada afirmación sustantiva en la resolución original mediante
   sentencia, página y extracto literal verificado;
6. identificar qué datos faltan y cuándo el corpus no permite responder.

Esta finalidad gobierna el modelo de datos, la recuperación, el prompt, la
presentación de fuentes y la evaluación. Un campo que no ayuda a recuperar,
comparar, explicar o verificar no debe tener prioridad sobre los que sí lo
hacen.

La arquitectura vigente, el estado F0.2, los aprendizajes y el orden de handoff
están consolidados en
[`CHAT_SYSTEM_ARCHITECTURE.md`](CHAT_SYSTEM_ARCHITECTURE.md).

## Ejemplo canónico

### Consulta

> Vivo fuera de España, pero mi familia sigue allí y mantengo una vivienda.
> ¿Qué tiene en cuenta Hacienda y hay casos similares?

### Conducta esperada

1. El chat identifica las cuestiones `183 días`, `presunción familiar`,
   `vivienda y uso efectivo` y, si procede, `centro de intereses`.
2. Pregunta por el periodo, el país alegado, los días, el uso de la vivienda, el
   motivo de permanencia de la familia, la actividad económica y la
   documentación extranjera que falten.
3. Recupera sentencias por coincidencia de **cuestión + patrón de hechos +
   prueba**, no solo por palabras o por el resultado global.
4. Presenta al menos un caso útil en cada dirección cuando el corpus lo permita.
   Por ejemplo, puede contrastar una resolución que valore la permanencia de la
   familia como indicio con otra en la que la presunción se desvirtúe por un
   traslado laboral y pruebas concordantes.
5. Para cada caso explica:
   - qué cuestión resolvió;
   - qué hechos constan;
   - qué prueba aportó cada parte y para qué;
   - qué aceptó o rechazó el tribunal y por qué;
   - qué resultado tuvo esa cuestión concreta;
   - por qué es similar o diferente al supuesto consultado.
6. Cada proposición jurídica o fáctica atribuida a una sentencia lleva una
   referencia resoluble a `ROJ/ECLI + página física + extracto literal`.
7. Termina señalando límites y preguntas que el abogado todavía debe comprobar.

### Conductas incorrectas

- «Eres residente en España» o «ganarías el recurso».
- Elegir únicamente sentencias ganadas por la parte que interesa al usuario.
- Tratar el resultado global de una sentencia como si resolviera igual todas sus
  cuestiones.
- Confundir una alegación, el resumen del LLM o una puntuación interna con una
  conclusión del tribunal.
- Mostrar como cita una paráfrasis o un texto que no sea subcadena del PDF.
- Afirmar que una prueba «siempre» basta a partir de uno o varios casos.
- Omitir una sentencia de contraste porque su resultado sea desfavorable.

## Contrato de respuesta

Una respuesta sustantiva debería poder componerse con estas unidades:

| Unidad | Contenido mínimo |
|---|---|
| `respuesta_sintetica` | Patrón observado en el corpus, con alcance limitado a las resoluciones recuperadas |
| `dato_faltante` | Hecho necesario para afinar la comparación |
| `caso_relevante` | Identificadores, órgano, fecha, periodo, países y cuestión |
| `aplicacion_en_el_caso` | Hechos, pruebas, valoración judicial, paso decisivo y resultado por cuestión |
| `comparacion` | Similitudes y diferencias respecto del caso del usuario |
| `cita` | Extracto literal, página física, etiqueta impresa si existe y hash de la fuente |
| `limite` | Qué no puede concluirse con el corpus recuperado |

El modelo puede redactar y comparar. No puede inventar hechos, completar citas,
convertir un resumen en texto judicial ni ocultar la procedencia.

## Modo experimental de dos respuestas

Antes de seleccionar una estrategia productiva, cada mensaje del usuario
generará dos respuestas consecutivas, independientes y claramente separadas:

1. **Respuesta A — Sistema estructurado actual**, basada en las unidades v3 y
   el ranking local.
2. **Respuesta B — Gemini File Search**, basada únicamente en la búsqueda sobre
   los PDF originales de la misma muestra.

Las respuestas no comparten candidatos, puntuaciones, texto generado ni
fuentes. Sí comparten los gates de seguridad: el PDF continúa siendo la
autoridad y ningún extracto se presenta como judicial sin verificación literal.
La interfaz no las fusiona ni declara automáticamente cuál es mejor. Cada
bloque muestra además su coste marginal en USD, indicando si procede de uso real
del proveedor o de una estimación, y el mismo valor queda registrado en logs
estructurados.

El contrato de independencia, presentación, streaming, medición y tratamiento
de errores está en
[`CHAT_RETRIEVAL_STRATEGY_COMPARISON.md`](CHAT_RETRIEVAL_STRATEGY_COMPARISON.md).
La posible unión de candidatos con reranking local queda documentada allí como
alternativa futura, no implementada.

## Unidad de recuperación

La sentencia completa es una unidad demasiado gruesa. La unidad primaria debe
ser el **pasaje jurídico estructurado por cuestión**, vinculado a su sentencia.
Una misma resolución puede contener resultados distintos sobre residencia,
liquidación, sanción o consecuencias tributarias.

Cada unidad recuperable debe incluir o enlazar:

- `judgment_id`: ROJ, ECLI y `source_sha256`;
- `issue_id`: cuestión jurídica estable dentro de la sentencia;
- `issue_type`: residencia, permanencia, centro económico, familia, CDI,
  prueba, sanción u otra;
- `holding`: resultado y conclusión judicial de esa cuestión;
- `decisive_reasoning`: paso o factor decisivo;
- `facts[]`: hechos normalizados, con periodo, país y sujeto;
- `evidence_findings[]`: prueba, parte, finalidad, valoración y motivo;
- `legal_rules[]`: norma, criterio o paso de CDI aplicado;
- `source_anchors[]`: página y fragmentos literales verificables;
- `review_status`: estado técnico y jurídico por separado.

La ficha de sentencia sigue siendo necesaria para contexto y presentación, pero
el ranking debe operar sobre estas unidades y reagruparlas después por
resolución.

## Recuperación y comparación

La búsqueda debe combinar:

1. facetas jurídicas: criterio, cuestión, país, CDI, tipo de prueba y periodo;
2. coincidencia semántica o léxica con hechos y razonamiento;
3. cobertura de los hechos proporcionados por el usuario;
4. diversidad deliberada: caso principal, casos de apoyo y casos de contraste;
5. disponibilidad de anclajes literales y estado de revisión.

El resultado judicial sirve para construir el contraste, no como sustituto de
la similitud. La similitud se calcula para cada consulta y no se guarda como una
propiedad universal entre dos sentencias.

El chat debe abstenerse o pedir más datos cuando:

- no conoce el ejercicio o el país relevante;
- la pregunta depende de hechos no proporcionados;
- no hay una cuestión equivalente en el corpus;
- solo existen textos pendientes de verificación para respaldar la respuesta;
- las sentencias recuperadas no permiten generalizar.

## Capas de datos y autoridad

```text
PDF original inmutable
    └── texto verbatim por páginas, extraído de forma determinista
          └── anclajes literales verificables

análisis estructurado híbrido
    ├── cuestiones y resultados por cuestión
    ├── hechos y patrones normalizados
    ├── pruebas, finalidad y valoración
    └── razonamiento y normas

índice de recuperación
    └── unidades por cuestión + facetas + enlaces a anclajes

respuesta del chat
    └── síntesis comparativa con referencias resolubles
```

El PDF es la máxima autoridad. Python extrae, identifica, valida, calcula hashes
y renderiza. El agente propone y revisa la estructura jurídica. Ninguna capa
derivada puede alterar el texto de la sentencia.

## Del perfil OKF/2 al caso v3

El diagnóstico que originó v3 fue que `residenciafiscal-okf/2` era una buena
ficha legible, pero no un índice suficiente para este caso de uso:

- `legal_issues` se materializaba principalmente en Markdown y sidecars, no como
  una colección canónica lista para recuperar;
- los hechos aparecían sobre todo en resúmenes narrativos, no como patrones
  normalizados enlazados a cada cuestión;
- una prueba conservaba parte, categoría, criterio, valoración y motivo, pero
  no siempre su relación explícita con una cuestión ni con el hecho que pretendía
  acreditar;
- el resultado global podía ocultar resultados diferentes por cuestión;
- no existía el texto íntegro por páginas recomendado para recuperar
  pasajes fuera de las citas preseleccionadas;
- los estados `draft` y `human_reviewed` no expresaban con suficiente
  granularidad qué cuestión, hecho o valoración había sido revisado;
- el corpus ligero del frontend no contenía la estructura necesaria para esta
  comparación.

El caso `residenciafiscal-case/3` resuelve esas carencias y ya se ha aplicado a
las 106 sentencias: incorpora cuestiones canónicas, hechos y pruebas
relacionados, resultados por cuestión, verbatim por páginas y unidades de
recuperación. Los borradores nuevos siguen `AGENT_REVIEWED_ONLY`.

F0.2 detectó un gap concreto de cobertura sobre ausencias esporádicas y demostró
que las etiquetas heredadas del router no son una evaluación neutral de
respuestas redactadas. El rollout técnico posterior no elimina ese límite ni
autoriza por sí solo promover el corpus completo al chat.

## Criterios de aceptación del corpus

Antes de ampliar a las 106 sentencias, la muestra de cinco debe demostrar que:

- una consulta puede recuperar la cuestión correcta y no solo la sentencia;
- la respuesta identifica casos favorables y de contraste relevantes;
- cada hecho o valoración atribuidos al tribunal tienen anclaje verificable;
- alegaciones, análisis derivado y texto judicial se distinguen sin ambigüedad;
- el sistema puede explicar por qué una prueba se aceptó o rechazó;
- los resultados se separan por cuestión;
- se puede detectar automáticamente cuándo falta información;
- ninguna cita publicada altera el texto extraído del PDF;
- la recuperación puede evaluarse con preguntas y casos esperados versionados.

El catálogo de consultas está en
[`CHAT_USER_QUESTION_CATALOG.md`](CHAT_USER_QUESTION_CATALOG.md). El piloto
manual de cuarenta preguntas sobre cinco sentencias se documenta en
[`experiments/CHAT_QUESTION_PILOT_5.md`](../experiments/CHAT_QUESTION_PILOT_5.md).
La recuperación estructurada, sus veinte paráfrasis, las conductas seguras y la
decisión provisional de no añadir embeddings se documentan en
[`JURISPRUDENCE_RETRIEVAL_PHASE_D.md`](JURISPRUDENCE_RETRIEVAL_PHASE_D.md).
La estrategia de implementación, responsabilidades y gates 1 → 5 → 106 están
en
[`JURISPRUDENCE_DATA_V3_ROADMAP.md`](JURISPRUDENCE_DATA_V3_ROADMAP.md).

## Estado de preparación

Las cinco sentencias piloto ya usan el caso canónico v3, texto verbatim por
páginas, unidades recuperables por cuestión y determinación residencial
tipada. La recuperación de fase D pasa sus gates sobre el banco de desarrollo
sin necesidad de embeddings.

F0.2 añade un redactor a A y la compara con File Search sobre los PDF originales
mediante ocho consultas reales. Ambas rutas verifican las fuentes y conservan
coste y errores por separado. La prueba no declara una ganadora: antes exige una
rúbrica neutral, revisión humana ciega y corregir la cobertura de ausencias
esporádicas. Resultados:
[`CHAT_STRATEGY_F02_RESULTS.md`](../experiments/CHAT_STRATEGY_F02_RESULTS.md).

E0 añadió una comprobación independiente: en el holdout congelado la conducta
correcta baja al 75 % y la seguridad de no devolver fuentes cuando debe
preguntar o abstenerse queda en 83,33 %. Repetido sobre las 106, el recall
esperado @3 queda en 47,86 %, la precisión relevante en 33,33 % y el recall de
contraste en 12,50 %. Ese banco es exclusivamente de observación y no puede
utilizarse para ajustar el router. Por ello el corpus completo sirve como
borrador de investigación y evaluación interna, pero no se promueve al chat.

El contrato, las mediciones y el resultado del rollout reanudable están en
[`JURISPRUDENCE_PHASE_E0.md`](JURISPRUDENCE_PHASE_E0.md).
