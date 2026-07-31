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
| `src/chat_model_policy.py` | Modelo y esfuerzo del chat: Luna + `max` |
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

## Reintento y fallback

El redactor A aplica dos intentos para errores transitorios, presupuesto total
de 200 s y máximo de 90 s por intento. El fallback de modelo está desactivado:
si respondiera un modelo distinto, el coste y la comparación quedarían mal
atribuidos.

Estas cifras proceden del experimento F0.2. Deben volver a medirse antes de
activar el chat productivo con Luna + `max`; esa medición evalúa respuestas a
preguntas, nunca análisis de PDF.

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
