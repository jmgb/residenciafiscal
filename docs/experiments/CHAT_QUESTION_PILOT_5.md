# Piloto manual del chat: 40 preguntas sobre 5 sentencias

## Objetivo

Este experimento comprueba si los datos actuales permiten el caso de uso
principal descrito en
[`CHAT_JURISPRUDENCE_USE_CASE.md`](../jurisprudence/CHAT_JURISPRUDENCE_USE_CASE.md):
responder preguntas de un abogado recuperando casos comparables, explicando qué
se aplicó en cada uno y respaldándolo con referencias verificables.

Las respuestas son una **verdad de referencia provisional**, redactada
manualmente solo con las cinco sentencias preparadas. No son asesoramiento, no
pretenden resumir toda la jurisprudencia y no convierten una correlación de la
muestra en una regla general.

## Corpus y notación

| Código | Resolución | País alegado | Resultado relevante sobre residencia |
|---|---|---|---|
| `1071` | [SAN 1071/2025](../../knowledge/jurisprudencia-muestra-5/sentencias/san-1071-2025.md) | Francia | Residencia en España; sanción anulada |
| `1136` | [SAN 1136/2016](../../knowledge/jurisprudencia-muestra-5/sentencias/san-1136-2016.md) | España | Residencia en España reconocida a favor de la contribuyente |
| `1210` | [SAN 1210/2023](../../knowledge/jurisprudencia-muestra-5/sentencias/san-1210-2023.md) | Mónaco | Residencia en España; sanción confirmada |
| `1226` | [SAN 1226/2021](../../knowledge/jurisprudencia-muestra-5/sentencias/san-1226-2021.md) | Reino Unido | No residente en España |
| `1386` | [SAN 1386/2017](../../knowledge/jurisprudencia-muestra-5/sentencias/san-1386-2017.md) | Suiza | Residente en Suiza desde el 1 de abril |

`p.` indica el índice físico del PDF registrado por el pipeline. Los perfiles
enlazados distinguen los extractos literales del contenido narrativo derivado.
Las cuestiones por sentencia siguen en estado `proposed`; ninguna de las cinco
ha recibido todavía aprobación jurídica humana integral.

Estados de respuesta:

- `responder`: la muestra contiene casos y anclajes suficientes para una
  respuesta limitada al corpus;
- `parcial`: permite aportar casos, pero falta cobertura para una respuesta
  general;
- `preguntar`: hacen falta hechos del usuario antes de seleccionar o comparar;
- `abstenerse`: la muestra no permite sostener la respuesta solicitada.

## Banco anotado

### Criterios generales

#### 1. `GEN-01` — ¿Qué tiene en cuenta Hacienda para demostrar la residencia en España?

- **Conducta:** `responder`.
- **Respuesta de referencia:** En esta muestra Hacienda utilizó conjuntos de
  indicios: días y desplazamientos; uso de viviendas; suministros, entregas,
  tarjetas y servicios cotidianos; residencia de la familia; sociedades,
  cargos y rentas en España; y debilidad de la documentación extranjera. En
  `1210` la Sala consideró suficiente la abundancia concordante de consumos,
  vigilancia, viajes, inmuebles y vínculos económicos (pp. 5–8). En `1071`
  resultó decisivo el núcleo de actividades económicas en España, reforzado por
  tarjetas y suministros de la vivienda (pp. 3–5).
- **Casos esperados / contraste:** `1210`, `1071` / `1226`, `1386`.
- **Límite y dato necesario:** No afirmar que todos los indicios sean
  obligatorios ni que uno aislado baste. El chat debe pedir ejercicio, país,
  días, familia, vivienda, actividad y documentos extranjeros.

#### 2. `GEN-02` — ¿Qué pruebas consideran más importantes los tribunales?

- **Conducta:** `responder`.
- **Respuesta de referencia:** Las cinco resoluciones no establecen una
  jerarquía universal. Dan más fuerza a paquetes coherentes con la vida real:
  `1226` combinó traslado laboral, 214 días fuera, traslado familiar, certificado
  y declaración británicos (p. 3); `1386` combinó entrada, empleo, seguro,
  seguridad social, gastos diarios y vivienda en Suiza (pp. 10–11); `1210`
  valoró conjuntamente numerosos indicios españoles (pp. 5–8).
- **Casos esperados / contraste:** `1226`, `1386`, `1210` / ninguno universal.
- **Límite:** El peso `1–5` del perfil es del análisis, no del tribunal, y no
  puede usarse para responder.

