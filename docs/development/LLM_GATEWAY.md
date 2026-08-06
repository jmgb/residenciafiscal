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
| `src/chat_model_policy.py` | Modelo primario, esfuerzo y cadena de fallbacks del chat |
| `src/gateway_setup.py` | Clientes, credenciales, singleton y sinks de uso/alerta |
| `src/llm_gateway_facade.py` | Fachada `gpt_request`: traduce el contrato estable a `LLMRequest` |
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
| A, respuesta estructurada | `CHAT_MODEL` + `CHAT_REASONING_EFFORT` + `CHAT_FALLBACK_MODELS` | Por defecto `gpt-5.6-luna` + `high`; la cadena se entrega al gateway |
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
`StructuredChatAnswerDraft` sigue exigiendo `limits` y `claims` porque un campo
omitido no puede significar «no hay», y el prompt los pide explícitamente. Esa
garantía es jurídica y ningún proveedor la da por nosotros;
`tests/test_chat_answer_contract.py` la comprueba sin red ni coste.

Desde el contrato `structured-claims-v5`, A no devuelve prosa libre: devuelve
afirmaciones atómicas con **sus** `evidence_ids` y una función jurídica
explícita (`party_argument`, `judicial_assessment`, `legal_rule`, `holding` o
`procedural_power`). El texto público se compone después, solo con las claims
que superan el gate léxico contra sus propios extractos. Además, una valoración
judicial debe citar `REASONING`, `HOLDING` o `BURDEN_OF_PROOF`, y un resultado
debe citar `HOLDING`; así una alegación no puede publicarse como conclusión del
tribunal. Una sola afirmación con toda la respuesta enlazada a todas las
fuentes declararía un respaldo que nadie ha comprobado, y por eso el esquema ya
no admite esa forma.

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

La respuesta determinista de A para `pregunta` o `abstención` termina antes de
construir una petición y no consume ningún modelo. En una respuesta sustantiva,
`GatewayChatWriter` construye un único `LLMRequest`; no llama a un SDK ni
mantiene un adaptador local.

El redactor A aplica dos intentos para errores transitorios, presupuesto total
de 200 s y máximo de 90 s por intento. La estrategia pasa
`FallbackPolicy.models_in_order(*CHAT_FALLBACK_MODELS)` al paquete. El gateway
resuelve el modelo primario, agota sus reintentos y, si la respuesta es fallida,
malformada o no cumple el esquema, prueba automáticamente cada fallback en el
orden declarado. Registra los intentos, el modelo que respondió y el coste
acumulado; la aplicación solo publica el resultado estructurado validado.

El paquete no selecciona un fallback por defecto: `LLMRequest` usa
`FallbackPolicy.disabled()`. Su helper `FallbackPolicy.cheaper_than()` deriva
modelos del mismo proveedor de forma deliberada. Como A necesita reducir el
riesgo de caída de un proveedor, la aplicación declara explícitamente una
cadena cross-provider (`gpt-5.6-luna` → `gemini-3.6-flash`) y la fachada rechaza
fallbacks conocidos del mismo proveedor.

La política vigente de A es:

```bash
CHAT_MODEL=gpt-5.6-luna
CHAT_FALLBACK_MODELS=gemini-3.6-flash
```

El modelo y la cadena se pueden cambiar sin tocar el adaptador, pero los
identificadores deben existir en el catálogo instalado del gateway. El smoke
pagado de A debe fijar explícitamente los mismos valores para que la prueba sea
reproducible:

```bash
uv run python src/gemini_file_search_cli.py compare \
  "¿Qué tiene en cuenta Hacienda para demostrar la residencia en España?" \
  --only a --chat-model gpt-5.6-luna \
  --chat-fallback-model gemini-3.6-flash --confirm-paid
```

El catálogo conoce los IDs Llama 4 —la `0.10.0` los marca *deprecated* y los
mantiene enrutables—, pero la API de Groq ya no los ofrece en el entorno
validado y el catálogo no declara `reasoning_efforts` ni entrada de ficheros
inline para ellos. Por eso no se usan como configuración de A.

La V1 Netlify-only sigue siendo un runtime anterior: sus adaptadores TypeScript
son directos porque aún no se ha completado el corte de tráfico a FastAPI. No
se amplían ni se usan desde la ruta Python canónica; el objetivo de la
migración es que A quede servido únicamente por este gateway.

