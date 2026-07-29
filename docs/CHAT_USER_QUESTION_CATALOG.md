# Catálogo inicial de preguntas del chat

## Finalidad

Este documento simula cómo puede preguntar una persona que llega con un caso
particular de residencia fiscal. Es el punto de partida para:

1. diseñar el schema jurisprudencial;
2. decidir qué información debe recuperarse de cada sentencia;
3. construir el banco de evaluación del chat;
4. comprobar si una respuesta está respaldada por casos y pasajes concretos.

El producto se concibe como una herramienta de investigación jurisprudencial.
No debe decidir dónde reside fiscalmente el usuario ni sustituir el criterio del
abogado. Debe localizar resoluciones relevantes, mostrar qué factores se
valoraron, distinguir similitudes y diferencias y permitir que el profesional
extraiga sus propias conclusiones.

Este catálogo desarrolla el caso de uso principal y su contrato funcional,
definidos en
[`CHAT_JURISPRUDENCE_USE_CASE.md`](CHAT_JURISPRUDENCE_USE_CASE.md). La primera
selección de 40 preguntas, contestada manualmente contra las cinco sentencias
preparadas, está en
[`experiments/CHAT_QUESTION_PILOT_5.md`](experiments/CHAT_QUESTION_PILOT_5.md).

## Comportamiento esperado

Ante una consulta sobre un caso particular, el chat debería:

1. identificar la cuestión jurídica y los hechos que el usuario ha facilitado;
2. preguntar por los datos decisivos que falten;
3. recuperar sentencias comparables por hechos, pruebas y criterio jurídico;
4. presentar casos favorables y desfavorables cuando existan;
5. explicar qué coincide y qué diferencia cada sentencia del caso descrito;
6. separar lo afirmado por las partes, lo considerado por Hacienda y lo
   aceptado o rechazado por el tribunal;
7. enlazar cada afirmación relevante con sentencia, página y extracto
   verificado;
8. indicar cuando el corpus no permite contestar;
9. evitar predecir el resultado del caso del usuario.

## 1. Preguntas generales sobre los criterios de residencia

| ID | Pregunta posible |
|---|---|
| GEN-01 | ¿Qué tiene en cuenta Hacienda para demostrar que una persona reside fiscalmente en España? |
| GEN-02 | ¿Qué pruebas suelen considerar los tribunales más importantes para decidir la residencia fiscal? |
| GEN-03 | ¿Basta con que Hacienda reúna muchos indicios o tiene que probar cada día de presencia en España? |
| GEN-04 | ¿Qué criterios han sido decisivos en las sentencias en las que ganó Hacienda? |
| GEN-05 | ¿Qué pruebas permitieron a contribuyentes demostrar que no residían en España? |
| GEN-06 | ¿Qué diferencia hay entre permanencia, centro de intereses económicos y centro de intereses vitales? |
| GEN-07 | ¿Puede Hacienda considerarme residente aplicando solo uno de esos criterios? |
| GEN-08 | ¿Qué hechos suelen valorar conjuntamente aunque ninguno sea concluyente por sí solo? |
| GEN-09 | ¿Qué pruebas aportadas por Hacienda han rechazado los tribunales y por qué? |
| GEN-10 | ¿Qué documentación de los contribuyentes se ha considerado insuficiente? |

## 2. Permanencia durante más de 183 días

| ID | Pregunta posible |
|---|---|
| DAY-01 | He pasado menos de 183 días en España, ¿qué podría utilizar Hacienda para sostener lo contrario? |
| DAY-02 | ¿Cómo han calculado los días de presencia las sentencias del corpus? |
| DAY-03 | ¿Qué valor tienen los pasaportes, billetes de avión y reservas de viaje? |
| DAY-04 | ¿Cómo se tratan los días en los que no se conoce dónde estaba la persona? |
| DAY-05 | ¿Qué son las ausencias esporádicas y cuándo se computan como días en España? |
| DAY-06 | Si trabajo fuera entre semana pero vuelvo a España los fines de semana, ¿hay casos similares? |
| DAY-07 | ¿Una estancia prolongada en otro país demuestra por sí sola que no residía en España? |
| DAY-08 | ¿Qué sucede si Hacienda solo tiene consumos y movimientos bancarios, pero no un calendario completo? |
| DAY-09 | ¿Hay sentencias en las que un certificado extranjero haya impedido computar ausencias como esporádicas? |
| DAY-10 | ¿Quién tiene que probar el número de días y cuándo se desplaza la carga de la prueba? |