#### 3. `GEN-05` — ¿Qué permitió probar que el contribuyente no residía en España?

- **Conducta:** `responder`.
- **Respuesta de referencia:** En `1226`, el traslado a Londres desde el 1 de
  junio, los 214 días fuera, el traslado posterior de esposa e hijos, la
  escolarización, el certificado fiscal y la declaración británica formaron un
  conjunto concordante (p. 3). En `1386`, la entrada en Suiza, el empleo desde
  el 1 de abril, seguros, seguridad social, gastos diarios y vivienda en
  Mendrisio desvirtuaron los indicios españoles y la presunción familiar
  (pp. 10–11).
- **Casos esperados / contraste:** `1226`, `1386` / `1210`.
- **Límite:** No presentar una lista cerrada ni asegurar que esos documentos
  producirían el mismo resultado con hechos distintos.

#### 4. `GEN-09` — ¿Qué pruebas de Hacienda han rechazado los tribunales?

- **Conducta:** `parcial`.
- **Respuesta de referencia:** En `1136` no bastó la manifestación aislada del
  representante del sujeto pasivo para fijar la residencia del causante frente
  a la documentación conjunta de la actora (pp. 3–4). En `1386`, el modelo 190,
  el modelo 030 y algunas nóminas conservaron valor indiciario, pero no
  prevalecieron sobre el conjunto que acreditaba el traslado a Suiza
  (pp. 4, 7 y 10–11).
- **Casos esperados / contraste:** `1136`, `1386` / `1210`.
- **Límite:** Distinguir `rechazada`, `valorada parcialmente` y `superada por
  otra prueba`; el esquema actual no normaliza siempre esa diferencia.

### Permanencia y 183 días

#### 5. `DAY-01` — Digo que pasé menos de 183 días en España, ¿qué usaría Hacienda?

- **Conducta:** `preguntar` y después `responder`.
- **Respuesta de referencia:** `1210` muestra una reconstrucción indirecta con
  entregas, cuotas de gimnasio, visitas médicas, viajes, consumos, vigilancia y
  uso de inmuebles (pp. 5–7). `1071` añade movimientos de tarjeta, repostajes y
  suministros de una vivienda (p. 4). Son indicios que el tribunal valoró
  conjuntamente, no un calendario universal de presencia.
- **Casos esperados / contraste:** `1210`, `1071` / `1226`.
- **Dato necesario:** Calendario, vuelos, estancias, titulares o usuarios de
  tarjetas y viviendas, y residencia fiscal extranjera.

#### 6. `DAY-02` — ¿Cómo calcularon los días las sentencias de la muestra?

- **Conducta:** `parcial`.
- **Respuesta de referencia:** `1226` contiene el cómputo más explícito: 214
  días fuera de España desde el 1 de junio hasta final de 2011 (p. 3). `1386`
  fija como hito la entrada en Suiza el 1 de abril y la corrobora con actividad
  posterior (pp. 10–11). `1210` sustenta la permanencia mediante acumulación de
  indicios, pero el perfil no conserva una línea temporal día a día.
- **Casos esperados / contraste:** `1226`, `1386`, `1210`.
- **Laguna:** Faltan `presence_periods`, eventos fechados y método de cómputo
  estructurados.

#### 7. `DAY-03` — ¿Qué valor tienen pasaportes, billetes y reservas?

- **Conducta:** `parcial`.
- **Respuesta de referencia:** En `1136`, los pasaportes con entradas reiteradas
  reforzaron la residencia en España junto con declaraciones y otros documentos
  (p. 3). En `1226`, los billetes del traslado familiar fueron corroboración del
  traslado al Reino Unido (p. 3). En `1210`, las reservas de viajes y hoteles
  formaron parte de un conjunto de indicios (p. 5).
- **Casos esperados / contraste:** `1136`, `1226`, `1210`.
- **Límite:** La muestra no permite afirmar que esos documentos prueben por sí
  solos todos los días ni quién realizó cada consumo o viaje.

#### 8. `DAY-05` — ¿Qué son las ausencias esporádicas y cuándo computan?

- **Conducta:** `abstenerse` de una doctrina general y aportar contexto parcial.
- **Respuesta de referencia:** La muestra etiqueta el criterio, pero los
  perfiles no contienen una explicación judicial suficiente y homogénea de su
  definición y cómputo. `1226` acredita más de 183 días fuera y residencia
  británica; `1386` acredita residencia suiza desde una fecha concreta. Sirven
  como casos de prueba de residencia exterior, no como definición completa de
  las ausencias esporádicas.