La fachada Python equivalente a `gpt_request` vive en
`src/llm_gateway_facade.py`. Conserva un punto de entrada funcional con modelo,
prompt de sistema, mensaje de usuario, `request_id`, `source` y resultado
`LLMResult`; no crea clientes ni aplana el resultado por su cuenta. La
aplicación puede adaptar ese resultado al contrato de dominio después, mientras
que uso, coste y alertas siguen centralizados en los sinks del gateway.

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

El paquete se instala desde PyPI con una versión exacta:

```toml
dependencies = ["neutral-llm-gateway[gemini,groq,openai,openrouter]==0.12.0"]
```

Cada tramo hasta aquí aporta algo que este proyecto da por hecho: la
`0.7.0` normaliza el esquema estricto y declara `supports_temperature` —por
debajo, este proyecto vuelve a necesitar los parches retirados—, la `0.8.0`
hace que `Execution.model_used` respete el id que reporta el proveedor, que es
el que el comparador publica como modelo de la respuesta, la `0.9.0` hace que
un `response_schema` llegue a los proveedores que no lo imponen, y la `0.10.0`
retira las conjeturas por familia de proveedor y por namespace del enrutado de
fallback: un modelo desconocido ya no se adivina, exige entrada explícita en el
catálogo. La cadena vigente (`gpt-5.6-luna` → `gemini-3.6-flash`) está
catalogada, así que ese cambio no la altera.

La `0.10.0` mueve además el catálogo compartido a `2026-08-04.5` sin tocar las
tarifas de los tres modelos del chat, y marca como *deprecated* —sin dejar de
enrutarlas— identidades que este proyecto no usa (Gemini antiguos, DeepSeek,
Llama de Groq y GPT-5.1/5.2). Lo que sí obliga es a regenerar
`frontend/netlify/functions/chat/pricing.generated.json`, que publica esa
versión de catálogo a la Function TypeScript. La `0.10.1` es solo determinismo
de la CI del paquete.

Las `0.11.0` y `0.12.0` añaden contratos que este proyecto no usa —imagen,
vídeo y function calling neutral para OpenAI y Groq— y mueven los builders de
catálogo a `llm_gateway.catalogs` sin tocar `lookup_model` ni `CATALOG_VERSION`,
que es lo único que el chat importa. Lo que sí obligan es a regenerar de nuevo
`pricing.generated.json`: el catálogo pasa a `2026-08-06.1` por los modelos de
vídeo de Replicate, sin cambiar las tarifas de los tres modelos del chat.

Ese último tramo es el aviso de esta sección cumpliéndose. Hasta la `0.9.0` los
adaptadores de Groq y OpenRouter pedían `{"type": "json_object"}` y descartaban
el esquema, así que el modelo respondía JSON válido con claves inventadas, el
gateway lo rechazaba, cobraba el intento y contestaba la cascada: **cada llamada
estructurada la servía el modelo de respaldo, a su precio**. El resultado era
correcto y el único síntoma estaba en la factura. La misma versión evita que
`ResponseFormat.JSON_OBJECT` falle con HTTP 400 en Groq, que rechaza ese modo si
los mensajes no citan «json».

La configuración histórica del chat usa Gemini y OpenAI, que sí imponen
esquema. A puede enrutar también a Groq u OpenRouter si el catálogo y sus
credenciales están configurados; en esos proveedores el gateway valida el JSON
después de la respuesta y contabiliza cada intento, incluido el que provoque un
fallback.

La versión es exacta por decisión explícita, como recomienda el propio paquete:
una versión nueva con cambios de contabilidad de coste —exactamente lo que trajo
la `0.9.0`— no debe entrar sola al regenerar el lock. Subir de versión es por
tanto un cambio deliberado: se edita el pin de `pyproject.toml`, se corre
`uv lock`, se lee el `CHANGELOG` del paquete —que señala explícitamente lo que
afecta al coste—, se regenera el catálogo de precios de la Function y se ejecuta
`make fast-check`. `uv.lock` clava la versión resuelta y CI ejecuta
`uv sync --locked`, así que nada se mueve sin ese paso. Nunca se fija una rama
mutable ni una ruta local.