## 3. Centro de intereses económicos

| ID | Pregunta posible |
|---|---|
| ECO-01 | Vivo fuera, pero la mayor parte de mis ingresos procede de España. ¿Qué dicen casos similares? |
| ECO-02 | ¿Tener sociedades o participar en consejos de administración españoles puede determinar la residencia? |
| ECO-03 | ¿Qué importancia tienen las cuentas bancarias y el patrimonio situado en España? |
| ECO-04 | ¿Se compara la renta obtenida en España con la obtenida en cada uno de los demás países? |
| ECO-05 | Tengo un empleo extranjero, pero mantengo inversiones en España. ¿Qué factores han resultado decisivos? |
| ECO-06 | ¿La gestión a distancia de empresas españolas se considera actividad económica en España? |
| ECO-07 | ¿Cobrar una pensión, dividendos o retribuciones de administrador en España es suficiente? |
| ECO-08 | ¿Qué pruebas han convencido al tribunal de que el centro económico estaba en el extranjero? |
| ECO-09 | ¿Importa más dónde se genera la renta o dónde está el patrimonio? |
| ECO-10 | ¿Hay casos con actividad económica en dos países y cómo se resolvieron? |

## 4. Familia y centro de intereses vitales

| ID | Pregunta posible |
|---|---|
| FAM-01 | Mi cónyuge y mis hijos viven en España, pero yo trabajo fuera. ¿Hay sentencias comparables? |
| FAM-02 | ¿La residencia de la familia convierte automáticamente al contribuyente en residente español? |
| FAM-03 | ¿Cómo se puede desvirtuar la presunción familiar? |
| FAM-04 | ¿Qué ocurre si la familia se traslada meses después que el contribuyente? |
| FAM-05 | ¿Se ha aceptado que la familia permaneciera en España por estudios, salud o discapacidad? |
| FAM-06 | Estoy separado de hecho, pero no legalmente. ¿Cómo han valorado esa circunstancia los tribunales? |
| FAM-07 | ¿Qué importancia tiene que los hijos estén escolarizados en España? |
| FAM-08 | ¿Se consideran otros familiares o únicamente cónyuge e hijos menores dependientes? |
| FAM-09 | ¿Hay casos en los que el centro vital estaba en España pero el económico en otro país? |

## 5. Vivienda, consumos y vida cotidiana

| ID | Pregunta posible |
|---|---|
| HOM-01 | Tengo una vivienda disponible en España, pero digo que no la utilizo. ¿Cómo puede probar Hacienda su uso efectivo? |
| HOM-02 | ¿Qué valor tienen los consumos de electricidad, agua, gas o gasóleo? |
| HOM-03 | ¿Un inmueble propiedad del cónyuge o de una sociedad vinculada se considera disponible para el contribuyente? |
| HOM-04 | ¿Qué han deducido los tribunales de entregas de paquetería, vino, combustible u otros productos? |
| HOM-05 | ¿Tener personal doméstico, alarma o mantenimiento demuestra que la vivienda se usa habitualmente? |
| HOM-06 | ¿Qué importancia tienen las reparaciones de vehículos o recogidas en el domicilio? |
| HOM-07 | ¿Pagar gimnasios, clubes deportivos o asociaciones sirve como prueba de presencia? |
| HOM-08 | ¿Cómo se valoran las retiradas de efectivo y los pagos con tarjeta realizados en España? |
| HOM-09 | ¿Las visitas médicas pueden utilizarse para acreditar presencia y con qué límites? |
| HOM-10 | ¿Existen casos en los que los consumos se consideraron insuficientes o contradictorios? |

## 6. Residencia y documentación extranjera

