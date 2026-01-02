# Guía de Pruebas: Comparación de Reasoning Effort

Documento detallado sobre las pruebas comparativas de `reasoning_effort` para modelos GPT-5 en el pipeline de Residencia Fiscal.

## 📋 Descripción General

El script `test_reasoning_effort_comparison.py` ejecuta el pipeline de análisis de sentencias con **8 configuraciones diferentes** usando el mismo documento PDF para comparar:

1. **Coste de API** (USD)
2. **Consumo de tokens** (entrada/salida)
3. **Tiempo de procesamiento** (segundos)
4. **Calidad de extracción** (confianza, criterios detectados, pruebas clasificadas)

### Configuraciones Probadas

```
┌──────────────────────────────────────────────────────────┐
│ Configuración 1-4: GPT-5 (gpt-5.2-2025-12-11)           │
├──────────────────────────────────────────────────────────┤
│ Config 1: reasoning_effort = "high"     (máximo esfuerzo) │
│ Config 2: reasoning_effort = "medium"   (equilibrado)     │
│ Config 3: reasoning_effort = "low"      (mínimo)          │
│ Config 4: reasoning_effort = "minimal"  (sin razonamiento)│
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│ Configuración 5-8: GPT-5-mini (gpt-5-mini-2025-08-07)   │
├──────────────────────────────────────────────────────────┤
│ Config 5: reasoning_effort = "high"     (máximo esfuerzo) │
│ Config 6: reasoning_effort = "medium"   (equilibrado)     │
│ Config 7: reasoning_effort = "low"      (mínimo)          │
│ Config 8: reasoning_effort = "minimal"  (sin razonamiento)│
└──────────────────────────────────────────────────────────┘
```

---

## 🎯 Métricas Capturadas

### 1. Performance & Costo

| Métrica | Descripción | Rango | Importancia |
|---------|-------------|-------|------------|
| **time_seconds** | Tiempo total de procesamiento en segundos | 10-120s | Media - afecta velocidad del pipeline |
| **tokens_in** | Tokens consumidos en la entrada (prompt + PDF) | 5000-50000 | Alta - factor clave en costo |
| **tokens_out** | Tokens generados en la respuesta | 1000-15000 | Alta - factor clave en costo |
| **cost_usd** | Costo total en dólares | $0.01-$1.00 | **Crítica** - impacto presupuestario |

**Fórmula de costo** (simplificada):
```
cost_usd = (tokens_in * precio_entrada + tokens_out * precio_salida) * reasoning_effort_multiplicador
```

Ejemplo:
- GPT-5 con `reasoning_effort="high"` → costo **~3-4x más** que `minimal`
- GPT-5-mini con `reasoning_effort="high"` → costo **~2-3x más** que `minimal`

---

### 2. Calidad de Extracción

#### A. Confianza (`confianza_extraccion`)

**Valores posibles:** `ALTA`, `MEDIA`, `BAJA`, `NO CONSTA`

Indica cuán "seguro" está el modelo de la información extraída.

```python
# Factores que aumentan confianza:
- Caso claro de residencia fiscal (sí/no definido)
- Criterios bien documentados en la sentencia
- Pruebas detalladas y citadas explícitamente
- Resultado final inequívoco

# Factores que reducen confianza:
- Casos ambiguos o parciales
- Documentación escasa de criterios
- Resultado final indeciso o en revisión
- Sentencia incompleta o fragmentada
```

**Interpretación:**
- `ALTA`: Resultado confiable para análisis cuantitativo
- `MEDIA`: Útil pero requiere revisión manual
- `BAJA`: Solo para análisis exploratorio, revisar antes de usar

---

#### B. Criterios Detectados (`criterios_detectados`)

**Cantidad de criterios de residencia identificados** en la sentencia.

Valores esperados según `prompt.py`:
- `CRIT_183_DIAS`: Presencia física > 183 días
- `CRIT_AUSENCIAS_ESPORADICAS`: Ausencias breves e intermitentes
- `CRIT_CENTRO_INTERESES_ECONOMICOS`: Centro de negocio/actividad
- `CRIT_CENTRO_INTERESES_VITALES`: Familia, amigos, bienes personales
- `CRIT_PRESUNCION_FAMILIA`: Presunción de residencia por familia
- `CRIT_CDI_TIEBREAKER`: Aplicación de Tratado de Doble Imposición
- `CRIT_OTRO`: Criterios no categorizados

