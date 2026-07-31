# El paquete compartido `llm_gateway`

Las llamadas a modelos del analizador legado pasan por
[`neutral-llm-gateway`](https://github.com/jmgb/llm-gateway-python), un paquete
público y neutral fijado a una etiqueta inmutable. Este documento explica qué
quedó de cada lado, qué se demostró antes de borrar la implementación anterior
y qué reglas rigen para tocarlo.

## La regla del corte

Una sola pregunta decide dónde vive cada línea:

> ¿Esto cambiaría si cambiase de **proveedor**, o si cambiase de **producto**?

| Preocupación | Dónde vive |
|---|---|
| Llamar a un SDK y mapear su respuesta | Paquete |
| Reintento, respaldo, contabilidad de intentos | Paquete |
| Recuento de tokens y aritmética de coste | Paquete |
| Recuperar el JSON de una respuesta envuelta en prosa | Paquete |
| Tarifas por modelo | Paquete (catálogo versionado) |
| Prompt, schema del análisis, qué modelo usa cada función | Aplicación |
| Forma del diccionario que espera el pipeline | Aplicación |
| Log de coste, alertas, credenciales | Aplicación, por puertos |

El paquete **no tiene tools, ni ficheros, ni streaming**, y es deliberado: cada
una es una capacidad con su propio modelo de coste y de fallo. Por eso el chat
jurisprudencial B sigue usando Gemini File Search por su cuenta
(`src/gemini_file_search_*.py`): esa capacidad no está ahí y no debe simularse.

Rige además la **regla de los dos consumidores**: nada entra en la API pública
del paquete hasta que dos proyectos distintos lo necesiten. Lo que solo necesita
este proyecto se resuelve con un puerto (`UsageSink`, `AlertSink`, `EventSink`,
`PriceCatalog`), no con un fork ni con un parámetro nuevo.

## Qué hay en este repositorio

| Fichero | Papel |
|---|---|
| `src/ai_service_adapter.py` | Fachada. `gpt_request_for_sentencia` conserva nombre, firma y diccionario de retorno; traduce, ya no llama |
| `src/gateway_setup.py` | Construye el gateway una vez con las credenciales de la aplicación y conecta los puertos |
| `src/gateway_chat_writer.py` | Redactor de la estrategia A del chat, sobre el mismo paquete |

`process_pdf_async` no se tocó, así que el CLI por lotes y la API HTTP siguen
recibiendo exactamente el mismo objeto que antes.

### Estado real del cableado

La migración está cerrada para los dos consumidores compatibles con el
paquete:

- el analizador legado llama a `get_gateway()` desde su fachada;
- la estrategia A del chat inyecta `GatewayChatWriter(get_gateway())` desde el
  CLI comparativo;
- ambos reutilizan la misma instancia de proceso, con `LoggingUsageSink` y
  `LoggingAlertSink`;
- el writer temporal de Interactions y su factoría de cliente se han retirado.

Los tests del composition root comprueban la conexión de cliente y sinks y el
singleton; los tests del CLI comprueban que A recibe esa misma instancia. La
paridad de modelo, tokens, coste y salida permanece protegida por los tests de
la fachada y del puerto del redactor.

Gemini File Search de la estrategia B sigue fuera del paquete por diseño: usa
tools, ficheros e indexación, capacidades que `neutral-llm-gateway` excluye
deliberadamente.

**No hay tabla de precios local.** `src/model_pricing.py` se borró: dos tablas
de tarifas acaban divergiendo, y la que nadie actualiza sigue facturando la del
año pasado sin que nada lo delate. El importe llega con la versión del catálogo
que lo produjo, que es lo que permite auditarlo después.

`detect_provider()` tampoco mantiene ya una tabla completa: delega en el
catálogo del paquete, que es el mismo que usa el registro para elegir adaptador.
Dos tablas de enrutado podrían discrepar, y una discrepancia significa validar
una credencial y llamar a otro proveedor.

Lo único que se añade al catálogo es `LEGACY_MODEL_PREFIXES` (`src/config.py`),
para ids heredados que el paquete no reconoce. Se declaran como **prefijos** y
no como subcadenas porque el registro enruta por prefijo, y `gateway_setup` los
registra en el propio registro: una regla que acertase en `detect_provider()` y
fallase en el registro validaría la credencial de un proveedor y dejaría la
llamada sin adaptador —el lote entero saldría como registros fallidos de
confianza `BAJA` con un error que ni menciona al proveedor. Hay un test
parametrizado sobre la tabla que impide que las dos caras se separen.

## Dos trampas del contrato con OpenAI

Ninguna de las dos es opinable; ambas rompen el analizador si se ignoran.

1. **El *system prompt* viaja como primer mensaje de entrada, no como
   `instructions`.** La Responses API rechaza el modo `json_object` si la
   palabra «json» no aparece en la entrada, e `instructions` no forma parte de
   ella. El texto de una sentencia no contiene esa palabra: solo la menciona el
   prompt de sistema. Lo resuelve el adaptador del paquete desde la v0.5.0.
2. **Los modelos de razonamiento rechazan `temperature=0`.** Se les envía 1, su
   valor por defecto, igual que hacía la implementación anterior con Chat
   Completions.

## Reintento y respaldo del analizador

`src/ai_service_adapter.py` declara la política, y las dos mitades se sostienen
la una a la otra:

| Política | Valor | Por qué |
|---|---|---|
| Reintento | `transient`, 2 intentos | Un lote son 106 sentencias en tandas de diez durante dos o tres horas; un límite de ritmo perdía esa sentencia como registro `BAJA` |
| Presupuesto total | 200 s | Heredado del cliente anterior; acota la llamada entera, reintento incluido |
| Tope por intento | 90 s | Sin él `per_attempt_seconds` cae en el total, y un primer intento colgado 199 s dejaría un segundo para el reintento |
| Respaldo de modelo | desactivado | Si contestara otro modelo, el export declararía el que no respondió y el coste quedaría mal atribuido |

Solo se reintenta lo que puede salir bien la segunda vez. Un error no
transitorio —un esquema inaceptable— fallaría igual y se cobraría dos veces. El
intento fallido que llegó al proveedor se factura y se ve: el gateway lo cuenta
como cualquier otro y el coste agregado degrada a `ESTIMATED`.

Los 90 s salen de latencias medidas, no de una intuición. El corpus se mueve
entre 12,7 s y 38,3 s, y —contra lo que se esperaría— **las sentencias más
grandes son las más rápidas**: `STS 1432/2023` son 61 712 tokens de entrada
resueltos en 14,9 s, porque queda fuera de alcance y el modelo emite 408 tokens.
La latencia la manda la salida, no la entrada, así que el caso lento es una
sentencia de residencia con análisis largo, no un PDF voluminoso. Estas
mediciones preceden a la política Luna + `max`: hay que repetir la muestra antes
de considerar validado el tope de 90 s para esa configuración.

## El coste no miente

Tres reglas heredadas del paquete que ahora se ven en los exports:

- Un uso no informado es `None`, nunca `0`.
- Un coste que no se pudo calcular es `UNAVAILABLE`, nunca `0.00 USD`. «Gratis»
  y «desconocido» son hechos distintos.
- `reasoning_tokens` es un **desglose** de `output_tokens`, nunca un sumando.
  Sumarlos facturaba el razonamiento dos veces; en la Responses API `input` más
  `output` cuadra con el total declarado.

Por eso el JSONL trae dos campos y no uno:

| Campo | Significado |
|---|---|
| `costo_usd` | Importe, o `null` si no se pudo calcular |
| `costo_medicion` | `ACTUAL` medido y tarifado, `ESTIMATED` cota inferior, `UNAVAILABLE` sin importe |

El total de un lote avisa cuando es una cota inferior en vez de presentarse como
el gasto exacto.

## Paridad demostrada antes de borrar

Nada se borró antes de comprobar sobre las mismas entradas que la ruta nueva
producía lo mismo que la anterior.

**Tarifas — 41 de 41 modelos.** Cada entrada de la tabla local borrada se
contrastó con el catálogo del paquete: precio de entrada, precio de salida y
proveedor rotulado idénticos en los 41. Cero divergencias, cero modelos sin
catalogar.

**Aritmética del coste.** Sobre los mismos recuentos de tokens, la tabla local y
el catálogo del paquete dan el mismo importe hasta el microdólar
(`0.040947` en ambos casos).

**Tokens de entrada — idénticos.** `SAN 1071/2025` consumió 10 683 tokens de
entrada por las dos rutas. La disposición de mensajes no cambió.

**Salida — dentro de la varianza del propio modelo.** Tres llamadas sobre la
misma sentencia con el mismo modelo y el mismo esfuerzo de razonamiento:

| Comparación | Campos idénticos |
|---|---|
| Legado #1 vs legado #2 (control) | 15 / 29 |
| Legado #1 vs gateway | 14 / 29 |
| Legado #2 vs gateway | 13 / 29 |

El legado difiere de sí mismo tanto como difiere del gateway: lo que se mide es
el no determinismo del modelo, no un cambio de comportamiento. Los once campos
deterministas —ROJ, ECLI, órgano, fecha, ejercicios, países, CDI invocado,
criterio decisivo, resultado final, confianza— coincidieron exactamente.

**Lote de cinco sentencias, extremo a extremo.** JSONL, los dos CSV y el XLSX
con la columna `costo_medicion`, cinco de cinco con confianza `ALTA` y coste
`ACTUAL`.

## Actualizar la versión del paquete

Cada consumidor fija una referencia inmutable, así que ningún importe ni
ninguna capacidad cambia sin una actualización explícita:

```toml
[tool.uv.sources]
neutral-llm-gateway = { git = "https://github.com/jmgb/llm-gateway-python.git", rev = "208eac03dde785f4b9baab7f2b9b50be39950814" }
```

Subir de versión exige una revisión del `CHANGELOG` del paquete y regenerar
`uv.lock`. **No apuntar nunca a una rama mutable ni a una ruta local en un
commit**: CI ejecuta
`uv sync --locked` sin credenciales contra el repositorio público.

El commit fijado es posterior a `v0.5.0`, pero todavía no tiene una etiqueta
nueva. Se necesita para admitir `none|low|medium|high|xhigh|max`, validar los
esfuerzos por modelo y usar el catálogo de precios del 2026-07-31 (Luna:
0,20 USD/MTok de entrada y 1,20 USD/MTok de salida). El SHA completo mantiene
la instalación reproducible. Cuando el paquete publique una release que
contenga `208eac03`, se sustituirá por esa etiqueta tras comprobar paridad.