| ID | Pregunta posible |
|---|---|
| FOR-01 | Tengo un certificado de residencia fiscal extranjero. ¿Es suficiente para acreditar que no resido en España? |
| FOR-02 | ¿Qué requisitos han exigido los tribunales a los certificados de residencia extranjeros? |
| FOR-03 | ¿Qué diferencia hay entre permiso de residencia, certificado consular y certificado de residencia fiscal? |
| FOR-04 | ¿Un contrato de alquiler extranjero demuestra residencia efectiva? |
| FOR-05 | ¿Qué valor tienen la declaración fiscal extranjera y los justificantes de haber pagado impuestos allí? |
| FOR-06 | ¿Se han rechazado certificados extranjeros por no acreditar tributación por la renta mundial? |
| FOR-07 | ¿Qué documentos complementarios reforzaron un certificado extranjero? |
| FOR-08 | ¿Hay casos relativos al mismo país en el que yo afirmo residir? |
| FOR-09 | ¿Cómo se ha valorado un contrato de trabajo extranjero iniciado a mitad de año? |
| FOR-10 | ¿Qué sucede si también presenté declaraciones o comuniqué un domicilio en España? |

## 7. Convenios de doble imposición

| ID | Pregunta posible |
|---|---|
| CDI-01 | España y el otro país me consideran residente. ¿Cómo se resuelve la doble residencia? |
| CDI-02 | ¿Qué significa tener una vivienda permanente a disposición en un país? |
| CDI-03 | Tengo vivienda permanente en ambos países. ¿Qué se analiza después? |
| CDI-04 | ¿Qué hechos se han usado para determinar el centro de intereses vitales del convenio? |
| CDI-05 | ¿Cómo se prueba dónde vive una persona de manera habitual? |
| CDI-06 | ¿Hay sentencias que hayan llegado al criterio de nacionalidad o al acuerdo entre autoridades? |
| CDI-07 | ¿Qué paso del desempate fue decisivo en casos relativos a Francia, Suiza, Reino Unido u otro país? |
| CDI-08 | ¿Puede aplicarse el convenio si el certificado extranjero no menciona expresamente el propio convenio? |

## 8. Carga de la prueba y actuación de Hacienda

| ID | Pregunta posible |
|---|---|
| PRU-01 | ¿Qué debe probar inicialmente Hacienda para considerarme residente? |
| PRU-02 | ¿Cuándo corresponde al contribuyente desvirtuar los indicios de Hacienda? |
| PRU-03 | ¿Puede Hacienda basarse exclusivamente en pruebas indirectas? |
| PRU-04 | ¿Qué se considera un conjunto de indicios sólido y concordante? |
| PRU-05 | ¿Hay casos en los que Hacienda perdió por no investigar o probar suficientemente? |
| PRU-06 | ¿Cómo valoran los tribunales una prueba aislada frente a la valoración conjunta? |
| PRU-07 | ¿Qué ocurre cuando hay documentos o indicios contradictorios? |
| PRU-08 | ¿Se han anulado actuaciones por vulnerar la intimidad al pedir datos médicos o realizar seguimientos? |
| PRU-09 | ¿Qué valor tienen las declaraciones de representantes, empleados, vecinos o proveedores? |
| PRU-10 | ¿Qué hechos se consideraron la prueba decisiva o “bala de plata” en otros casos? |

## 9. Sanciones y pronunciamientos distintos de la residencia

| ID | Pregunta posible |
|---|---|
| SAN-01 | Aunque Hacienda demuestre la residencia, ¿puede anularse la sanción? |
| SAN-02 | ¿Una discrepancia razonable sobre la residencia excluye la culpabilidad? |
| SAN-03 | ¿Qué motivación debe contener el acuerdo sancionador? |
| SAN-04 | ¿Cómo influye haber obtenido un certificado fiscal extranjero en la sanción? |
| SAN-05 | ¿Hay sentencias en las que Hacienda ganó la liquidación pero perdió la sanción? |
| SAN-06 | ¿Qué otros pronunciamientos aparecen junto a la residencia: exenciones, tipos, ganancias o devoluciones? |

## 10. Búsqueda y comparación de casos