**Ejemplo de salida:**
```json
{
  "Criterios_residencia_detectados": [
    "CRIT_183_DIAS",
    "CRIT_CENTRO_INTERESES_VITALES",
    "CRIT_CDI_TIEBREAKER"
  ],
  "criterios_detectados": 3
}
```

**Impacto de reasoning_effort:**
- `high`: Tiende a detectar **más criterios** (puede ser sobre-interpretación)
- `minimal`: Tiende a detectar **menos criterios** (puede perder matices)
- `medium`: Balance entre completitud y precisión

---

#### C. Resultado Final (`resultado_final`)

**Desenlace del caso de residencia fiscal:**

| Resultado | Significado | Frecuencia |
|-----------|------------|-----------|
| `GANA_AEAT` | Administración tributaria gana el caso | ~40% |
| `GANA_CONTRIBUYENTE` | Contribuyente gana el caso | ~35% |
| `PARCIAL` | Sentencia con resultados mixtos | ~20% |
| `RETROACCION` | Retroacción de la resolución | ~3% |
| `INADMISION` | Caso declarado inadmisible | ~2% |

**Verificación de calidad:**
```
✓ Si resultado_final = GANA_AEAT:
  - Pruebas_AEAT debe tener items aceptados
  - Pruebas_contribuyente debe tener rechazos

✓ Si resultado_final = GANA_CONTRIBUYENTE:
  - Pruebas_contribuyente debe tener items aceptados
  - Pruebas_AEAT debe tener rechazos

✓ Si resultado_final = PARCIAL:
  - Ambas partes deben tener items aceptados Y rechazados
```

---

#### D. Pruebas Clasificadas por Parte (`pruebas_aeat`, `pruebas_contribuyente`)

**Estructura de cada prueba presentada por una parte:**

```json
{
  "categoria": "PRESENCIA_FISICA_Y_DESPLAZAMIENTOS",
  "subcategoria": "días de estancia declarados",
  "detalle": "contribuyente registró 200 días en España",
  "aceptada": "SI",
  "peso": 4,
  "motivo": "evidencia documental clara",
  "cita": {
    "pagina": "3",
    "texto": "La declaración de días de estancia fue confirmada..."
  }
}
```

**Campos detallados:**

| Campo | Tipo | Descripción | Ejemplo |
|-------|------|------------|---------|
| `categoria` | String (ENUM) | Categoría oficial de prueba | `PRESENCIA_FISICA_Y_DESPLAZAMIENTOS` |
| `subcategoria` | String | Tipo específico de prueba | `"días de estancia"` |
| `detalle` | String | Descripción de la prueba | `"registró 200 días en España"` |
| `aceptada` | String (SI\|NO\|PARCIAL) | Veredicto del juez | `"SI"` |
| `peso` | Integer (1-5) | Importancia relativa | `4` (crítica) |
| `motivo` | String | Fundamento de aceptación/rechazo | `"evidencia documental clara"` |
| `cita.pagina` | String | Número de página en sentencia | `"3"` |
| `cita.texto` | String | Fragmento textual de la sentencia | `"La declaración fue confirmada..."` |

---

#### E. Pruebas Rechazadas Clave (`pruebas_rechazadas_clave`)

**Definición:** Pruebas que el juez rechazó pero que **hubieran podido cambiar el resultado** si se hubieran aceptado.

**Estructura:**

```json
[
  {
    "parte": "CONTRIBUYENTE",
    "categoria": "CONSUMOS_FINANCIEROS",
    "subcategoria": "transacciones bancarias",
    "detalle": "20+ transacciones mensuales en bancos españoles",
    "razon_rechazo": "falta de autenticidad de documentos",
    "cita": {
      "pagina": "8",
      "texto": "Los extractos bancarios no cumplen requisitos de auditoria..."
    }
  }
]
```

**Campos:**

| Campo | Descripción | Significado |
|-------|------------|-----------|
| `parte` | AEAT \| CONTRIBUYENTE | ¿Quién presentó esta prueba? |
| `categoria` | ENUM (12 categorías) | Tipo de prueba rechazada |
| `subcategoria` | String libre | Subtipo (ej: "transacciones mensuales") |
| `detalle` | String libre | Descripción específica de la prueba |
| `razon_rechazo` | String libre | Por qué el juez la rechazó |
| `cita.pagina` | String | Dónde aparece en sentencia |
| `cita.texto` | String | Texto de la sentencia que explica rechazo |

