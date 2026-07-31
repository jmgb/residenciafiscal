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
| `frontend/netlify/functions/chat/provider-adapters.ts` | Adaptadores Node mínimos de la V1 Netlify-only |

Lo que cambia con el proveedor pertenece al paquete neutral. Lo que cambia con
el producto —prompt jurídico, recuperación, citas, abstención, logs y límites—
permanece en esta aplicación.

## Costes y observabilidad

No hay una tabla de precios local mantenida a mano. La Function necesita un
artefacto JSON para Node, pero se genera desde las tarifas y `CATALOG_VERSION`
del paquete y un test exige igualdad byte a byte. El proyecto conserva tokens,
modelo efectivo y tipo de medición:

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

El importe de A ya no se calcula aquí: lo mide el gateway y viaja en
`ChatWriterResult.cost`. Antes, A recomponía la cuenta con las mismas
tarifas y moría con `modelo File Search sin tarifa` si el modelo no estaba
en la lista de B, **después** de haber pagado la llamada.

## Lo que resuelve el paquete y aquí no se reimplementa

Mover A a Luna destapó dos incompatibilidades que Gemini perdonaba y OpenAI no.
Se parchearon aquí, y la `v0.7.0` las resolvió en origen. **Los parches locales
se retiraron**: mantener dos sitios decidiendo lo mismo garantiza que uno de
los dos envejezca sin que nadie lo note.

| Problema | Quién lo resuelve |
|---|---|
| El modo estricto exige `required` completo y `additionalProperties: false` | `providers/strict_schema.py` reescribe el esquema antes de enviarlo |
| Un modelo de razonamiento rechaza `temperature` | `ModelInfo.supports_temperature`; el gateway descarta la opción antes del intento |
| Un modelo no catalogado no tiene tarifa | El catálogo versionado del paquete |
| Qué proveedor sirve cada id | `resolve_provider` y el registro; aquí no hay tabla de enrutado |

Lo único que se conserva de aquellos parches es lo que **no** es del proveedor:
`StructuredChatAnswerDraft` sigue exigiendo `limits` y `evidence_ids` porque un
campo omitido no puede significar «no hay», y el prompt los pide explícitamente.
Esa garantía es jurídica y ningún proveedor la da por nosotros;
`tests/test_chat_answer_contract.py` la comprueba sin red ni coste.

La clase base `ChatAnswerDraft` no cambia: la usa B contra File Search, y
endurecerla convertiría en fallo respuestas hoy válidas en un camino que ya
alimentó artefactos de revisión.

El coste de A también se delega: el puerto del redactor transporta el `Cost`
que midió el gateway en vez de que la estrategia rehaga la cuenta. Con ello
hereda la degradación a `ESTIMATED` cuando un intento facturado no tiene
importe conocido, que la cuenta local no sabía reproducir. B sigue calculando
el suyo: mide sobre la Interactions API, fuera del paquete, y factura tokens
de documento recuperado que ninguna llamada del gateway produce.

## Reintento y fallback

La V1 Netlify-only no puede importar un paquete Python. Sus dos adaptadores Node
son una excepción de runtime deliberadamente estrecha: solo traducen el contrato
HTTP/SDK; prompts, recuperación, citas, estados y presupuesto siguen siendo del
producto. No constituyen una segunda API pública compartida y no deben crecer
con routing, fallback ni catálogos. Si aparece un segundo consumidor Node, rige
la regla de los dos consumidores y ese transporte deberá extraerse a un paquete
neutral; si vuelven a necesitarse llamadas largas, la arquitectura FastAPI usa
ya `neutral-llm-gateway` sin duplicación.

En la V1 ambos SDK se ejecutan una sola vez, sin reintentos ni fallback, bajo la
misma señal de cancelación de 52 s. Lo siguiente describe el prototipo Python
conservado:

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
| `high` | 11,1 – 36,7 s (ocho medidas) | 1 095 – 3 432 | $0.0032 – $0.0060 |

`max` costaba entre tres y cuatro veces más tiempo y dinero por respuesta, y
nadie había medido qué calidad compraba a cambio. En un chat que **no puede
transmitir tokens según se generan** —el paquete excluye el streaming por
diseño— esa diferencia es pantalla en blanco pagada a precio de salida.

Con `max` dos de las cuatro respuestas superaban el tope de 90 s, y la misma
pregunta caía a un lado y al otro según la ejecución: un corte intermitente que
el reintento no salvaba, porque gastados 90 s de los 200 s de presupuesto el
segundo intento se cortaba igual y la respuesta acababa en fallo pagado dos
veces. Con `high` los 90 s son 2,4× el peor caso.

Si se cambia el modelo o el esfuerzo, hay que repetir la medición: es una
latencia dominada por la salida, no por el tamaño de la pregunta.

## Versión

El paquete se instala desde PyPI con un mínimo y sin techo:

```toml
dependencies = ["neutral-llm-gateway[gemini,groq,openai,openrouter]>=0.8.0"]
```

El mínimo es `0.8.0`, y cada tramo aporta algo que aquí se da por hecho: la
`0.7.0` normaliza el esquema estricto y declara `supports_temperature` —por
debajo, este proyecto vuelve a necesitar los parches retirados—, y la `0.8.0`
hace que `Execution.model_used` respete el id que reporta el proveedor, que es
el que el comparador publica como modelo de la respuesta.

No hay techo por decisión explícita. El contrapeso conviene tenerlo presente:
el propio paquete recomienda fijar una versión exacta, y sin máximo una futura
`0.8.0` con cambios de contabilidad de coste entraría al regenerar el lock.
`uv.lock` sigue clavando la versión resuelta y CI ejecuta `uv sync --locked`, así
que el cambio solo se materializa cuando alguien corre `uv lock` — momento en el
que conviene leer el `CHANGELOG`, que señala explícitamente lo que afecta al
coste, y ejecutar `make fast-check`. Nunca se fija una rama mutable ni una ruta
local.
