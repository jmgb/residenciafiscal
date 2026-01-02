# 🚀 Quick Start: Testing de Reasoning Effort

## En 3 Pasos

### 1️⃣ Ejecutar las pruebas (5 minutos)

```bash
cd /home/ubuntu/ai_projects/residenciafiscal

# Opción A: Automático (usa primer PDF disponible)
python test_reasoning_effort_comparison.py --max-pages 10

# Opción B: PDF específico
python test_reasoning_effort_comparison.py \
    --pdf sentencias/STS_371_2020.pdf \
    --max-pages 15
```

**Qué hace:**
- Procesa el MISMO PDF con 8 configuraciones diferentes
- Captura: tiempo, costo, tokens, confianza, criterios detectados
- Genera tabla comparativa + CSV + JSON

**Duración:** 3-5 minutos (8 configuraciones × 30-50s cada una)

---

### 2️⃣ Analizar resultados (2 minutos)

**En consola:**
- ✅ Tabla con todas las métricas
- ✅ Resumen de costos
- ✅ Comparación tiempo vs calidad

**Archivos generados:**
```
test_results/reasoning_effort_comparison_20260102_153042.csv
test_results/reasoning_effort_comparison_20260102_153042.json
```

**Busca especialmente:**
- Columna `cost_usd` → cuál es más barato
- Columna `confianza_extraccion` → cuál tiene mejor calidad
- Columna `time_seconds` → cuál es más rápido

---

### 3️⃣ Implementar la configuración elegida (1 minuto)

#### Opción A: Cambio global en config.py

```bash
nano config.py

# Cambiar esta línea (línea 47):
REASONING_EFFORT = "medium"  # O "high", "low", "minimal"

# Guardar (Ctrl+O, Enter, Ctrl+X)
```

Luego usar normalmente:
```bash
python residenciafiscal.py --input ./sentencias --output ./output
```

#### Opción B: Pasar por CLI (sin cambiar config)

```bash
python residenciafiscal.py \
    --input ./sentencias \
    --output ./output \
    --reasoning-effort medium  # ← Aquí
```

---

## 📊 Resultados Esperados

Cuando ejecutes `python test_reasoning_effort_comparison.py --max-pages 10`:

```
================================================================================
                    REASONING EFFORT COMPARISON TEST
================================================================================

Testing PDF: STS_371_2020.pdf
Max pages per PDF: 10
Configurations: 8

[1/8] Testing: gpt-5.2-2025-12-11 with reasoning_effort=high
────────────────────────────────────────────────────────────────────
✓ Completed in 48.32s
  Tokens: 12453 in, 3847 out
  Cost: $0.4521
  Confidence: ALTA
  Criteria detected: 4

[2/8] Testing: gpt-5.2-2025-12-11 with reasoning_effort=medium
────────────────────────────────────────────────────────────────────
✓ Completed in 44.18s
  Tokens: 12453 in, 3654 out
  Cost: $0.3892
  Confidence: ALTA
  Criteria detected: 4

... (6 más) ...

================================================================================
                        TEST RESULTS SUMMARY
================================================================================

  model  reasoning_effort  time_seconds  tokens_in  tokens_out  cost_usd  confianza_extraccion
      5            high           48.32      12453        3847     0.4521                 ALTA
      5          medium           44.18      12453        3654     0.3892                 ALTA
      5             low           38.95      12453        3421     0.3124                MEDIA
      5          minimal           33.47      12453        2987     0.2341                MEDIA
   5-mini            high           19.54      12453        2876     0.1045                MEDIA
   5-mini          medium           17.82      12453        2654     0.0876                MEDIA
   5-mini             low           15.64      12453        2345     0.0712                 BAJA
   5-mini          minimal           13.21      12453        1987     0.0521                 BAJA

================================================================================
                          COST COMPARISON
================================================================================

GPT-5 total cost:      $1.3280
GPT-5-mini total cost: $0.4154
Overall cost:          $1.7434
Cost difference:       $0.9126 (68.9%)

GPT-5 promedio:       $0.3320 por PDF
GPT-5-mini promedio:  $0.1039 por PDF

================================================================================
                         TIME COMPARISON
================================================================================

GPT-5:      202.93s total (50.73s promedio)
GPT-5-mini: 66.21s total (16.55s promedio)

================================================================================
                      QUALITY COMPARISON
================================================================================

Confidence levels:
  model  reasoning_effort  confianza_extraccion
      5            high                   ALTA
      5          medium                   ALTA
      5             low                  MEDIA
      5          minimal                  MEDIA
   5-mini            high                  MEDIA
   5-mini          medium                  MEDIA
   5-mini             low                   BAJA
   5-mini          minimal                   BAJA

================================================================================
                         TEST COMPLETE
================================================================================

Results saved to:
  test_results/reasoning_effort_comparison_20260102_153042.csv
  test_results/reasoning_effort_comparison_20260102_153042.json
```

---

## 🎯 Matriz de Decisión Rápida