- **Casos esperados:** `1226`, `1386`.
- **Laguna:** Hace falta recuperar los pasajes verbatim donde se formula y aplica
  la regla, además de más resoluciones.

#### 9. `DAY-08` — ¿Bastan consumos y movimientos sin calendario completo?

- **Conducta:** `responder` con cautela.
- **Respuesta de referencia:** En `1210`, no aparecen solos: consumos,
  movimientos, entregas, vigilancia, viajes, servicios e intereses económicos
  se valoraron como un conjunto suficiente (pp. 5–8). En `1071`, tarjetas y
  suministros reforzaron una conclusión cuyo criterio decisivo fue económico
  (pp. 4–5). La muestra permite decir que pueden contribuir decisivamente, no
  que siempre sustituyan un calendario.
- **Casos esperados / contraste:** `1210`, `1071` / `1226`.
- **Límite:** No convertir “abundancia concordante” en una presunción automática.

#### 10. `DAY-10` — ¿Quién debe probar el número de días?

- **Conducta:** `parcial`.
- **Respuesta de referencia:** La carga depende de la pretensión y del estado de
  la prueba. `1210` parte de indicios suficientes de la Administración y exige
  al contribuyente desvirtuarlos (pp. 7–8). `1136` exige a la Administración
  prueba suficiente para desvirtuar los hechos aportados (p. 4). `1386` recuerda
  que quien hace valer su derecho prueba sus hechos constitutivos (p. 4).
- **Casos esperados / contraste:** `1210`, `1136`, `1386`.
- **Límite:** No formular una única regla sin conocer procedimiento, pretensión y
  prueba ya aportada.

### Centro de intereses económicos

#### 11. `ECO-01` — Vivo fuera, pero mis ingresos proceden de España.

- **Conducta:** `preguntar`.
- **Respuesta de referencia:** `1071` declaró residencia española porque el
  núcleo principal de actividades o intereses económicos estaba en España,
  atendiendo al control y administración de una sociedad española y a indicios
  adicionales (pp. 3–5). `1386` muestra el contraste: el empleo, la actividad y
  la vida diaria acreditados en Suiza desde abril prevalecieron en la cuestión
  de residencia (pp. 10–11).
- **Casos esperados / contraste:** `1071` / `1386`.
- **Dato necesario:** Origen y cuantía comparada de rentas, funciones efectivas,
  lugar de gestión, patrimonio, empleo exterior y CDI.

#### 12. `ECO-02` — ¿Influyen sociedades o consejos españoles?

- **Conducta:** `responder`.
- **Respuesta de referencia:** Sí pueden influir. En `1071` la participación
  mayoritaria y administración de Iberdigest formaron parte del criterio
  decisivo del centro económico (pp. 3–4). En `1210`, cargos y percepciones de
  entidades españolas reforzaron los intereses económicos en España (p. 6).
  Ninguna de las dos autoriza a decir que el mero cargo formal determine siempre
  la residencia.
- **Casos esperados / contraste:** `1071`, `1210` / `1386`.
- **Laguna:** El esquema necesita distinguir cargo formal, funciones reales,
  lugar de gestión y renta derivada.

#### 13. `ECO-05` — Empleo extranjero e inversiones en España: ¿qué fue decisivo?

- **Conducta:** `preguntar` y comparar.
- **Respuesta de referencia:** En `1386`, el contrato y la actividad suizos,
  entrada, seguridad social, gastos y vivienda apoyaron el traslado efectivo
  pese a vínculos españoles (pp. 10–11). En `1071`, el tribunal no apreció
  vínculos económicos o afectivos relevantes en Francia que desvirtuaran el
  núcleo español (pp. 4–5).
- **Casos esperados / contraste:** `1386` / `1071`.
- **Dato necesario:** Sustancia del empleo exterior, calendario, gestión de las
  inversiones españolas, rentas por país y vivienda.

#### 14. `ECO-08` — ¿Qué convenció de que el centro económico estaba fuera?

- **Conducta:** `parcial`.
- **Respuesta de referencia:** El mejor caso de la muestra es `1386`: contrato
  con empleador suizo, incorporación el 1 de abril, seguridad social, superación
  del periodo de prueba, gastos diarios y vivienda en Mendrisio (pp. 10–11).
  `1226` también tuvo en cuenta el traslado por el empleador y que el núcleo de
  intereses no radicaba en España (p. 3), aunque el perfil ofrece menos desglose
  económico.