**Análisis de Impacto:**

```python
# Ejemplo: ¿Cuántas pruebas rechazadas habrían ganado el caso?
pruebas_rechazadas = datos.get("pruebas_rechazadas_clave", [])

# Si resultado_final = GANA_AEAT
# Pero pruebas_rechazadas del contribuyente son muchas:
#   → Caso es más "frágil" (AEAT ganó por poco)
#   → Mayor riesgo de apelación

# Si resultado_final = GANA_CONTRIBUYENTE
# Pero pruebas_rechazadas de AEAT son pocas:
#   → Caso es más "sólido" (victoria clara)
#   → Menor riesgo de revisión
```

**Interpretación según reasoning_effort:**

```
reasoning_effort="high":
  ✓ Identifica MÁS pruebas rechazadas
  ✓ Mejor análisis de impacto contrafáctico
  ✓ Entiende alternativas al resultado

reasoning_effort="minimal":
  ✗ Puede perder pruebas rechazadas importantes
  ✗ Menor análisis de escenarios alternativos
```

---

#### F. Prueba Decisiva / "Bala de Plata" (`prueba_o_bala_de_plata`)

**Definición:** La **prueba más importante** que determinó el resultado del caso. La que "rompió el empate".

**Estructura:**

```json
{
  "parte": "AEAT",
  "categoria": "VIVIENDA_Y_USO_EFECTIVO",
  "subcategoria": "declaración de impuestos inmuebles",
  "detalle": "contribuyente declaró bienes inmuebles en España bajo residencia española",
  "cita": {
    "pagina": "15",
    "texto": "La propia presentación fiscal del contribuyente, declarando inmuebles en España bajo jurisdicción tributaria española..."
  }
}
```

**Campos:**

| Campo | Descripción |
|-------|------------|
| `parte` | AEAT \| CONTRIBUYENTE (quién ganó) |
| `categoria` | Categoría de la prueba decisiva |
| `subcategoria` | Tipo específico |
| `detalle` | Descripción ejecutiva (1-2 líneas) |
| `cita.pagina` | Página donde aparece en sentencia |
| `cita.texto` | Texto que justifica por qué fue decisiva |

**Ejemplos de "Balas de Plata":**

```
Caso 1 - AEAT gana:
  "La propia declaración del contribuyente reconoce residencia en España"
  → Evidencia de admisión de parte

Caso 2 - Contribuyente gana:
  "Contrato de empleo con empresa francesa, con sedes solo en París"
  → Centro de intereses económicos fuera de España

Caso 3 - PARCIAL:
  "Se demuestra residencia para 2 de 3 años bajo revisión"
  → Evidencia mixta, resultado compartido
```

**Indicadores de Calidad:**

```
✓ BUENA extracción:
  - Bala de plata es coherente con resultado_final
  - Cita.texto es específica y directa
  - Detalle explica causalidad

✗ MALA extracción:
  - Bala de plata contradice resultado_final
  - Cita.texto es vaga ("NO CONSTA")
  - Detalle es genérico o irrelevante
```

**Verificación de Coherencia:**

```python
# Ejemplo de verificación
bala = resultado.get("Prueba_o_bala_de_plata", {})
resultado_final = resultado.get("resultado_final")

# Validación
if resultado_final == "GANA_AEAT":
    assert bala.get("parte") == "AEAT", "Inconsistencia: parte no coincide"
    assert bala.get("cita", {}).get("pagina") != "NO CONSTA", "Cita vacía"

# Métrica de calidad
calidad_bala = {
    "coherencia": bala.get("parte") == parte_ganadora,
    "especificidad": len(bala.get("cita", {}).get("texto", "")) > 50,
    "completitud": all([
        bala.get("parte"),
        bala.get("categoria"),
        bala.get("detalle"),
        bala.get("cita", {}).get("texto")
    ])
}
```

**Categorías esperadas (según `config.py`):**