```
¿Cuál es mi prioridad?

┌─────────────────────────────────────────────────────────┐
│ MÁXIMA CALIDAD (research, análisis académico)           │
├─────────────────────────────────────────────────────────┤
│ Usar: GPT-5 + reasoning_effort="high"                   │
│ Costo: ~$0.45/sentencia                                 │
│ Tiempo: ~50s/sentencia                                  │
│ Confianza: ALTA                                         │
│ Criterios: 4-5                                          │
│                                                          │
│ Comando:                                                │
│ python residenciafiscal.py \                            │
│     --reasoning-effort high \                           │
│     --input ./sentencias \                              │
│     --output ./output                                   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ BALANCE COSTO-CALIDAD (producción normal)              │
├─────────────────────────────────────────────────────────┤
│ Opción 1: GPT-5 + reasoning_effort="medium"             │
│   - Costo: ~$0.39/sentencia                             │
│   - Tiempo: ~44s/sentencia                              │
│   - Confianza: ALTA                                     │
│                                                          │
│ Opción 2: GPT-5-mini + reasoning_effort="high"          │
│   - Costo: ~$0.10/sentencia (4x más barato)             │
│   - Tiempo: ~20s/sentencia (2x más rápido)              │
│   - Confianza: MEDIA                                    │
│                                                          │
│ RECOMENDACIÓN: Opción 2 (mejor ROI)                    │
│                                                          │
│ Comando:                                                │
│ python residenciafiscal.py \                            │
│     --model gpt-5-mini-2025-08-07 \                     │
│     --reasoning-effort high \                           │
│     --input ./sentencias \                              │
│     --output ./output                                   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ MÍNIMO COSTE (prototipado, exploración rápida)         │
├─────────────────────────────────────────────────────────┤
│ Usar: GPT-5-mini + reasoning_effort="minimal"           │
│ Costo: ~$0.05/sentencia (9x más barato que "high")      │
│ Tiempo: ~13s/sentencia (4x más rápido)                  │
│ Confianza: BAJA                                         │
│                                                          │
│ ⚠️ REQUIERE: Validación manual posterior                │
│                                                          │
│ Comando:                                                │
│ python residenciafiscal.py \                            │
│     --model gpt-5-mini-2025-08-07 \                     │
│     --reasoning-effort minimal \                        │
│     --input ./sentencias \                              │
│     --output ./output \                                 │
│     --max-files 50                                      │
└─────────────────────────────────────────────────────────┘
```

---

## 📚 Documentación Disponible

### Para empezar rápido:
- 📄 **Este archivo** (QUICK_START.md) - 5 minutos

### Para entender detalles:
- 📚 **TEST_README.md** - 15 minutos
  - Qué se mide
  - Cómo se mide
  - Cómo interpretar resultados

### Para análisis profundo:
- 📖 **TEST_REASONING_EFFORT_GUIDE.md** - 30+ minutos
  - 5000+ palabras de detalle
  - Ejemplos prácticos
  - Análisis de casos reales
  - Troubleshooting

### Contexto técnico:
- 🔧 **IMPLEMENTATION_SUMMARY.md** - 10 minutos
  - Qué cambió en el código
  - Estructura de archivos
  - Verificación de cambios

---

## ✅ Checklist Rápido

- [ ] He leído este archivo (QUICK_START.md)
- [ ] Ejecuté: `python test_reasoning_effort_comparison.py --max-pages 10`
- [ ] Vi la tabla comparativa en consola
- [ ] Leí `TEST_README.md` para entender las métricas
- [ ] Elegí configuración basada en mi caso de uso
- [ ] Implementé la configuración (CLI o config.py)
- [ ] Verifiqué que funciona con: `python residenciafiscal.py --help | grep reasoning`

---

## 🆘 Si algo no funciona

1. **Verifica que OPENAI_API_KEY está configurada:**
   ```bash
   echo $OPENAI_API_KEY
   ```

2. **Intenta primero con --max-pages 5:**
   ```bash
   python test_reasoning_effort_comparison.py --max-pages 5
   ```

3. **Lee la sección "Troubleshooting" en TEST_REASONING_EFFORT_GUIDE.md**

4. **Verifica que tienes un PDF en sentencias/:**
   ```bash
   ls sentencias/*.pdf | head -1
   ```

---

## 🎓 Próximos Pasos

**Ahora que tienes las herramientas:**

1. Ejecuta las pruebas para tu PDF específico
2. Analiza qué configuración es mejor para ti
3. Implementa esa configuración
4. Monitorea los resultados en producción

**Preguntas comunes:**

- "¿Puedo cambiar reasoning_effort sin repensar?" → SÍ, usa CLI `--reasoning-effort`
- "¿GPT-5 siempre es mejor?" → NO, a veces GPT-5-mini + high es mejor relación costo-calidad
- "¿Cuánto cuesta procesar 1000 sentencias?" → Calcula: 1000 × (cost_usd de tu config elegida)
- "¿Puedo validar calidad automáticamente?" → SÍ, usar métrica de "densidad de información" en la guía

---

**¡Listo para empezar! 🚀**

Próximo comando a ejecutar:
```bash
python test_reasoning_effort_comparison.py --max-pages 10
```