- **Casos esperados / contraste:** `1386`, `1226` / `1071`.
- **Laguna:** Faltan magnitudes comparables de rentas, patrimonio y gestión.

### Familia

#### 15. `FAM-01` — Mi familia vive en España, pero trabajo fuera.

- **Conducta:** `preguntar` y comparar.
- **Respuesta de referencia:** `1386` es comparable: cónyuge e hijo seguían en
  España, pero la discapacidad del hijo explicó esa permanencia y el conjunto
  probatorio acreditó residencia suiza (pp. 10–11). En `1226`, la esposa y los
  hijos se trasladaron al Reino Unido meses después y la presunción quedó
  desvirtuada (p. 3).
- **Casos esperados:** `1386`, `1226`.
- **Dato necesario:** Motivo y duración de la separación, dependencia de hijos,
  vivienda, visitas, días y evidencia del trabajo y vida exterior.

#### 16. `FAM-02` — ¿La familia en España me convierte automáticamente en residente?

- **Conducta:** `responder`.
- **Respuesta de referencia:** No en estos casos: es una presunción susceptible
  de prueba en contrario. `1386` la desvirtuó pese a cónyuge e hijo en España
  (pp. 10–11), y `1226` acreditó el traslado y residencia británicos (p. 3).
  `1136` muestra su uso en sentido contrario, junto con otras pruebas, para
  concluir residencia en España (pp. 3–4).
- **Casos esperados / contraste:** `1386`, `1226` / `1136`.
- **Límite:** No ignorar los requisitos legales de la presunción ni tratarla
  como hecho concluyente.

#### 17. `FAM-03` — ¿Cómo se desvirtúa la presunción familiar?

- **Conducta:** `responder`.
- **Respuesta de referencia:** Mediante prueba coherente de la residencia
  efectiva fuera y una explicación verificable de la situación familiar.
  `1386` combinó empleo, entrada, seguro, gastos y vivienda en Suiza con la
  discapacidad del hijo (pp. 10–11). `1226` combinó traslado laboral, 214 días
  fuera, certificado y declaración británicos y traslado familiar posterior
  (p. 3).
- **Casos esperados / contraste:** `1386`, `1226` / `1136`.
- **Límite:** No reducir la respuesta a un solo documento.

#### 18. `FAM-05` — ¿Se aceptó que la familia quedara por salud o discapacidad?

- **Conducta:** `responder`.
- **Respuesta de referencia:** Sí, en `1386` la Sala valoró que el hijo tenía una
  discapacidad del 33 % y aceptó esa circunstancia dentro del conjunto que
  explicaba la permanencia familiar en España, sin impedir la residencia del
  recurrente en Suiza (pp. 10–11).
- **Casos esperados:** `1386`.
- **Límite:** Es un solo caso; no afirmar que cualquier motivo médico desvirtúe
  por sí solo la presunción.

### Vivienda, consumos y vida cotidiana

#### 19. `HOM-01` — Tengo vivienda en España, pero no la utilizo.

- **Conducta:** `preguntar`.
- **Respuesta de referencia:** `1210` muestra cómo Hacienda intentó probar el
  uso efectivo mediante entregas, suministros, vigilancia, reparaciones,
  servicios e inmuebles vinculados (pp. 5–8). `1071` valoró suministros
  continuados y movimientos de tarjeta próximos a la vivienda (p. 4).
- **Casos esperados / contraste:** `1210`, `1071` / `1386`.
- **Dato necesario:** Disponibilidad, ocupantes, consumos fechados, contratos,
  accesos, entregas y vivienda efectiva en el extranjero.

#### 20. `HOM-02` — ¿Qué valor tienen electricidad, agua, gas o gasóleo?

- **Conducta:** `responder`.
- **Respuesta de referencia:** Fueron indicios de uso, no reglas autónomas. En
  `1071`, agua y electricidad evidenciaron ocupación continuada de la vivienda
  (p. 4). En `1210`, electricidad y entregas de gasóleo se sumaron a muchos
  otros datos de presencia y habitabilidad (pp. 5–7).
- **Casos esperados:** `1071`, `1210`.
- **Límite:** Comprobar titular, inmueble, periodo, patrón y posibles ocupantes;
  el consumo no identifica automáticamente al contribuyente.

