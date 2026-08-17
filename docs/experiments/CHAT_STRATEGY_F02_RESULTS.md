# Resultados F0.2 — redacción comparable sobre cinco sentencias

**Estado:** evaluación de desarrollo completada; banco de 40 y promoción de
modelo aplazados.
**Fecha:** 2026-07-30.
**Modelo de ambas estrategias:** `gemini-3.5-flash-lite`.
**Muestra:** cinco sentencias.

La arquitectura y el estado canónicos están en
[`CHAT_SYSTEM_ARCHITECTURE.md`](../jurisprudence/CHAT_SYSTEM_ARCHITECTURE.md).
Este documento conserva la evidencia y decisión específicas del experimento.

## Objetivo

F0.2 convierte la comparación inicial en una prueba más justa:

- A conserva su recuperación jurídica estructurada, pero ya no muestra un
  inventario determinista; un LLM redacta con las unidades recuperadas;
- B conserva Gemini File Search sobre los PDF originales;
- ambas usan el mismo modelo y la misma instrucción jurídica base;
- cada estrategia mantiene recuperación, contexto, fuentes, coste y errores
  independientes;
- no existe fallback de una estrategia a la otra.

La extensión de A exige que el modelo devuelva IDs opacos `E<n>`. La aplicación
resuelve esos IDs a fragmentos literales ya verificados; el modelo no redacta
ni reconstruye citas. B obtiene sus fuentes de las anotaciones de File Search y
las contrasta localmente contra el verbatim/PDF.

Una respuesta sustantiva sin al menos una fuente verificable se retira y se
publica como `error`. El coste incurrido se conserva aunque la respuesta quede
bloqueada.

## Banco de desarrollo

Se seleccionaron ocho preguntas del banco canónico de 40, sin modificarlas:

[`CHAT_STRATEGY_F02_DEV_SET.json`](CHAT_STRATEGY_F02_DEV_SET.json).

La selección cubre pregunta general, caso particular incompleto, prueba
concreta, CDI, familia, falta de cobertura, contraste y solicitud de fuentes.
Incluye las cuatro conductas heredadas: responder, parcial, preguntar y
abstenerse.

Esas etiquetas se diseñaron originalmente para evaluar el router estructurado.
Por tanto, su coincidencia sirve para detectar regresiones de A, pero **no es
una métrica neutral para declarar ganadora a A o B**.

## Presupuesto de contexto de A

La primera redacción LLM de A inyectó demasiados anclajes. Se limitó el contexto
a un máximo de dos fragmentos por unidad recuperada, conservando las unidades
de apoyo y contraste.

| Medición sucesiva sobre `GEN-01` | Tokens de entrada | Fuentes exactas | Coste de A |
|---|---:|---:|---:|
| Antes del límite | 31.038 | 13 | USD 0,010731 |
| Después del límite | 8.954 | 10 | USD 0,003499 |
| Variación | −71,1 % | −3 | −67,4 % |

La comparación muestra el efecto observado en dos ejecuciones sucesivas, no un
benchmark determinista. El límite reduce contexto redundante sin eliminar
ninguna de las cinco sentencias recuperadas para esa pregunta.

## Resultados

Los importes de B marcados como estimados son límites inferiores: Interactions
no informó los tokens de modalidad `document` recuperados. Los importes de A
incluyen los tokens de la redacción; preguntar o abstenerse antes de llamar al
modelo cuesta USD 0.

| ID | Conducta heredada | A: estado / coste / fuentes | B: estado / coste / fuentes |
|---|---|---|---|
| `GEN-01` | responder | completa / USD 0,003499 real / 10 | completa / ≥ USD 0,002362 estimado / 4 |
| `DAY-01` | preguntar | pregunta / USD 0 / 0 | completa / ≥ USD 0,001829 estimado / 4 |
| `FOR-02` | parcial | parcial / USD 0,003236 real / 2 | error / USD 0,000861 real / 0 |
| `CDI-01` | preguntar | pregunta / USD 0 / 0 | completa / ≥ USD 0,001119 estimado / 1 |
| `FAM-02` | responder | completa / USD 0,004231 real / 8 | completa / ≥ USD 0,001727 estimado / 4 |
| `DAY-05` | abstenerse | abstención / USD 0 / 0 | completa / ≥ USD 0,000930 estimado / 2 |
| `CMP-04` | responder | completa / USD 0,004417 real / 6 | error / USD 0,000409 real / 0 |
| `SRC-02` | responder | completa / USD 0,002911 real / 10 | pregunta / USD 0,000282 real / 0 |

