# Revisión híbrida de la muestra OKF de cinco sentencias

## Objetivo y alcance

Esta revisión aplica el reparto de responsabilidades acordado:

- Python extrae páginas, congela hashes, normaliza modelos, recupera citas
  literales, valida anclajes y genera los artefactos;
- el agente revisa PDF y análisis conjuntamente, propone cuestiones jurídicas
  diferenciadas y copia fragmentos exactos como anclajes;
- una persona revisora decide posteriormente si aprueba o rechaza las
  propuestas.

El agente no edita el PDF, no reescribe citas y no marca sus propias propuestas
como revisión humana.

## Resultado

| Sentencia | Literales | Pendientes | Cuestiones propuestas | Estado |
|---|---:|---:|---:|---|
| SAN 1071/2025 | 12 | 5 | 3 | `draft` |
| SAN 1136/2016 | 15 | 0 | 2 | `stable` |
| SAN 1210/2023 | 21 | 6 | 3 | `draft` |
| SAN 1226/2021 | 14 | 3 | 1 | `draft` |
| SAN 1386/2017 | 19 | 3 | 3 | `draft` |
| **Total** | **81** | **17** | **12** | — |

`stable` solo describe la verificación automática de citas y la ausencia de
warnings; no equivale a aprobación jurídica humana. Las doce cuestiones siguen
en estado `proposed`.

## Aportación del agente

- SAN 1136/2016 separa la residencia de actora y causante del efecto sobre las
  reducciones del Impuesto sobre Sucesiones.
- SAN 1210/2023 distingue residencia, ganancias patrimoniales no justificadas y
  sanción tributaria.
- SAN 1226/2021 conserva como cuestión principal la no residencia en España y
  explicita que la Sala se apoya en el efecto reflejo de una sentencia previa.
- SAN 1386/2017 separa residencia suiza, ausencia de exención de la
  indemnización de alta dirección y aplicación del tipo de no residentes.

Estas distinciones aumentan la cobertura respecto de un único
`resultado_final`, especialmente en sentencias con resultado material mixto.

## Gates automáticos aplicados

- Los cinco PDF y registros coinciden con
  `sentencias/okf_muestra_5.json`.
- Todos los anclajes del agente son subcadenas exactas de su página física.
- Ningún match fuzzy se publica como texto de la sentencia.
- Los cinco conceptos, snapshots e informes técnicos tienen hash en el
  manifiesto.
- Dos órdenes de entrada diferentes producen artefactos idénticos.
- Un error de entrada o validación impide publicar el lote completo.

## Puntuaciones y pesos

Las puntuaciones de matching son diagnósticos para priorizar revisión, no
medidas de validez jurídica. Por ello viven en
`reports/<slug>.verification.json` y no en el Markdown principal.

El peso 1–5 procede del análisis estructurado, no del tribunal. Se conserva por
compatibilidad y aparece rotulado como `Peso del análisis (1–5)`. Antes del
rollout a 106 conviene medir si realmente mejora ordenación o recuperación; si
no aporta valor observable, debe eliminarse del futuro prompt para ahorrar
tokens de entrada y salida.

## Trabajo abierto antes de 106

1. Una persona debe aprobar o rechazar las doce cuestiones y las correcciones
   propuestas.
2. Deben clasificarse las 17 citas pendientes, priorizando los dos
   `not_found` de SAN 1210/2023 y SAN 1226/2021.
3. Hay que decidir si el peso 1–5 permanece en la siguiente versión del schema.
4. Debe probarse la representación `verbatim/` antes de elegir la estrategia
   RAG; el perfil OKF no sustituye al texto íntegro cuando la pregunta exige un
   pasaje no seleccionado.
5. Solo tras esos pasos se congela un manifiesto de 106 entradas.
