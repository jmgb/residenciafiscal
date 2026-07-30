# Reasoning effort

El parámetro `reasoning_effort` regula cuánto "piensa" un modelo GPT-5 antes de
responder. En este pipeline es la palanca principal del compromiso entre
**precisión de la extracción**, **tiempo** y **coste**.

## Dónde se configura

Hay tres niveles, de menor a mayor prioridad:

| Nivel | Dónde | Alcance |
|-------|-------|---------|
| Por defecto | `REASONING_EFFORT = "medium"` en `src/config.py` | Todo el proyecto |
| Por ejecución | `make run EFFORT=high` → `--reasoning-effort high` | Un run del CLI |
| Por petición | campo `reasoning_effort` del formulario en `POST /analizar` | Una llamada a la API |

```bash
make run EFFORT=high                                    # vía Makefile
uv run python src/residenciafiscal.py --reasoning-effort low # CLI directo

curl -X POST -F "archivo=@sentencias/SAN_1226_2021.pdf" \
     -F "reasoning_effort=high" http://127.0.0.1:8010/analizar
```

La API solo acepta `low`, `medium` o `high` (validado en `src/api/main.py`); un valor
distinto devuelve 400. El valor vigente por defecto se consulta en
`GET /config` → `reasoning_effort_default`.

## A qué modelos se aplica

El parámetro **solo se envía a modelos GPT-5**. En `src/residenciafiscal.py`:

```python
reasoning_effort=reasoning_effort if "gpt-5" in ai_model else None,
```

Para cualquier otro modelo (GPT-4, Gemini, Groq, OpenRouter) se omite
silenciosamente, así que fijar `EFFORT=high` con un modelo no-GPT-5 no cambia
nada ni da error.

Ojo con las sentencias clave: los 23 ficheros de `sentencias/sentencias_CLAVE.txt`
fuerzan el modelo premium (`SENTENCIA_CLAVE_MODEL`) al margen de `--model`, pero
**sí respetan** el `reasoning_effort` que le pases.

## Niveles

| Nivel | Coste relativo | Cuándo usarlo |
|-------|----------------|---------------|
| `low` | Base | Prototipado, validar que el pipeline corre de punta a punta, sentencias cortas y de criterio único |
| `medium` | ~1,5× | **Por defecto.** Equilibrio razonable para el grueso del corpus |
| `high` | ~2–4× | Sentencias largas, aplicación de CDI con tie-breaker, casos con muchas pruebas cruzadas |

Los multiplicadores son órdenes de magnitud, no medidas: el sobrecoste llega por
los *reasoning tokens*, que se facturan como salida y varían mucho según el
documento. Para cifras reales de tu corpus, usa el comparador.

## Comparador

`tests/test_reasoning_effort_comparison.py` procesa **el mismo PDF** con varias
configuraciones y tabula lo que cuesta cada una. Es un script manual, **no entra
en `pytest`** y **gasta dinero real**.

```bash
uv run python tests/test_reasoning_effort_comparison.py
uv run python tests/test_reasoning_effort_comparison.py --pdf sentencias/STS_4220_2024.pdf
```

Las configuraciones viven en `TEST_CONFIGURATIONS`, al principio del script.
Hoy son tres, de más barata a más cara:

```python
TEST_CONFIGURATIONS = [
    ("gpt-5.6-luna", "medium"),
    ("gpt-5.6-luna", "high"),
    ("gpt-5.2-2025-12-11", "medium"),
]
```

Edita esa lista para añadir o quitar combinaciones. Cada entrada es una llamada
completa al modelo sobre el PDF entero: el coste crece de forma lineal con el
número de filas.

### Qué mide

Vuelca a consola y a `test_results/reasoning_effort_comparison_<timestamp>.{csv,json}`
(directorio ignorado por git):

- **Coste y rendimiento**: `time_seconds` y `cost_usd`.
- **Cobertura de la extracción**: `criterios_detectados`, `pruebas_aeat` y
  `pruebas_contribuyente`.
- **Resultado y calidad declarada**: `confianza_extraccion` (ALTA / MEDIA /
  BAJA), `resultado_final`, `es_caso_residencia_irpf` y `se_invoca_CDI`.

No hay conteo de tokens: `process_pdf_async()` descarta `tokens_in` y
`tokens_out` antes de escribir el JSONL (`src/residenciafiscal.py`), así que el
comparador no puede leerlos. Si te hace falta el desglose por tokens, hay que
dejar de descartarlos primero.

### Cómo leerlo

La señal útil no es el coste aislado, sino **cuánto compras con él**:

- Si al subir de `medium` a `high` no cambian ni los criterios detectados ni la
  confianza, el gasto extra no aporta: quédate en `medium`.
- Si `confianza_extraccion` sube de BAJA a ALTA, o aparecen criterios que
  `medium` no veía, `high` está pagando por sí mismo en ese tipo de sentencia.
- Si `confianza_extraccion` sale BAJA en **todas** las configuraciones, el
  problema no es el esfuerzo: comprueba que el PDF tiene capa de texto, porque
  el pipeline no hace OCR.

Un patrón razonable en producción es `medium` para todo el corpus y `high` solo
para el subconjunto que lo justifique, mediante `make run-list`.

## Problemas frecuentes

| Síntoma | Causa probable |
|---------|----------------|
| El esfuerzo no cambia nada | El modelo no es GPT-5; el parámetro se omite por diseño |
| `cost_usd = 0` en toda la tabla | El modelo no está en `src/model_pricing.py`; añade sus precios |
| Timeouts con `high` | Baja a `medium`, o reduce `BATCH_SIZE` en `src/config.py` |
| 400 en `/analizar` | La API solo admite `low`, `medium` o `high`; `minimal` no está permitido |

## Referencias

- [OpenAI — Reasoning models](https://platform.openai.com/docs/guides/reasoning)
- `src/config.py` — valores por defecto
- `tests/README.md` — inventario de tests y coste de cada uno
