# El gateway LLM pertenece al chat

[`neutral-llm-gateway`](https://github.com/jmgb/llm-gateway-python) es la
infraestructura de inferencia del chat. No participa en la preparación,
estructuración ni validación de sentencias.

## Frontera obligatoria

```text
Preparación offline del corpus
PDF → Python → propuesta del agente → gates Python → caso v3
                                                    sin gateway

Respuesta online
pregunta → recuperación v3 → gateway LLM → respuesta con citas y coste
```

Consecuencias:

- no existe `gpt_request_for_sentencia`;
- no existe `POST /analizar`;
- los módulos `jurisprudence_*` no importan `llm_gateway`, `gateway_setup` ni
  `chat_model_policy`;
- cualquier llamada de pago corresponde a una pregunta del chat o a un
  experimento conversacional confirmado expresamente;
- los PDF originales y los verbatim nunca se envían al gateway para construir
  el corpus.

`tests/test_llm_architecture_boundary.py` convierte estas reglas en un gate
ejecutable.

## Reparto de responsabilidades

| Pieza | Responsabilidad |
|---|---|
| `src/chat_model_policy.py` | Modelo y esfuerzo del chat: Luna + `high` |
| `src/gateway_setup.py` | Clientes, credenciales, singleton y sinks de uso/alerta |
| `src/gateway_chat_writer.py` | Adaptador del redactor estructurado del chat |
| `src/current_structured_strategy.py` | Recuperación y respuesta A del comparador |
| `src/google_genai_file_search.py` | File Search B, fuera del paquete porque usa ficheros/tools |

Lo que cambia con el proveedor pertenece al paquete neutral. Lo que cambia con
el producto —prompt jurídico, recuperación, citas, abstención, logs y límites—
permanece en esta aplicación.

## Costes y observabilidad

No hay tabla de precios local. Las tarifas y `CATALOG_VERSION` proceden del
paquete; el proyecto conserva tokens, modelo efectivo y tipo de medición:

- `ACTUAL`: uso completo informado por el proveedor;
- `ESTIMATED`: importe parcial o intento fallido facturable;
- `UNAVAILABLE`: no existe información suficiente para calcularlo.

Un coste desconocido nunca se convierte en cero. Los logs no incluyen pregunta,
respuesta ni texto judicial.

## Cada estrategia con su modelo

A y B ya no comparten modelo, y no es una preferencia sino una restricción de
capacidad: **File Search es una capacidad de Gemini**, así que B solo puede
correr sobre `SUPPORTED_FILE_SEARCH_MODELS` y `GeminiFileSearchResponder`
rechaza cualquier otro. A no usa File Search, y atarla a esa lista era lo que
dejaba la política de `chat_model_policy` sin llegar a ninguna llamada.

| Estrategia | Modelo | De dónde sale |
|---|---|---|
| A, respuesta estructurada | `chat_model_policy.CHAT_MODEL` + `CHAT_REASONING_EFFORT` | Política del chat |
| B, File Search | `--model`, por defecto `gemini-3.5-flash-lite` | Allowlist de File Search |

El esfuerzo de razonamiento viaja con la petición de A. Sin él, la petición
salía con el valor por defecto del proveedor y declararlo en la política no
habría cambiado nada.

El importe deja de exigir un modelo de File Search: `calculate_request_cost`
tarifa cualquier modelo catalogado y `calculate_gemini_file_search_cost`
conserva la restricción de B. Antes, una A fuera de esa lista moría con
`modelo File Search sin tarifa` **después** de haber pagado la llamada.

## Lo que exige la Responses API y Gemini perdonaba

Mover A a Luna destapó tres cosas que Gemini aceptaba y OpenAI no. Ninguna la
detecta la suite por sí sola: los tests del chat usan dobles de proveedor, que
admiten cualquier petición.

**1. Modo estricto: `required` con todas las propiedades.** Un campo con valor
por defecto en Pydantic no llega a `required`, y OpenAI rechaza el esquema
entero con `invalid_json_schema` —`Missing 'limits'`—, no el campo. Por eso
`StructuredChatAnswerDraft` redeclara `limits` y `evidence_ids` sin valor por
defecto, y el prompt de A los pide explícitamente: exigir en el esquema lo que
las instrucciones no mencionan traslada al modelo un requisito que nadie le
comunicó. Hay una ventaja de fondo, no solo de compatibilidad: un `limits`
ausente se convertía en tupla vacía, y eso confunde «no hay salvedades» con «el
modelo no se pronunció», que en una respuesta jurídica no es lo mismo.
`tests/test_chat_answer_strict_schema.py` lo comprueba sin red ni coste.

La clase base `ChatAnswerDraft` no cambia. La usa B contra File Search, que no
impone modo estricto, y endurecerla convertiría en fallo respuestas hoy válidas
en un camino que ya alimentó artefactos de revisión.

**2. `temperature=0` no existe para un modelo de razonamiento.** La API
responde `Unsupported parameter`. `ChatWriterRequest` la pide a 0 por defecto
—correcto para una tarea jurídica, y aceptado por Gemini—, así que sin el
ajuste de `gateway_chat_writer` **todas** las respuestas de A fallarían. La
condición se deriva del catálogo (`provider == "openai"` y `reasoning_efforts`
declarados) en vez de una lista de nombres, y se acota a OpenAI porque Gemini 3
también declara esfuerzos y sí admite temperatura: quitársela cambiaría el
determinismo y con él las cifras ya medidas.

**3. El coste asumía que toda generación era de File Search.** Resuelto al
separar tarifar de permitir, según la tabla de la sección anterior.

## Reintento y fallback

El redactor A aplica dos intentos para errores transitorios, presupuesto total
de 200 s y máximo de 90 s por intento. El fallback de modelo está desactivado:
si respondiera un modelo distinto, el coste y la comparación quedarían mal
atribuidos.

La cifra sigue al esfuerzo declarado, porque **la latencia la manda el
razonamiento y no el tamaño de la pregunta**. Las mismas dos preguntas del
corpus de cinco, medidas dos veces con cada esfuerzo:

| Esfuerzo | Latencia | Tokens de salida | Coste por respuesta |
|---|---|---|---|
| `max` | 81,0 / 81,7 / 93,4 / 95,9 s | 7 854 – 9 077 | $0.0113 – $0.0128 |
| `high` | 16,3 / 17,8 / 22,2 / 30,3 s | 1 617 – 3 432 | $0.0038 – $0.0060 |

`max` costaba entre tres y cuatro veces más tiempo y dinero por respuesta, y
nadie había medido qué calidad compraba a cambio. En un chat que **no puede
transmitir tokens según se generan** —el paquete excluye el streaming por
diseño— esa diferencia es pantalla en blanco pagada a precio de salida.

Con `max` dos de las cuatro respuestas superaban el tope de 90 s, y la misma
pregunta caía a un lado y al otro según la ejecución: un corte intermitente que
el reintento no salvaba, porque gastados 90 s de los 200 s de presupuesto el
segundo intento se cortaba igual y la respuesta acababa en fallo pagado dos
veces. Con `high` los 90 s son 3× el peor caso.

Si se cambia el modelo o el esfuerzo, hay que repetir la medición: es una
latencia dominada por la salida, no por el tamaño de la pregunta.

## Versión fijada

El proyecto usa una referencia Git inmutable:

```toml
[tool.uv.sources]
neutral-llm-gateway = { git = "https://github.com/jmgb/llm-gateway-python.git", rev = "208eac03dde785f4b9baab7f2b9b50be39950814" }
```

Ese commit, posterior a `v0.5.0`, añade esfuerzos
`none|low|medium|high|xhigh|max`, validación por modelo y catálogo
`2026-07-31`. Cuando exista una release que lo contenga, puede sustituirse el
SHA por su etiqueta tras revisar `CHANGELOG`, regenerar `uv.lock` y ejecutar
`make fast-check`. Nunca se fija una rama mutable ni una ruta local.