```python
VALID_CATEGORIAS_PRUEBA = {
    "PRESENCIA_FISICA_Y_DESPLAZAMIENTOS",    # Viajes, pasaportes, billetes
    "VIVIENDA_Y_USO_EFECTIVO",               # Vivienda principal, piso compartido
    "SUMINISTROS_Y_CONSUMOS_DOMESTICOS",     # Agua, luz, gas, internet
    "CONSUMOS_FINANCIEROS",                  # Bancos, tarjetas, seguros
    "FAMILIA_Y_ENTORNO_PERSONAL",            # Cónyuge, hijos, amigos
    "SALUD_Y_SERVICIOS_PERSONALES",          # Médicos, escuelas, dentista
    "ACTIVIDAD_ECONOMICA_Y_GESTION",         # Empresa, oficina, empleados
    "DOCUMENTACION_FISCAL_EXTRANJERA",       # Declaraciones impuestos extranjero
    "VINCULOS_ADMINISTRATIVOS_EN_ESPANA",    # Carnet conducir, empadronamiento
    "TRAZAS_DIGITALES",                      # Email, redes sociales, IP
    "TESTIFICAL_Y_PERICIAL",                 # Testimonios, peritos
    "OTROS",                                  # Pruebas no catalogadas
}
```

**Métricas de prueba:**

| Campo | Significado | Rango |
|-------|------------|-------|
| `aceptada` | Juez aceptó la prueba | SI/NO/PARCIAL |
| `peso` | Importancia relativa | 1 (baja) - 5 (crítica) |
| `motivo` | Razón de aceptación/rechazo | Texto libre |
| `cita.pagina` | Referencia en sentencia | "1", "3", "15" |
| `cita.texto` | Fragmento relevante | Texto extraído |

**Impacto de reasoning_effort:**

```
reasoning_effort="high":
  ✓ Más pruebas detectadas
  ✓ Mejor contextualización
  ✓ Motivos más detallados
  ✗ Más costoso
  ✗ Más tiempo

reasoning_effort="minimal":
  ✓ Más rápido
  ✓ Menos costoso
  ✗ Puede perder detalles
  ✗ Menos motivos documentados
```

---

### 3. Indicadores de Sesgo Potencial

**Monitorear estas métricas para detectar comportamientos anómalos:**

```
⚠️ SESGO POSITIVO (sobre-interpretación):
   - criterios_detectados >> 4 (más de lo esperado)
   - confianza = ALTA incluso en casos ambiguos
   - pruebas_aeat >> pruebas_contribuyente (favorece admin)

⚠️ SESGO NEGATIVO (sub-interpretación):
   - criterios_detectados < 1 (muy pocos)
   - confianza = BAJA en casos claros
   - Citaciones vacías o "NO CONSTA"

⚠️ INCONSISTENCIA:
   - resultado_final = GANA_AEAT pero pruebas_aeat está vacío
   - confianza = ALTA pero observaciones contienen errores
```

---

## 📊 Cómo Interpretar Resultados

### Tabla de Comparación

El script genera una tabla como esta:

```
model  reasoning_effort  time_seconds  tokens_in  tokens_out  cost_usd  confianza_extraccion  criterios_detectados
5      high             48.32         12453      3847        0.4521    ALTA                  4
5      medium           44.18         12453      3654        0.3892    ALTA                  4
5      low              38.95         12453      3421        0.3124    MEDIA                 3
5      minimal          33.47         12453      2987        0.2341    MEDIA                 3
5-mini high             19.54         12453      2876        0.1045    MEDIA                 3
5-mini medium           17.82         12453      2654        0.0876    MEDIA                 3
5-mini low              15.64         12453      2345        0.0712    BAJA                  2
5-mini minimal          13.21         12453      1987        0.0521    BAJA                  2
```

### Análisis de Decisión

**¿Cuándo usar cada configuración?**