| ID | Pregunta posible |
|---|---|
| CMP-01 | Busca sentencias con hechos parecidos a los míos. |
| CMP-02 | ¿Cuáles son los tres casos más similares y por qué? |
| CMP-03 | ¿Qué hechos de mi caso coinciden con cada sentencia y cuáles son diferentes? |
| CMP-04 | ¿Hay casos similares en los que ganó Hacienda y otros en los que ganó el contribuyente? |
| CMP-05 | Compara cómo se valoró la misma prueba en sentencias con resultados distintos. |
| CMP-06 | ¿Qué factor explica que dos casos aparentemente parecidos terminaran de forma diferente? |
| CMP-07 | Muéstrame casos del mismo país, criterio y tipo de prueba. |
| CMP-08 | ¿Cuál es la sentencia más parecida dictada por el Tribunal Supremo? |
| CMP-09 | ¿Hay doctrina más reciente que trate una situación similar? |
| CMP-10 | Dame los casos comparables sin decirme qué resultado tendría mi asunto. |
| CMP-11 | ¿Qué argumentos de esos casos podría contrastar un abogado con mis documentos? |
| CMP-12 | Enséñame también los casos que contradicen la posición que estoy planteando. |

## 11. Preparación del caso y preguntas hipotéticas

Estas preguntas deben contestarse describiendo patrones observados en las
sentencias, no dando instrucciones jurídicas personalizadas.

| ID | Pregunta posible |
|---|---|
| PRE-01 | Con los datos que te he dado, ¿qué hechos faltan para encontrar casos realmente comparables? |
| PRE-02 | ¿Qué documentos aparecen habitualmente en los casos sobre este criterio? |
| PRE-03 | ¿Qué aspectos de situaciones parecidas cuestionó Hacienda? |
| PRE-04 | ¿Qué pruebas fueron rechazadas por no demostrar residencia efectiva? |
| PRE-05 | ¿Qué diferencias entre mi situación y los precedentes debería revisar un abogado? |
| PRE-06 | Si mi familia permaneciera en España, ¿qué casos pasarían a ser más relevantes? |
| PRE-07 | ¿Cambiarían los casos comparables si hubiera estado 170 días en España en lugar de 190? |
| PRE-08 | ¿Y si tuviera certificado fiscal extranjero pero no declaración de impuestos allí? |
| PRE-09 | ¿Qué precedentes serían relevantes si el centro económico y la familia estuvieran en países distintos? |
| PRE-10 | ¿Qué hechos de mi relato no aparecen tratados en el corpus? |

## 12. Fuentes, literalidad y límites

| ID | Pregunta posible |
|---|---|
| SRC-01 | ¿En qué sentencia y página se afirma eso? |
| SRC-02 | Muéstrame el texto exacto de la sentencia, no un resumen. |
| SRC-03 | ¿Ese fragmento es literal o procede del análisis automático? |
| SRC-04 | Dame el ROJ, ECLI, fecha, órgano y enlace a la resolución oficial. |
| SRC-05 | ¿La cuestión jurídica de esa sentencia ha sido revisada por una persona? |
| SRC-06 | ¿Qué nivel de confianza tiene la extracción de este caso? |
| SRC-07 | ¿Hay sentencias relevantes que no puedas verificar o citar literalmente? |
| SRC-08 | ¿El corpus contiene toda la jurisprudencia aplicable a mi situación? |
| SRC-09 | ¿Puedes determinar con estas sentencias dónde soy residente fiscal? |
| SRC-10 | ¿Qué parte de la respuesta no consta en las resoluciones recuperadas? |

## 13. Ejemplos de conversaciones típicas

### Conversación A: consulta general que se concreta

1. «¿Qué tiene en cuenta Hacienda para probar residencia en España?»
2. «En mi caso tengo vivienda, pero casi no la uso.»
3. «Los suministros son bajos, aunque mi familia vive allí.»
4. «¿Qué casos se parecen y qué diferencias hay?»
5. «Muéstrame los extractos exactos y las páginas.»

### Conversación B: trabajo y familia en países distintos

