# Testing Suite: Reasoning Effort Comparison

Documentación completa sobre el sistema de pruebas para comparar diferentes niveles de `reasoning_effort` en modelos GPT-5.

## 📚 Documentación Disponible

### 1. **Guía Detallada de Pruebas** → `TEST_REASONING_EFFORT_GUIDE.md`

Documento exhaustivo (5000+ palabras) que incluye:

#### Contenido Principal:
- 📋 **Descripción General**: Las 8 configuraciones y qué se mide
- 🎯 **Métricas Capturadas**: Coste, tokens, tiempo, calidad (20+ métricas específicas)
- 📊 **Estructura de Datos**: Detalle de cada tipo de prueba:
  - `Pruebas_AEAT` / `Pruebas_contribuyente` (7 campos)
  - `Pruebas_rechazadas_clave` (5 campos + análisis de impacto)
  - `Prueba_o_bala_de_plata` (prueba decisiva, 5 campos + coherencia)
  - Indicadores de sesgo y consistencia

#### Análisis Práctico:
- 🎯 **Impacto de reasoning_effort**: 3 escenarios detallados mostrando diferencias reales
- 📈 **Métrica de Densidad de Información**: Algoritmo para cuantificar calidad
- 💡 **Interpretación de Resultados**: Cómo leer tablas comparativas
- 🛠️ **Casos de Uso**: Cuándo usar cada configuración (research, producción, prototipado)

#### Ejemplos:
- ✅ Ejemplo 1: Comparación de criterios detectados
- ✅ Ejemplo 2: Diferencias en clasificación de pruebas
- 📉 Gráficas interpretables
- 🔍 Troubleshooting común

---

## 🚀 Cómo Usar el Sistema

### Paso 1: Ejecutar Pruebas

```bash
# Con PDF automático (primera disponible)
python test_reasoning_effort_comparison.py --max-pages 10

# Con PDF específico
python test_reasoning_effort_comparison.py \
    --pdf sentencias/STS_371_2020.pdf \
    --max-pages 15

# Sin límites
python test_reasoning_effort_comparison.py \
    --pdf sentencias/STS_371_2020.pdf
```

**Duración estimada:** 3-5 minutos (8 configuraciones × ~30-50s cada una)

**Salida:**
- ✅ Tabla comparativa en consola
- ✅ `test_results/reasoning_effort_comparison_YYYYMMDD_HHMMSS.csv`
- ✅ `test_results/reasoning_effort_comparison_YYYYMMDD_HHMMSS.json`

---

### Paso 2: Analizar Resultados

**En la tabla CSV busca:**

| Métrica | Buscar | Acción |
|---------|--------|--------|
| **cost_usd** | Columna mínima | Esa config es más económica |
| **time_seconds** | Columna mínima | Esa config es más rápida |
| **confianza_extraccion** | "ALTA" | Mejor calidad |
| **criterios_detectados** | 4-5 | Config detectó bien |
| **tokens_in/out** | Proporción | Impacto en presupuesto |

**En el JSON busca:**

```python
import json

with open("reasoning_effort_comparison_*.json") as f:
    results = json.load(f)

# Analizar
for config in results:
    print(f"{config['model']} + {config['reasoning_effort']}")
    print(f"  Cost: ${config['cost_usd']:.4f}")
    print(f"  Time: {config['time_seconds']}s")
    print(f"  Quality: {config['confianza_extraccion']}")
    print()
```

---

### Paso 3: Tomar Decisión

**Matriz de decisión:**

```
¿Cuál es tu prioridad?

┌─────────────────────────────────────────────────────────┐
│ MÁXIMA CALIDAD (research, análisis académico)           │
│ → GPT-5 + reasoning_effort="high"                       │
│ Costo: $0.40-0.50 por sentencia, 45-50s                │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ BALANCE COSTO-CALIDAD (producción normal)              │
│ → GPT-5 + reasoning_effort="medium"                     │
│   O GPT-5-mini + reasoning_effort="high"                │
│ Costo: $0.09-0.39 por sentencia, 17-44s                │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ MÍNIMO COSTE (prototipado, exploración)                │
│ → GPT-5-mini + reasoning_effort="minimal"               │
│ Costo: $0.05 por sentencia, 13s                        │
│ ⚠️ Requiere validación manual posterior                 │
└─────────────────────────────────────────────────────────┘
```

---

### Paso 4: Implementar Configuración

#### Opción A: Cambio Global (config.py)

```python
# Editar: config.py
REASONING_EFFORT = "medium"  # Cambiar aquí
DEFAULT_MODEL = GPT_5  # Opcional: cambiar modelo también
```

Luego:
```bash
python residenciafiscal.py --input ./sentencias --output ./output
```

---

#### Opción B: Por Línea de Comandos (CLI)

```bash
python residenciafiscal.py \
    --input ./sentencias \
    --output ./output \
    --model gpt-5.2-2025-12-11 \
    --reasoning-effort high \
    --max-files 100
```

---

## 📊 Métricas Explicadas Brevemente

### Performance & Costo
- **time_seconds**: Cuánto tardó (mínimo esperado: 13s, máximo: 50s)
- **cost_usd**: Cuánto costó procesar UNA sentencia
- **tokens_in/out**: Consumo de tokens (importante para presupuesto)

### Calidad de Extracción
- **confianza_extraccion**: ALTA/MEDIA/BAJA
  - ALTA: Apta para análisis automatizado confiable
  - MEDIA: Requiere revisión manual
  - BAJA: Solo para exploración