```
┌─────────────────────────────────────────────────────────────┐
│ CASO DE USO: Research/Análisis Académico                    │
├─────────────────────────────────────────────────────────────┤
│ RECOMENDACIÓN: GPT-5 + reasoning_effort="high"              │
│                                                              │
│ RAZÓN:                                                       │
│ - Máxima precisión y completitud                            │
│ - Presupuesto no es restricción                             │
│ - Valor de error bajo                                       │
│                                                              │
│ COSTO: ~$0.45-0.50 por sentencia                           │
│ TIEMPO: 45-50 segundos por sentencia                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ CASO DE USO: Producción en Volumen                          │
├─────────────────────────────────────────────────────────────┤
│ RECOMENDACIÓN: GPT-5 + reasoning_effort="medium"            │
│                O GPT-5-mini + reasoning_effort="high"       │
│                                                              │
│ RAZÓN:                                                       │
│ - Balance costo-calidad                                     │
│ - Suficientemente preciso para análisis cuantitativo       │
│ - Margen presupuestario más amplio                          │
│                                                              │
│ COSTO: ~$0.09-0.39 por sentencia                           │
│ TIEMPO: 17-44 segundos por sentencia                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ CASO DE USO: Exploración/Prototipado Rápido                │
├─────────────────────────────────────────────────────────────┤
│ RECOMENDACIÓN: GPT-5-mini + reasoning_effort="minimal"      │
│                                                              │
│ RAZÓN:                                                       │
│ - Costo mínimo                                              │
│ - Velocidad máxima                                          │
│ - Aceptable para pre-filtrado                              │
│                                                              │
│ COSTO: ~$0.05 por sentencia (24x más barato que high)      │
│ TIEMPO: 13 segundos por sentencia                          │
│                                                              │
│ ⚠️ REQUISITO: Validación manual posterior                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Impacto de reasoning_effort en Pruebas Específicas

### Cómo reasoning_effort afecta la clasificación de pruebas

#### Escenario 1: Pruebas Rechazadas Clave

```
Sentencia: Contribuyente vs AEAT sobre residencia fiscal
Caso: Contribuyente declara residencia en París, AEAT dice España

reasoning_effort="high":
  pruebas_rechazadas_clave: [
    {
      "parte": "AEAT",
      "categoria": "PRESENCIA_FISICA_Y_DESPLAZAMIENTOS",
      "detalle": "facturas de hotel en España pero sin continuidad",
      "razon_rechazo": "aisladas, no demuestran residencia habitual",
      "cita": {"pagina": "7", "texto": "Las estancias puntuales no acreditan residencia..."}
    },
    {
      "parte": "AEAT",
      "categoria": "VIVIENDA_Y_USO_EFECTIVO",
      "detalle": "contrato de alquiler en Madrid de 3 meses",
      "razon_rechazo": "duración limitada, no vivienda habitual",
      "cita": {"pagina": "8", "texto": "El contrato de corta duración no evidencia..."}
    }
  ],
  "pruebas_rechazadas_clave_count": 2

reasoning_effort="minimal":
  pruebas_rechazadas_clave: [
    {
      "parte": "AEAT",
      "categoria": "VIVIENDA_Y_USO_EFECTIVO",
      "detalle": "contrato de alquiler",
      "razon_rechazo": "NO CONSTA",
      "cita": {"pagina": "NO CONSTA", "texto": "NO CONSTA"}
    }
  ],
  "pruebas_rechazadas_clave_count": 1

# ANÁLISIS:
# reasoning_effort="high" detectó 2 pruebas clave vs 1 en "minimal"
# Información perdida: Fundamento del rechazo, contexto de cada prueba
# IMPACTO: Análisis incompleto del caso con reasoning_effort="minimal"
```

---

#### Escenario 2: Bala de Plata (Prueba Decisiva)

```
reasoning_effort="high":
  "Prueba_o_bala_de_plata": {
    "parte": "CONTRIBUYENTE",
    "categoria": "ACTIVIDAD_ECONOMICA_Y_GESTION",
    "subcategoria": "oficina principal registrada",
    "detalle": "Contribuyente mantiene oficina con empleados en París desde 2015,
               donde realiza todas las operaciones de su empresa de consultoría",
    "cita": {
      "pagina": "12",
      "texto": "Consta en autos que el demandante mantiene una oficina con cuatro
               empleados en París, donde se gestiona la totalidad de las operaciones
               de su empresa de consultoría fiscal. No existe evidencia de actividad
               económica en España en los períodos bajo revisión."
    }
  }

reasoning_effort="minimal":
  "Prueba_o_bala_de_plata": {
    "parte": "CONTRIBUYENTE",
    "categoria": "ACTIVIDAD_ECONOMICA_Y_GESTION",
    "subcategoria": "oficina",
    "detalle": "Oficina en París",
    "cita": {
      "pagina": "12",
      "texto": "NO CONSTA"
    }
  }

# DIFERENCIAS CLAVE:
# high:  Detalla "4 empleados", "desde 2015", "gestión total operaciones"
#        Contextualiza por qué es decisiva
# minimal: Solo menciona existencia de oficina
#          Pierde contexto causal

