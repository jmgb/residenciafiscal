# Propuesta aislada: ausencias esporádicas

**Estado:** `PROPOSED_NOT_APPLIED`.
**Artefacto verificable:** [`CHAT_DATA_GAP_ABSENCES_CANDIDATE.json`](CHAT_DATA_GAP_ABSENCES_CANDIDATE.json).

## Por qué existe

La pregunta `DAY-05` —«¿Qué son las ausencias esporádicas y cuándo
computan?»— detectó un hueco de recuperación en la muestra piloto. Las
sentencias sí contienen material útil, pero los casos estructurados no lo
exponen como criterio recuperable específico.

El baseline F0.2 también conserva una incidencia de redacción: una respuesta
afirma que las ausencias «no se computarán [...] salvo que» se acredite
residencia exterior, mientras las citas que publica dicen «se computarán [...]
salvo que». El baseline ciego no se corrige ni se sobrescribe; el revisor debe
evaluar esa contradicción conforme al gate de fidelidad y al criterio de fallo
crítico. La propuesta de datos no se presenta como corrección automática de una
respuesta ya generada.

La propuesta conserva dos tipos de evidencia separados:

- la reproducción de la regla legal en `SAN 1226/2021`;
- el razonamiento de la Sala sobre su aplicación y la acreditación de
  residencia exterior en `SAN 1210/2023`.

Los pasajes del JSON son copias literales del verbatim por páginas. El texto de
las sentencias no se corrige, resume ni normaliza dentro de las citas.

## Qué se puede afirmar y qué no

La muestra permite proponer esta regla de recuperación:

> Para calcular la permanencia superior a 183 días, las ausencias esporádicas
> se computan salvo que el contribuyente acredite su residencia fiscal en otro
> país.

La frase anterior es una proposición estructurada propuesta, no una cita. Las
citas `EXACT` que la respaldan están en el artefacto JSON.

Con estas cinco sentencias no debe ofrecerse una definición exhaustiva de qué
hace que una ausencia sea «esporádica». Si el usuario pregunta por esa
delimitación, el chat debe explicar la regla respaldada, declarar el límite de
la muestra y evitar completar el hueco con conocimiento no recuperado.

## Aislamiento y aprobación

Este artefacto no forma parte del corpus canónico, no se compila y no modifica
los casos ni sus derivados. Tras una revisión jurídica humana:

1. se acepta, corrige o rechaza la proposición;
2. si se acepta, se actualizan las propuestas fuente del pipeline híbrido;
3. se recompilan casos y derivados de forma determinista;
4. se repite `DAY-05` sin sobrescribir el baseline F0.2.

Nunca se editan manualmente los JSON o Markdown generados del corpus.

## Verificación mecánica

```bash
make validate-chat-absences-candidate
```

El validador comprueba hashes del PDF y del verbatim, correspondencia de
documento y página, y que cada cita sea una subcadena literal de la página.