#### 21. `HOM-04` — ¿Qué se deduce de paquetería, vino o combustible?

- **Conducta:** `responder`.
- **Respuesta de referencia:** En `1210`, las entregas de vino, paquetes,
  gasóleo y cápsulas en domicilios españoles fueron indicios concordantes de
  uso habitual, junto con consumos, vigilancia y otros servicios (pp. 5–7).
- **Casos esperados:** `1210`.
- **Límite:** La entrega aislada no acredita necesariamente presencia personal;
  hacen falta receptor, frecuencia, fechas y conexión con otros hechos.

#### 22. `HOM-08` — ¿Cómo se valoran tarjetas y retiradas de efectivo?

- **Conducta:** `parcial`.
- **Respuesta de referencia:** En `1071`, restaurantes y repostajes próximos a
  Bescanó reforzaron la ocupación y los vínculos españoles (p. 4). En `1210`,
  movimientos y retiradas gestionadas por una persona de confianza se sumaron
  al conjunto probatorio (p. 6). En `1386`, los gastos diarios en Suiza
  corroboraron la residencia exterior (p. 10).
- **Casos esperados / contraste:** `1071`, `1210` / `1386`.
- **Laguna:** Hay que estructurar autor material, titular, fecha, lugar y fuerza
  inferencial; una operación por tercero no equivale a presencia.

### Documentación extranjera

#### 23. `FOR-01` — ¿Basta un certificado fiscal extranjero?

- **Conducta:** `responder`.
- **Respuesta de referencia:** No puede afirmarse que baste siempre. En `1226`
  el certificado británico fue importante junto con declaración, días y
  traslado (p. 3). En `1386`, los certificados suizos fueron corroboradores,
  no concluyentes por sí solos (pp. 7, 10–11). En `1071`, la documentación
  francesa no desvirtuó la residencia española, aunque contribuyó a excluir
  culpabilidad sancionadora (pp. 4–5).
- **Casos esperados / contraste:** `1226`, `1386` / `1071`, `1210`.
- **Límite:** Diferenciar certificado fiscal, administrativo y consular.

#### 24. `FOR-02` — ¿Qué requisitos se exigieron a los certificados?

- **Conducta:** `parcial`.
- **Respuesta de referencia:** Los casos exigen leer contenido y efecto, no solo
  el título. En `1210`, certificados consulares referidos a aspectos
  administrativos no probaron residencia fiscal efectiva en Mónaco (p. 6). En
  `1386`, la ausencia de domicilio expreso limitó la fuerza de certificados
  suizos, que se valoraron con el resto (pp. 7 y 10–11).
- **Casos esperados:** `1210`, `1386`, `1226`.
- **Laguna:** El schema no conserva de forma normalizada autoridad emisora,
  periodo, renta mundial, CDI invocado y defecto apreciado.

#### 25. `FOR-04` — ¿Un alquiler extranjero prueba residencia efectiva?

- **Conducta:** `responder`.
- **Respuesta de referencia:** No por sí solo según `1210`: el mero hecho de
  poseer o alquilar un inmueble en Mónaco no acreditó ocupación efectiva ni más
  de 183 días frente a los indicios españoles (p. 8). `1386` muestra el
  contraste: la vivienda de Mendrisio se valoró junto con empleo, entrada,
  gastos, seguros, vehículos y cuentas (pp. 10–11).
- **Casos esperados / contraste:** `1210` / `1386`.
- **Límite:** Distinguir disponibilidad jurídica y uso efectivo.

#### 26. `FOR-07` — ¿Qué reforzó la documentación extranjera?

- **Conducta:** `responder`.
- **Respuesta de referencia:** En `1226`: traslado laboral, 214 días fuera,
  traslado familiar, escolarización y declaración británica (p. 3). En `1386`:
  entrada migratoria, contrato, seguridad social, seguro médico, periodo de
  prueba superado, gastos y vivienda suiza (pp. 10–11).
- **Casos esperados / contraste:** `1226`, `1386` / `1210`.
- **Límite:** El patrón relevante es la concordancia con hechos efectivos.

### Convenios de doble imposición

#### 27. `CDI-01` — Dos países me consideran residente, ¿cómo se resuelve?