# CALIDAD:
# high:   Especificidad=95%, Coherencia=SÍ, Completitud=100%
# minimal: Especificidad=20%, Coherencia=SÍ, Completitud=40%
```

---

#### Escenario 3: Pruebas Aceptadas con Detalles

```
Categoría: CONSUMOS_FINANCIEROS
Prueba: Transacciones bancarias

reasoning_effort="high":
  {
    "categoria": "CONSUMOS_FINANCIEROS",
    "subcategoria": "patrones de gasto mensual",
    "detalle": "200+ transacciones mensuales en comercios, restaurantes y servicios
              españoles en 2022-2024, con gasto promedio de €3,500/mes",
    "aceptada": "SI",
    "peso": 5,
    "motivo": "patrón de consumo consistente en España demuestra residencia
             habitual, incluyendo gastos estacionales y recurrentes de mantenimiento",
    "cita": {
      "pagina": "14-15",
      "texto": "Los registros bancarios del demandante muestran un patrón de gastos
              consistente en territorio español, con transacciones regularmente
              distribuidas a lo largo de los meses bajo revisión, incluyendo
              pagos de servicios domésticos, supermercados y entretenimiento..."
    }
  }

reasoning_effort="minimal":
  {
    "categoria": "CONSUMOS_FINANCIEROS",
    "subcategoria": "transacciones bancarias",
    "detalle": "Transacciones en España",
    "aceptada": "SI",
    "peso": 3,
    "motivo": "Demuestra residencia",
    "cita": {
      "pagina": "14",
      "texto": "Registros bancarios muestran transacciones en España"
    }
  }

# DIFERENCIAS:
# high:   Cuantificación (200+, €3,500/mes)
#         Análisis temporal (2022-2024, distribución mensual)
#         Categorización (comercios, servicios, mantenimiento)
#         Peso: 5 (crítica)

# minimal: Descripción genérica
#          Sin cifras
#          Sin temporal
#          Peso: 3 (moderada)

# IMPACTO en análisis:
# high:   Permite estadísticas: "promedio gasto por categoría"
#         Detecta patrones estacionales
#         Mejor para validación automática

# minimal: Solo binary (existe/no existe)
#          Imposible análisis cuantitativo
```

---

### Métrica Agregada: "Densidad de Información"

Métrica propuesta para medir diferencia de reasoning_effort:

```python
def calculate_information_density(resultado, reasoning_effort):
    """
    Calcula índice de información (0-100) basado en:
    - Completitud de campos
    - Especificidad de detalles
    - Proporción de 'NO CONSTA'
    - Longitud de citas
    """

    score = 0
    weights = {
        "pruebas_completas": 30,      # 0-30 pts
        "citas_completas": 20,         # 0-20 pts
        "motivos_detallados": 20,      # 0-20 pts
        "pesos_calibrados": 15,        # 0-15 pts
        "sin_no_consta": 15,           # 0-15 pts
    }

    # Pruebas completas (todas tienen cita.texto)
    pruebas = (resultado.get("Pruebas_AEAT", []) +
               resultado.get("Pruebas_contribuyente", []))
    if pruebas:
        completas = sum(1 for p in pruebas if p.get("cita", {}).get("texto") != "NO CONSTA")
        score += (completas / len(pruebas)) * weights["pruebas_completas"]

    # Citas con texto largo (> 50 caracteres)
    citas_largas = sum(1 for p in pruebas
                      if len(p.get("cita", {}).get("texto", "")) > 50)
    if pruebas:
        score += (citas_largas / len(pruebas)) * weights["citas_completas"]

    # Motivos >= 20 caracteres
    motivos_detailed = sum(1 for p in pruebas
                          if len(p.get("motivo", "")) >= 20)
    if pruebas:
        score += (motivos_detailed / len(pruebas)) * weights["motivos_detallados"]

    # Pesos distribuidos (no todos 1 o todos 5)
    pesos = [p.get("peso", 1) for p in pruebas]
    peso_variance = sum(abs(p - 3) for p in pesos) / len(pesos) if pesos else 0
    score += min(peso_variance / 2, weights["pesos_calibrados"])

    # Sin "NO CONSTA"
    no_consta_count = sum(1 for p in pruebas
                         if "NO CONSTA" in str(p))
    score += (1 - min(no_consta_count / max(len(pruebas), 1), 1)) * weights["sin_no_consta"]

    return round(score)

