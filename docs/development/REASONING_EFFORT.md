# Reasoning effort del chat

`reasoning_effort` regula el presupuesto de razonamiento de la respuesta
conversacional. No es un parámetro del pipeline de sentencias: el corpus se
prepara mediante Python + agente y no llama a OpenAI.

## Política vigente

La única fuente de verdad es `src/chat_model_policy.py`:

| Campo | Valor |
|---|---|
| Modelo del chat | `gpt-5.6-luna` |
| Esfuerzo | `high` |
| Valores admitidos | Derivados de `reasoning_efforts` en el catálogo del gateway |

`GET /config` publica `chat_model`, `chat_reasoning_effort` y
`chat_reasoning_efforts_permitidos`. Los valores actuales son `none`, `low`,
`medium`, `high`, `xhigh` y `max`.

## Qué significa `high`

Es una decisión de producto que prioriza la calidad de la respuesta jurídica
manteniendo una latencia compatible con el chat. Es el esfuerzo que viaja por
defecto en A junto a `gpt-5.6-luna`.
No garantiza por sí sola mayor precisión. Puede aumentar razonamiento, latencia
y coste, por lo que cada respuesta debe mostrar y registrar:

- modelo efectivo;
- esfuerzo enviado explícitamente al proveedor, o `NULL` si no se configuró;
- tokens de entrada y salida;
- coste marginal en USD;
- tipo de medición;
- latencia.

La evaluación pendiente debe comparar respuestas del chat sobre el mismo banco
de preguntas y la misma evidencia recuperada. No debe procesar sentencias ni
enviar PDF al modelo.

## Ámbito

- El comparador F0 puede usar Gemini para mantener A y B comparables; esa
  configuración experimental no redefine la política productiva.
- La preparación de casos v3, verbatim, perfiles OKF e índices no conoce este
  parámetro.
- `tests/test_llm_architecture_boundary.py` impide volver a conectar el gateway
  al pipeline offline.