- **Conducta:** `preguntar` y responder solo de forma parcial.
- **Respuesta de referencia:** La muestra contiene un caso claro de aplicación
  del artículo 4 del CDI hispano-suizo: `1386` analizó vivienda y centro de
  intereses junto con la evidencia de vida y trabajo en Suiza (pp. 6–11).
  `1071` no permite asumir que el CDI con Francia resolviera su cuestión del
  mismo modo.
- **Casos esperados:** `1386`; `1071` como límite.
- **Dato necesario:** País, residencia conforme a cada legislación, texto y año
  del CDI, viviendas, centro vital, estancia habitual y nacionalidad.

#### 28. `CDI-03` — Tengo vivienda permanente en ambos países, ¿qué sigue?

- **Conducta:** `parcial`.
- **Respuesta de referencia:** `1386` permite señalar el centro de intereses
  vitales como paso relevante y muestra hechos de empleo, vivienda, cuentas,
  gastos y familia. Pero estas cinco fichas no ofrecen cobertura suficiente
  para explicar con precisión toda la secuencia de desempate aplicable a
  cualquier convenio.
- **Casos esperados:** `1386`.
- **Laguna:** Faltan `tiebreaker_steps[]` con orden, resultado, hechos y anclajes
  por paso, además del texto vigente del CDI.

#### 29. `CDI-07` — ¿Cómo interactúan CDI y artículo 9 LIRPF?

- **Conducta:** `parcial`.
- **Respuesta de referencia:** El artículo 9 se utiliza para la calificación
  interna y, cuando existe doble residencia relevante, el CDI puede resolver el
  conflicto. `1386` es el caso de la muestra que estructura ambos planos. No
  debe deducirse que invocar un CDI sustituya la prueba de los hechos ni que
  todos los casos lleguen al desempate.
- **Casos esperados:** `1386`; `1071` como contraste de aplicación no
  acreditada en la ficha.
- **Laguna:** Separar en datos `domestic_law_analysis` y `treaty_analysis`.

### Prueba y carga

#### 30. `PRU-01` — ¿Quién tiene la carga de probar la residencia?

- **Conducta:** `parcial`.
- **Respuesta de referencia:** No hay una respuesta única fuera del contexto
  procesal. `1136` exigió a la Administración desvirtuar la prueba aportada
  (p. 4); `1210` consideró que, aportados indicios suficientes, correspondía al
  contribuyente acreditar la realidad de su residencia en Mónaco (pp. 7–8);
  `1386` aplicó la regla de que quien hace valer su derecho prueba los hechos
  constitutivos (p. 4).
- **Casos esperados:** `1136`, `1210`, `1386`.
- **Dato necesario:** Acto impugnado, pretensión y hechos inicialmente
  acreditados.

#### 31. `PRU-02` — ¿Cuándo se desplaza la carga al contribuyente?

- **Conducta:** `parcial`.
- **Respuesta de referencia:** `1210` es el ejemplo más claro de la muestra: la
  Administración aportó un conjunto que la Sala consideró suficiente y la
  documentación monegasca no lo desvirtuó (pp. 5–8). Esta observación no debe
  convertirse en una fórmula automática; `1136` muestra que la Administración
  puede no superar su propia carga frente a prueba contradictoria (pp. 3–4).
- **Casos esperados / contraste:** `1210` / `1136`.
- **Laguna:** Representar la secuencia de carga, no solo una etiqueta `AMBOS`.

#### 32. `PRU-05` — ¿Cómo se valora un conjunto de indicios?

- **Conducta:** `responder`.
- **Respuesta de referencia:** Por concordancia y capacidad conjunta de explicar
  la vida efectiva. `1210` acumuló vivienda, consumos, entregas, vigilancia,
  salud, viajes, banca, familia y actividad (pp. 5–8). `1386` acumuló entrada,
  empleo, seguros, gastos y vivienda en sentido contrario (pp. 10–11). El número
  de indicios no sustituye su conexión con el hecho discutido.
- **Casos esperados / contraste:** `1210` / `1386`.
- **Límite:** No usar el peso analítico ni un conteo bruto como decisión.

#### 33. `PRU-06` — ¿Importa que los indicios sean coherentes entre sí?

- **Conducta:** `responder`.
- **Respuesta de referencia:** Sí es un patrón visible. En `1226` los documentos
  laborales, temporales, familiares y fiscales apuntaban al Reino Unido (p. 3).
  En `1386` documentos de distintas categorías convergían en Suiza
  (pp. 10–11). En `1136`, una manifestación aislada perdió fuerza frente a un
  historial documental coherente en España (pp. 3–4).