# Resultados esperados:
# reasoning_effort="high":    densidad_informacion = 85-95
# reasoning_effort="medium":  densidad_informacion = 70-80
# reasoning_effort="low":     densidad_informacion = 55-70
# reasoning_effort="minimal":  densidad_informacion = 30-50
```

**Cómo usar esta métrica:**

```bash
# En tus análisis CSV/JSON:
if información_densidad < 50:
    print("⚠️ ADVERTENCIA: Información incompleta")
    print("   Considerar re-procesar con reasoning_effort='high'")

if información_densidad > 85:
    print("✓ Información de alta calidad")
    print("   Apta para análisis cuantitativo confiable")
```

---

## 🔍 Ejemplos de Análisis Detallados

### Ejemplo 1: Comparación de Calidad

**Hipótesis:** ¿"high" detecta criterios que "minimal" no ve?

**Análisis:**

```python
# Datos simulados de una sentencia sobre CDI
high_config = {
    "criterios_detectados": 4,
    "Criterios_residencia_detectados": [
        "CRIT_183_DIAS",
        "CRIT_CENTRO_INTERESES_VITALES",
        "CRIT_CENTRO_INTERESES_ECONOMICOS",
        "CRIT_CDI_TIEBREAKER"
    ],
    "confianza_extraccion": "ALTA"
}

minimal_config = {
    "criterios_detectados": 2,
    "Criterios_residencia_detectados": [
        "CRIT_183_DIAS",
        "CRIT_CDI_TIEBREAKER"
    ],
    "confianza_extraccion": "BAJA"
}

# Análisis:
# - "high" detectó 2 criterios adicionales
# - Mejora de confianza de BAJA a ALTA
# - Costo adicional: $0.218 (48% más caro)
# - Tiempo adicional: 14.85s (37% más lento)

# CONCLUSIÓN:
# Vale la pena usar "high" para casos con CDI (tiebreaker complexo)
```

---

### Ejemplo 2: Comparación de Pruebas

**Hipótesis:** ¿"high" clasifica las pruebas de forma diferente?

**Análisis:**

```python
# Prueba específica en ambas configuraciones

high_evidence = {
    "categoria": "VIVIENDA_Y_USO_EFECTIVO",
    "subcategoria": "contrato de arrendamiento",
    "detalle": "contrato de alquiler en España a nombre del contribuyente",
    "aceptada": "SI",
    "peso": 5,
    "motivo": "evidencia directa de domicilio habitual",
    "cita": {
        "pagina": "12",
        "texto": "En el contrato de arrendamiento consta que el domicilio..."
    }
}

minimal_evidence = {
    "categoria": "VIVIENDA_Y_USO_EFECTIVO",
    "subcategoria": "contrato de arrendamiento",
    "detalle": "contrato de alquiler",
    "aceptada": "PARCIAL",
    "peso": 3,
    "motivo": "evidencia de domicilio",
    "cita": {
        "pagina": "12",
        "texto": "NO CONSTA"
    }
}

# Diferencias:
# - Weight: 5 vs 3 (reasoning_effort="high" más crítica)
# - Aceptación: SI vs PARCIAL (high más decisivo)
# - Cita.texto: Completa vs Vacía (high mejor documentada)
# - Motivo: Más específico en high
```

---

## 📈 Interpretación de Gráficas

### Gráfica 1: Costo vs Calidad

```
COST (USD)
0.50 │     ╭─ GPT-5 high
     │    ╱
0.40 │   ╱  ╭─ GPT-5 medium
     │  ╱  ╱
0.30 │ ╱  ╱  ╭─ GPT-5 low
     │╱  ╱  ╱
0.20 │  ╱  ╱  ╭─ GPT-5-mini high
     │ ╱  ╱  ╱
0.10 │╱  ╱  ╱
     ├────────────────────────────
     │ BAJA  MEDIA  ALTA
     └─────────────────────
         CONFIANZA
```

**Lectura:**
- Costo sube exponencialmente con confianza
- Punto óptimo típicamente en "medium" de GPT-5 o "high" de GPT-5-mini
- ROI (Return on Investment) cae después de "medium"

---

### Gráfica 2: Tiempo vs Costo

```
TIEMPO (segundos)
50 │ GPT-5 high
   │ ╱
40 │╱  GPT-5 medium
   │   ╱