El artefacto local original de `CMP-04` se generó antes de endurecer el gate y
conserva `parcial` sin fuentes. Aplicando el contrato actual, su interpretación
es `error` y la prosa no se publica. No se repitió una llamada de pago solo para
reescribir ese artefacto.

### Agregados observados

| Métrica | A — estructurada | B — File Search |
|---|---:|---:|
| Coste total marginal | USD 0,018294 | ≥ USD 0,009519 |
| Tokens de entrada informados | 44.830 | 1.203 + documentos no informados |
| Tokens de salida/razonamiento | 1.938 | 3.663 |
| Latencia media | 2.462 ms | 8.620 ms |
| Latencia mediana | 1.825 ms | 9.193 ms |
| Fragmentos exactos publicados | 36 | 15 |
| Coincidencia con etiquetas heredadas | 8/8 | 2/8 |

El coste conjunto observado fue al menos USD 0,027813. No incluye preparar el
corpus v3 ni indexar el store. No debe compararse el total de entrada de A con
el de B como si fueran magnitudes completas: B omite en cinco ejecuciones los
tokens de los documentos recuperados.

## Revisión cualitativa

- En `GEN-01` ambas respuestas son útiles. A es más concisa y muestra apoyo y
  contraste de las cinco sentencias; B ofrece una explicación más extensa.
- En `FAM-02` ambas distinguen correctamente la presunción familiar de una
  conversión automática en residente. Una aclaración común en el prompt evitó
  que B confundiera residencia fiscal con extranjería.
- En `FOR-02` y `CMP-04`, B produjo prosa sin fuentes locales verificables. El
  gate actual la bloquea en vez de degradarla silenciosamente.
- En `DAY-05`, B recuperó pasajes pertinentes sobre ausencias esporádicas, pero
  su redacción afirma que «no se computarán [...] salvo que» se acredite
  residencia exterior, mientras las fuentes publicadas dicen que «se
  computarán [...] salvo que». La formulación parece invertir la regla y debe
  tratarse como posible fallo crítico hasta la revisión jurídica. La abstención
  de A revela además una carencia del dato estructurado; ninguno de los dos
  hechos constituye una victoria automática de una estrategia.
- En `DAY-01` y `CDI-01`, A pide hechos para comparar el caso particular,
  mientras B contesta la regla general. Ambas conductas pueden ser correctas
  según la intención de producto.
- En `SRC-02`, A expone diez fragmentos exactos; B pide concretar el caso o la
  cuestión. También aquí hace falta una regla de producto, no solo una etiqueta
  heredada.

## Decisión

No se ejecuta todavía el banco completo de 40 ni se promociona a
`gemini-3.7-flash`.

Antes deben completarse estos gates:

1. congelar una rúbrica neutral que distinga «explicar la regla general» de
   «aplicar al caso particular y pedir hechos»;
2. añadir al corpus estructurado la cobertura de ausencias esporádicas, con
   anclajes verificables;
3. realizar revisión humana ciega de las ocho respuestas;
4. fijar métricas que no premien por diseño al router de A;
5. repetir solo después el banco de desarrollo ampliado y reservar un holdout
   que no se use para ajustar.

Un modelo más caro no corrige esos gaps de datos, grounding o evaluación. La
promoción a 3.6 seguirá siendo manual y solo tendrá sentido cuando exista una
rúbrica capaz de medir su mejora.

F0.3 ya congeló esa rúbrica y convirtió estas salidas en un paquete X/Y
saneado. La revisión jurídica ciega por un abogado especialista permanece
pendiente:
[`CHAT_STRATEGY_F03_LEGAL_REVIEW_PROTOCOL.md`](CHAT_STRATEGY_F03_LEGAL_REVIEW_PROTOCOL.md),
[`CHAT_STRATEGY_F03_RUBRIC.md`](CHAT_STRATEGY_F03_RUBRIC.md),
[`CHAT_STRATEGY_F03_BLIND_REVIEW.md`](CHAT_STRATEGY_F03_BLIND_REVIEW.md) y
[`CHAT_STRATEGY_F03_REVIEW_FORM_TEMPLATE.md`](CHAT_STRATEGY_F03_REVIEW_FORM_TEMPLATE.md).

## Integración pendiente con el paquete compartido

F0.2 usa un puerto asíncrono local y un adaptador temporal mínimo de Gemini
Interactions. El paquete interno compartido de peticiones LLM lo implementa
otro agente. Cuando esté disponible, debe sustituir solo el adaptador de
infraestructura, conservando:

- el contrato de redacción estructurada;
- `fallback_policy="disabled"`;
- modelo explícito y común para A y B;
- uso y coste devueltos por llamada;
- `store=false`;
- los tests de grounding y resolución de IDs.