- **Casos esperados:** `1226`, `1386`, `1136`.
- **Laguna:** Hace falta relacionar explícitamente cada evidencia con el hecho
  que corrobora o contradice.

### Sanciones

#### 34. `SAN-01` — Si pierdo residencia, ¿la sanción se mantiene automáticamente?

- **Conducta:** `responder`.
- **Respuesta de referencia:** No en la muestra. `1071` mantuvo la conclusión de
  residencia en España, pero anuló la sanción por falta de culpabilidad
  infractora (pp. 4–5). `1210`, en cambio, mantuvo residencia y sanción porque
  consideró motivada la culpabilidad ligada a no justificar la residencia
  efectiva en Mónaco (pp. 8–9).
- **Casos esperados / contraste:** `1071` / `1210`.
- **Límite:** Separar siempre liquidación, residencia y sanción.

#### 35. `SAN-02` — ¿Hay casos con liquidación confirmada y sanción anulada?

- **Conducta:** `responder`.
- **Respuesta de referencia:** Sí: `1071` declaró que la residencia radicaba en
  España y mantuvo la regularización discutida, pero concluyó que no concurría
  culpabilidad y anuló la sanción (pp. 4–5).
- **Casos esperados / contraste:** `1071` / `1210`.
- **Límite:** El resultado global `PARCIAL` no basta para encontrar este patrón;
  se necesita resultado por cuestión.

#### 36. `SAN-05` — ¿Qué diferencia los casos con sanción anulada y confirmada?

- **Conducta:** `parcial`.
- **Respuesta de referencia:** En `1071`, la documentación francesa y las
  circunstancias permitieron mantener una duda incompatible con la culpabilidad
  sancionadora, aunque no vencieran en residencia (p. 5). En `1210`, la Sala
  consideró suficientemente motivada la culpabilidad por no acreditar la
  residencia efectiva en Mónaco (p. 9).
- **Casos esperados / contraste:** `1071` / `1210`.
- **Límite:** Solo hay dos casos sancionadores en la muestra; no generalizar un
  test completo de culpabilidad.

### Comparación, preparación y fuentes

#### 37. `CMP-02` — ¿Qué sentencia se parece más a mi situación?

- **Conducta:** `preguntar`.
- **Respuesta de referencia:** No puede elegirse sin hechos. El chat debe pedir
  como mínimo ejercicio, país, días, familia, viviendas, actividad e ingresos,
  documentación extranjera, CDI, acto discutido y sanción. Después debe
  comparar por cuestión, hechos y pruebas, mostrando también el principal caso
  de contraste.
- **Casos esperados:** Dependen de los hechos.
- **Límite:** No rankear por resultado global ni declarar un «caso gemelo».

#### 38. `CMP-04` — ¿Hay casos con hechos parecidos y resultados opuestos?

- **Conducta:** `responder`.
- **Respuesta de referencia:** Sí hay contrastes útiles. `1210` y `1386`
  contienen vivienda, banca, familia y documentación extranjera, pero el
  conjunto de `1210` apuntó a España y el de `1386` acreditó vida y trabajo en
  Suiza. `1071` y `1226` también contrastan vínculo económico español frente a
  traslado laboral, días y tributación británicos.
- **Casos esperados / contraste:** `1210` ↔ `1386`; `1071` ↔ `1226`.
- **Límite:** “Parecidos” debe explicarse dimensión por dimensión; no es una
  propiedad fija almacenada.

#### 39. `PRE-01` — ¿Qué datos necesitas para buscar casos comparables?

- **Conducta:** `responder`.
- **Respuesta de referencia:** Periodo y países; días y cronología; viviendas y
  uso; cónyuge e hijos y motivo de su localización; empleo, sociedades,
  funciones, rentas y patrimonio por país; consumos y desplazamientos;
  certificados, declaraciones y permisos extranjeros; posible doble residencia
  y CDI; acto recurrido; y si existe sanción.
- **Casos esperados:** Todos, según facetas.
- **Límite:** Pedir solo datos necesarios y evitar identificadores personales
  que no aporten a la búsqueda.

#### 40. `SRC-02` — ¿Puedes mostrar el fragmento exacto y la página?