1. «Trabajo todo el año en Reino Unido, pero mi cónyuge y mis hijos siguen en
   España.»
2. «Mis hijos permanecieron para terminar el curso escolar.»
3. «¿Se ha aceptado esa explicación en alguna sentencia?»
4. «Compárala con casos en los que no se consiguió desvirtuar la presunción.»

### Conversación C: certificado extranjero

1. «Tengo certificado fiscal de Suiza. ¿Con eso basta?»
2. «También tengo contrato de trabajo, seguro médico y movimientos bancarios.»
3. «¿Qué pruebas similares aceptaron los tribunales?»
4. «¿Qué documentos extranjeros rechazaron en otros casos y por qué?»

### Conversación D: permanencia discutida

1. «Hacienda dice que estuve más de 183 días, pero no tiene todos mis vuelos.»
2. «Utiliza pagos con tarjeta, visitas médicas y consumos de una vivienda.»
3. «¿Hay casos construidos con esos indicios?»
4. «¿En cuáles fueron suficientes y en cuáles no?»

### Conversación E: doble residencia y CDI

1. «España y Francia me consideran residente.»
2. «Tengo vivienda en los dos países y actividad económica en España.»
3. «¿Qué paso del convenio han aplicado casos comparables?»
4. «¿Qué hechos se usaron para decidir el centro de intereses vitales?»

### Conversación F: liquidación y sanción

1. «Si pierdo la discusión sobre residencia, ¿la sanción se mantiene
   automáticamente?»
2. «Yo tenía un certificado de residencia extranjero.»
3. «¿Hay sentencias que confirmaron la liquidación pero anularon la sanción?»
4. «Enséñame la motivación exacta del tribunal.»

## 14. Metadatos para convertir preguntas en banco de evaluación

Cada pregunta seleccionada para el banco debería evolucionar a un registro con:

| Campo | Función |
|---|---|
| `id` | Identificador estable, por ejemplo `DAY-05` |
| `question` | Pregunta exacta del usuario |
| `conversation_context` | Mensajes anteriores necesarios |
| `intent` | Criterio, prueba, comparación, sanción, fuente o límite |
| `case_facts` | Hechos expresamente proporcionados |
| `missing_facts` | Datos que el chat debería solicitar |
| `required_facets` | Criterios, países, pruebas, órgano, años o CDI |
| `expected_cases` | Sentencias que deberían recuperarse |
| `counter_cases` | Sentencias relevantes con resultado o razonamiento contrario |
| `must_mention` | Hechos o límites que deben aparecer |
| `must_not_assert` | Conclusiones que el corpus no permite afirmar |
| `required_quotes` | Sentencia, página y extracto exacto esperado |
| `needs_verbatim` | Si el perfil estructurado no contiene el pasaje necesario |
| `expected_behavior` | Responder, pedir datos, comparar o abstenerse |
| `difficulty` | Básica, seguimiento, comparativa o adversarial |

## 15. Consecuencias preliminares para el futuro modelo de datos

El catálogo sugiere que `resultado_final` y un resumen global no bastan. Para
responder con precisión harán falta, como mínimo:

- cuestiones jurídicas separadas dentro de cada sentencia;
- criterio aplicado y paso decisivo;
- hechos relevantes normalizados;
- pruebas de cada parte, finalidad, aceptación, rechazo y motivo;
- carga de la prueba y quién la cumplió;
- países, CDI y paso de desempate;
- resultados separados para residencia, liquidación, sanción y otros motivos;
- extractos judiciales exactos con página;
- estado técnico y estado de revisión jurídica;
- relaciones explícitas de similitud y diferencia calculadas para cada
  consulta, sin usar el resultado como atajo de relevancia.

La selección inicial ya se ha ejecutado en
[`experiments/CHAT_QUESTION_PILOT_5.md`](experiments/CHAT_QUESTION_PILOT_5.md):
40 preguntas anotadas contra las cinco sentencias. El experimento concluye que
el perfil v2 permite lectura y trazabilidad, pero necesita evolucionar antes de
las 106 para recuperar por cuestión, hechos y pruebas enlazados.