30 │  ╱  GPT-5 low
   │ ╱  ╱
20 │╱  ╱  GPT-5-mini high
   │   ╱  ╱
10 │  ╱  ╱  GPT-5-mini minimal
   │─────────────────────────
   │ 0.05  0.15  0.25  0.35  0.45
   └─────────────────────────
         COSTO (USD)
```

**Lectura:**
- Correlación fuerte: más costo → más tiempo
- Excepciones: GPT-5-mini puede ser 2x más rápido por mismo resultado
- Inflection point en ~$0.30 (modelo menos eficiente)

---

## 🛠️ Cómo Usar los Resultados

### 1. Seleccionar Configuración Óptima

```bash
# Paso 1: Ejecutar pruebas
python test_reasoning_effort_comparison.py \
    --pdf sentencias/STS_371_2020.pdf

# Paso 2: Analizar CSV generado
#   test_results/reasoning_effort_comparison_*.csv

# Paso 3: Decidir basado en:
#   - Presupuesto disponible
#   - Tolerancia a error
#   - Velocidad requerida
```

### 2. Actualizar Configuración

```bash
# Opción A: Cambiar en config.py (afecta todos los runs)
# Editar: REASONING_EFFORT = "high"

# Opción B: Pasar por CLI (solo ese run)
python residenciafiscal.py \
    --input ./sentencias \
    --output ./output \
    --model gpt-5.2-2025-12-11 \
    --reasoning-effort medium
```

### 3. Monitorear en Producción

```python
# En tus logs, buscar:
"⚙️ Reasoning Effort: medium"

# Y correlacionar con:
cost_usd = resultado.get("cost_usd")
confianza = resultado.get("confianza_extraccion")

# Si cost_usd > presupuesto:
#   → Considerar cambiar a "low" o GPT-5-mini
# Si confianza = "BAJA" frequently:
#   → Considerar cambiar a "high"
```

---

## 📋 Checklist de Validación

Antes de usar los resultados en producción:

- [ ] ¿Las 8 configuraciones completaron exitosamente?
- [ ] ¿Hay patrones coherentes en cost_usd?
- [ ] ¿confianza_extraccion es consistente dentro de cada modelo?
- [ ] ¿criterios_detectados varían razonablemente (1-5)?
- [ ] ¿Las citas están completas (no "NO CONSTA")?
- [ ] ¿Hay correlación clear entre reasoning_effort y calidad?
- [ ] ¿El presupuesto disponible soporta la configuración elegida?
- [ ] ¿El tiempo de procesamiento es aceptable?

---

## 🚨 Troubleshooting

### Problema: "cost_usd = 0" en todas las configuraciones

**Causa:** La función de cálculo de costos no está cargando precios.

**Solución:**
```bash
# Verificar que model_pricing.py existe
ls -la model_pricing.py

# Si no existe, crear con precios OpenAI
python -c "from openai import OpenAI; print(OpenAI.__version__)"
```

---

### Problema: "tokens_in es diferente entre configuraciones"

**Causa normal:** Razonamientos diferentes generan prompts ligeramente distintos.

**Esperado:** `tokens_in` debe ser **idéntico** (mismo PDF).

**Solución:**
```bash
# Verificar en JSONL output
cat test_results/reasoning_effort_comparison_*.json | \
    grep "tokens_in" | \
    sort | uniq -c
```

---

### Problema: "confianza_extraccion = 'NO CONSTA'" en todos

**Causa:** LLM no está extrayendo el campo correctamente.

**Solución:**
1. Verificar que `prompt.py` incluye instrucción de confianza
2. Usar el PDF completo (todas las páginas) para evitar respuestas incompletas
3. Cambiar a `reasoning_effort="high"` (más contexto)

---

## 📚 Referencias

- **OpenAI Reasoning Effort Docs:** https://platform.openai.com/docs/guides/reasoning
- **Pricing Calculator:** https://openai.com/pricing
- **Model Capabilities:** https://platform.openai.com/docs/models

---

## 📞 Soporte

Si encuentras discrepancias o resultados inesperados:

1. Revisa la sección **Troubleshooting** arriba
2. Verifica que `OPENAI_API_KEY` está configurada
3. Consulta los logs detallados: `tail -100 test_reasoning_effort_comparison.log`
4. Intenta primero con un PDF pequeño (test case simple)