- **criterios_detectados**: Cantidad de criterios de residencia encontrados
  - Rango esperado: 1-5
  - Menos de 1: bajo esfuerzo
  - Más de 5: posible sobre-interpretación

- **resultado_final**: GANA_AEAT, GANA_CONTRIBUYENTE, PARCIAL, etc.
  - Valida coherencia con pruebas aceptadas/rechazadas

### Pruebas Específicas
- **pruebas_aeat / pruebas_contribuyente**: Cantidad y detalles
- **pruebas_rechazadas_clave**: Pruebas que hubieran cambiado el resultado
- **prueba_o_bala_de_plata**: La prueba decisiva (más importante)

---

## 💡 Tips Prácticos

### Tip 1: Comparar Configuraciones Rápido

```bash
# Generar comparación de costos
python -c "
import json
with open('reasoning_effort_comparison_*.json') as f:
    data = json.load(f)
    for cfg in data:
        print(f\"{cfg['model']:6} + {cfg['reasoning_effort']:8} = \${cfg['cost_usd']:.4f}\")
" | sort -k4 -n
```

**Output:**
```
5-mini + minimal   = $0.0521
5-mini + low       = $0.0712
5      + minimal   = $0.2341
5      + low       = $0.3124
... (y así)
```

---

### Tip 2: Detectar Problemas de Calidad

```bash
# Buscar "NO CONSTA" excesivo
grep -c "NO CONSTA" analisis.jsonl

# Si cuenta > 10% total de registros → considerar "high"
```

---

### Tip 3: Validar Coherencia

```python
import json

with open("analisis.jsonl") as f:
    for line in f:
        data = json.loads(line)

        # Validar que bala de plata coincide con ganador
        if data["resultado_final"] == "GANA_AEAT":
            assert data["Prueba_o_bala_de_plata"]["parte"] == "AEAT"

        # Validar que hay pruebas del ganador
        if data["resultado_final"] == "GANA_AEAT":
            assert len(data["Pruebas_AEAT"]) > 0
```

---

## 🔗 Referencias Cruzadas

**Archivos relacionados:**

- `residenciafiscal.py` - Pipeline principal (modificado para aceptar `--reasoning-effort`)
- `ai_service_adapter.py` - Integración con OpenAI (gestiona parámetros)
- `config.py` - Configuración central (REASONING_EFFORT)
- `prompt.py` - Definición del análisis (qué campos extraer)
- `test_reasoning_effort_comparison.py` - Script de pruebas

**Cambios implementados:**

```
✅ process_pdf_async()  - Acepta parámetro reasoning_effort
✅ main_async()         - Propaga reasoning_effort a process_pdf_async()
✅ main()               - CLI argument --reasoning-effort
✅ test script          - Ejecuta 8 configuraciones automáticamente
```

---

## 📞 Soporte

Si encuentras problemas:

1. **Lee** `TEST_REASONING_EFFORT_GUIDE.md` (secciones "Troubleshooting")
2. **Verifica** que `OPENAI_API_KEY` está configurada
3. **Intenta** primero con `--max-pages 5` (test case simple)
4. **Revisar** logs: `tail -50 test_reasoning_effort_comparison.py`

---

## 📋 Checklist de Uso

- [ ] He leído `TEST_REASONING_EFFORT_GUIDE.md`
- [ ] Tengo un PDF válido en `sentencias/`
- [ ] He configurado `OPENAI_API_KEY`
- [ ] He ejecutado `python test_reasoning_effort_comparison.py`
- [ ] He analizado los resultados en CSV/JSON
- [ ] He elegido configuración basada en mis necesidades
- [ ] He actualizado `config.py` o uso CLI `--reasoning-effort`
- [ ] He validado que la extracción es coherente

---

## 🎯 Próximos Pasos

**Después de las pruebas:**

1. **Usar configuración elegida** en pipeline normal:
   ```bash
   python residenciafiscal.py --input ./sentencias --output ./output --reasoning-effort medium
   ```

2. **Monitorear resultados** en producción:
   ```bash
   # Verificar confianza y costo
   tail analisis.jsonl | jq '.confianza_extraccion, .costo_usd'
   ```

3. **Iterar** si es necesario:
   - Baja confianza → cambiar a "high"
   - Costo muy alto → cambiar a "low" o GPT-5-mini
   - Mucho "NO CONSTA" → cambiar a "high"

---

## 📈 Resultados Esperados

Cuando ejecutes las pruebas:

```
[1/8] Testing: gpt-5.2-2025-12-11 with reasoning_effort=high
  ✓ Completed in 48.32s
  Tokens: 12453 in, 3847 out
  Cost: $0.4521
  Confidence: ALTA
  Criteria detected: 4

[2/8] Testing: gpt-5.2-2025-12-11 with reasoning_effort=medium
  ✓ Completed in 44.18s
  ...

... (6 más) ...

COST COMPARISON
  GPT-5 total cost:      $1.3280
  GPT-5-mini total cost: $0.4154
  Overall cost:          $1.7434
  Cost difference:       $0.9126 (68.9%)

TEST COMPLETE
Results saved to:
  test_results/reasoning_effort_comparison_20260102_153042.csv
  test_results/reasoning_effort_comparison_20260102_153042.json
```

---

Documento creado: `TEST_REASONING_EFFORT_GUIDE.md` (con 800+ líneas de detalle)

¡Listo para usar! 🚀