- **Conducta:** `responder` solo con citas verificadas.
- **Respuesta de referencia:** Sí cuando el pipeline conserva un
  `source_excerpt_verbatim` exacto y su página física. Por ejemplo, `1071`
  contiene en p. 5 el extracto que anula la sanción; `1210`, en p. 8, la
  conclusión sobre residencia; y `1386`, en p. 11, la residencia suiza. Si el
  texto está marcado como fuzzy o pendiente, el chat debe describirlo como
  análisis derivado o abstenerse de citarlo literalmente.
- **Casos esperados:** Los cinco.
- **Laguna:** El corpus verbatim completo aún no existe y hay 17 citas
  pendientes en la muestra; no todo pasaje útil es recuperable hoy.

## Cobertura

| Área | Preguntas | Casos principales |
|---|---:|---|
| Criterios generales | 4 | Los cinco |
| Permanencia | 6 | `1210`, `1226`, `1386` |
| Centro económico | 4 | `1071`, `1210`, `1386` |
| Familia | 4 | `1136`, `1226`, `1386` |
| Vivienda y vida cotidiana | 4 | `1071`, `1210`, `1386` |
| Documentación extranjera | 4 | `1071`, `1210`, `1226`, `1386` |
| CDI | 3 | `1386` |
| Prueba y carga | 4 | `1136`, `1210`, `1386` |
| Sanción | 3 | `1071`, `1210` |
| Comparación, preparación y fuentes | 4 | Los cinco |
| **Total** | **40** | **5 sentencias** |

El banco contiene deliberadamente respuestas `parcial`, `preguntar` y
`abstenerse`. Un sistema que siempre responde no supera la evaluación.

## Hallazgos sobre la estructura actual

### Lo que ya funciona

- Identificadores, país, ejercicios, criterios, resultado global y fuente.
- Pruebas separadas por parte, categoría, criterio, valoración y motivo.
- Resumen y razonamiento identificados como contenido derivado.
- Resultados por cuestión propuestos mediante sidecars.
- Citas exactas con página física y hash del PDF.
- Separación entre citas literales y candidatos pendientes.

### Lo que falta para responder bien

1. **Cuestiones canónicas recuperables.** `legal_issues[]` debe vivir en el
   modelo estructurado, no solo en Markdown o sidecars, con tipo, conclusión,
   resultado, razonamiento y anclajes.
2. **Hechos normalizados.** Hacen falta `facts[]` con categoría, sujeto, país,
   fechas o periodo, valor, estado de controversia y anclaje.
3. **Relación prueba → hecho → cuestión.** Cada `evidence_finding` debe indicar
   quién la aporta, qué pretende probar, qué hecho apoya o contradice, cómo la
   valora el tribunal y por qué.
4. **Secuencia de carga.** Una etiqueta como `AMBOS` no explica quién debía
   probar qué, qué indicios activaron el desplazamiento ni si se cumplió.
5. **Cronología.** `presence_events[]` y `presence_periods[]` deben permitir
   responder sobre días, traslados y hechos fechados sin reconstruirlos desde
   una narración.
6. **Documentos extranjeros.** Tipo, autoridad, jurisdicción, periodo,
   naturaleza fiscal o administrativa, renta mundial, defecto y efecto
   probatorio.
7. **Análisis del CDI.** Separar ley interna y convenio, y representar cada paso
   del desempate con resultado, hechos y cita.
8. **Resultados por cuestión.** Residencia, liquidación, sanción y consecuencias
   no pueden depender de `resultado_final`.
9. **Citas enlazadas a proposiciones.** No basta una bolsa de citas por
   sentencia; cada hecho, valoración y holding necesita sus anclajes.
10. **Revisión granular.** Estado técnico y jurídico por cuestión, hecho,
    valoración y cita, sin que `status: stable` parezca aprobación jurídica.
11. **Texto verbatim por páginas.** Necesario para recuperar pasajes que el
    análisis inicial no preseleccionó y citarlos sin alterar su contenido.
12. **Índice orientado a consulta.** Debe recuperar unidades por cuestión y
    reagrupar por sentencia, con casos de contraste y sin usar el resultado como
    atajo de similitud.

## Decisión para la siguiente iteración

No se recomienda ampliar todavía el perfil actual a 106 sentencias. El siguiente
ciclo debe:

1. definir `residenciafiscal-case/3` a partir de los doce gaps anteriores;
2. actualizar primero una sentencia con el enfoque híbrido;
3. comprobar que las 40 preguntas pueden mapearse a campos y anclajes;
4. regenerar y revisar las cinco;
5. medir recuperación y calidad de respuesta;
6. autorizar las 106 solo si los gates del caso de uso pasan.
