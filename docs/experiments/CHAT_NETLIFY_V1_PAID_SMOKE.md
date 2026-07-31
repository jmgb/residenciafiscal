# Smoke pagado de la V1 Netlify-only

**Fecha:** 2026-07-31.  
**Estado:** una observación técnica válida; no es evaluación jurídica ni autoriza
Production.

## Objetivo y método

Se ejecutó el runtime TypeScript de la Netlify Function con proveedores reales,
las cinco sentencias del corpus v3 y el File Search Store ya preparado. A y B
comenzaron en paralelo bajo el mismo deadline global de 52 segundos. No se usó
el comparador Python histórico ni se activó el sitio.

Pregunta:

> ¿Qué tiene en cuenta Hacienda para demostrar la residencia fiscal en España?

La ejecución capturada fue `paid-smoke-621cd961-0148-4d54-bcc1-656479b6cd67`.
El ledger no formó parte del smoke porque Netlify Database todavía no está
provisionada localmente; recuperación, proveedores, verificación de citas,
tokens, coste y deadline sí fueron los de la Function.

## Resultado medido

| Dimensión | A · corpus estructurado | B · Gemini File Search |
|---|---:|---:|
| Estado | `completa` | `completa` |
| Modelo | `gpt-5.6-luna`, `high` | `gemini-3.5-flash-lite` |
| Latencia propia | 13.536 ms | 9.444 ms |
| Tokens de entrada declarados | 5.457 | 78 |
| Tokens de salida declarados | 1.166 | 902 |
| Tokens de documento declarados | 0 | 0 |
| Coste mostrado | USD 0,002491 | USD 0,002278 |
| Medición | `ACTUAL` | `ESTIMATED` |
| Citas exactas publicadas | 8 | 5 |
| Sentencias distintas citadas | 5 | 4 |

El tiempo de pared fue 13.552 ms: confirma que las estrategias corren en
paralelo y que el orden visual A → B no introduce una espera secuencial. El coste
nominal conjunto fue USD 0,004769, pero no debe tratarse como importe contable
definitivo porque B no informó los tokens de documentos recuperados. Su importe
es una estimación y debe cuadrarse con el panel de Gemini.

Hubo llamadas diagnósticas previas al resultado válido. No se incluyen en la
tabla: el runtime retiró correctamente sus respuestas y no recibió uso completo,
por lo que su posible cargo solo puede determinarse en los paneles de proveedor.

## Calidad provisional

A resultó más útil para investigación por un abogado: distinguió criterios,
hechos acreditados, valoración, carga de prueba y resultados de contraste. Además
declaró límites y citó las cinco sentencias. El precio fue USD 0,000213 mayor y
la latencia propia, 4.092 ms superior a B.

B fue más rápida y su coste estimado fue un 8,6 % menor. Organiza bien los tres
criterios generales, pero ofrece menos contraste entre casos, contiene el error
de redacción «trazitas» y su afirmación sobre certificados extranjeros no queda
respaldada de forma directa por los extractos exactos mostrados. Que las citas
sean literales demuestra fidelidad de la fuente, no que cada proposición de la
prosa esté jurídicamente sustentada.

La preferencia técnica provisional es A para el caso de uso principal y B como
comparador experimental. Esta observación no sustituye la revisión ciega por un
abogado ni permite generalizar desde una sola pregunta.

## Fallos descubiertos y corregidos

1. Gemini API rechazó `labels`, parámetro exclusivo de Enterprise Agent
   Platform. Se retiró del adaptador y quedó cubierto por contrato.
2. El techo de 1.200 tokens de Luna `high` incluía razonamiento y truncó el JSON.
   Se subió a 4.000; el resultado válido consumió 1.166 tokens de salida.
3. El runtime aisló ambos fallos sin filtrar excepciones al usuario, tal como
   exige el contrato.

## Gates que siguen abiertos

- cuadrar el coste estimado de B con la facturación de Gemini y corregir el
  desglose si el proveedor expone los tokens de documento por otra vía;
- provisionar Netlify Database, aplicar la migración y probar concurrencia;
- repetir en Deploy Preview y medir varios días, no una sola pregunta;
- completar privacidad y la revisión jurídica humana.
