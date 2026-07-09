# CLAUDE.md

Guía para Claude Code en el proyecto **Residencia Fiscal**.

## Quick Start

```bash
# Instalar dependencias
pip install -r requirements.txt

# Configurar API key
export OPENAI_API_KEY="sk-..."

# Ejecutar pipeline completo (106 PDFs → ~$2.80 USD, ~2-3h)
python residenciafiscal.py --input ./sentencias --output ./output

# Test rápido con 1 PDF
python residenciafiscal.py --input ./sentencias --output ./output --max-files 1
```

## Resumen del Proyecto

Pipeline Python que analiza **106 sentencias judiciales españolas** sobre residencia fiscal (Art. 9 LIRPF) usando LLMs para extraer:

- **Criterios de residencia** aplicados (183 días, centro de intereses, familia, CDI)
- **Pruebas aportadas** por AEAT y contribuyente (aceptadas/rechazadas)
- **Razonamiento judicial** (doctrina, carga de prueba, motivación)
- **Resultado** (GANA_AEAT / GANA_CONTRIBUYENTE / PARCIAL)

**Usuarios objetivo**: Investigadores fiscales, abogados tributaristas, compliance.

## Arquitectura

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────────┐
│  sentencias/    │────▶│ residencia   │────▶│  output/            │
│  106 PDFs       │     │ fiscal.py    │     │  ├─ analisis.jsonl  │
│  (STS + SAN)    │     │              │     │  ├─ sentencias.csv  │
└─────────────────┘     │  + prompt.py │     │  ├─ pruebas.csv     │
                        │  + config.py │     │  └─ analisis.xlsx   │
                        └──────────────┘     └─────────────────────┘
                               │
                               ▼
                        ┌──────────────┐
                        │ OpenAI API   │
                        │ GPT-5 / Nano │
                        └──────────────┘
```

| Archivo | Función |
|---------|---------|
| `residenciafiscal.py` | Pipeline principal (async, batches de 10 PDFs) |
| `prompt.py` | System prompt con contexto legal y schema JSON |
| `config.py` | Modelos, rutas, enums, campos requeridos |
| `ai_service_adapter.py` | Wrapper para llamadas LLM con retry y cost tracking |

## Dataset

| Concepto | Valor |
|----------|-------|
| Total PDFs | 106 sentencias |
| Tribunal Supremo (STS) | 74 |
| Audiencia Nacional (SAN) | 32 |
| Período | 2015-2025 |
| Sentencias clave | 23 (modelo premium GPT-5) |

## Outputs Generados

Cada ejecución genera 5 archivos con timestamp:

| Archivo | Formato | Uso |
|---------|---------|-----|
| `analisis_*.jsonl` | 1 JSON/línea | Raw data completo, resumable |
| `analisis_*.csv` | Flat | Campos complejos como JSON strings |
| `sentencias_*.csv` | 1 fila/sentencia | Agregados de pruebas |
| `pruebas_*.csv` | 1 fila/prueba | Detalle judicial completo |
| `analisis_*.xlsx` | 2 hojas | Excel con Sentencias + Pruebas |

## Campos Principales del Schema

### Identificación
- `archivo`, `ROJ`, `ECLI`, `organo`, `fecha_resolucion`

### Residencia
- `es_caso_residencia_irpf`: SI/NO
- `pais_alegado_residencia_pf`, `pais_CDI_aplicado`
- `se_invoca_CDI`, `tiebreaker_paso_decisivo`

### Criterios (CRIT_*)
- `CRIT_183_DIAS` - Permanencia >183 días
- `CRIT_AUSENCIAS_ESPORADICAS` - Art. 9.1.a) segundo párrafo
- `CRIT_CENTRO_INTERESES_ECONOMICOS` - Núcleo principal de actividades
- `CRIT_CENTRO_INTERESES_VITALES` - Vínculos personales y familiares
- `CRIT_PRESUNCION_FAMILIA` - Cónyuge e hijos menores en España
- `CRIT_CDI_TIEBREAKER` - Reglas de desempate Art. 4 CDI
- `CRIT_OTRO`

### Pruebas (por parte: AEAT / Contribuyente)
```json
{
  "categoria": "PRESENCIA_FISICA_Y_DESPLAZAMIENTOS",
  "subcategoria": "sellos_pasaporte",
  "detalle": "Pasaporte con sellos de entrada/salida",
  "objetivo_probatorio": "Acreditar estancia fuera de España",
  "criterio_atacado": "CRIT_183_DIAS",
  "tipo_prueba": "DIRECTA | INDICIARIA | PRESUNCION",
  "origen": "APORTADA_PARTE | REQUERIDA_INSPECCION | OBTENIDA_TERCEROS",
  "aceptada": "SI | NO",
  "peso": 1-5,
  "motivo_valoracion": "Razón del juez para aceptar/rechazar",
  "cita": {"pagina": "12", "texto": "...extracto literal..."}
}
```

### Categorías de Prueba (12)
1. `PRESENCIA_FISICA_Y_DESPLAZAMIENTOS`
2. `VIVIENDA_Y_USO_EFECTIVO`
3. `SUMINISTROS_Y_CONSUMOS_DOMESTICOS`
4. `CONSUMOS_FINANCIEROS`
5. `FAMILIA_Y_ENTORNO_PERSONAL`
6. `SALUD_Y_SERVICIOS_PERSONALES`
7. `ACTIVIDAD_ECONOMICA_Y_GESTION`
8. `DOCUMENTACION_FISCAL_EXTRANJERA`
9. `VINCULOS_ADMINISTRATIVOS_EN_ESPANA`
10. `TRAZAS_DIGITALES`
11. `TESTIFICAL_Y_PERICIAL`
12. `OTROS`

### Razonamiento Judicial
- `doctrina_citada`: Lista de sentencias precedentes
- `carga_prueba`: {quien_tenia_carga, motivo, cumplida, cita}
- `razonamiento_residencia`: Texto explicando la decisión

### Resultado
- `resultado_final`: GANA_AEAT | GANA_CONTRIBUYENTE | PARCIAL | RETROACCION | INADMISION
- `confianza_extraccion`: ALTA | MEDIA | BAJA
- `tiempo_ejecucion`, `costo_usd`

## Sentencias Clave

23 sentencias en `sentencias/sentencias_CLAVE.txt` usan automáticamente **GPT-5** (modelo premium) independientemente del `--model` indicado:

```
STS_107_2018.pdf    # Caso ICEX - 183 días
STS_4305_2017.pdf   # Doctrina TS sobre centro intereses
STS_3942_2021.pdf   # CDI España-Suiza
...
```

**Coste**: ~$0.10/sentencia clave vs ~$0.006/sentencia normal

## Comandos Útiles

```bash
# Procesamiento completo
python residenciafiscal.py --input ./sentencias --output ./output

# Limitar archivos (testing)
python residenciafiscal.py --max-files 5

# Continuar ejecución interrumpida
python residenciafiscal.py --skip-existing

# Modelo específico (ignorado para sentencias clave)
python residenciafiscal.py --model gpt-4-turbo

# Reasoning effort (minimal/low/medium/high)
python residenciafiscal.py --reasoning-effort high

# Lista específica de PDFs
python residenciafiscal.py --pdf-list ./mi_lista.txt
```

## Costes Estimados

| Modelo | Coste/PDF | 106 PDFs |
|--------|-----------|----------|
| gpt-5-nano (default) | $0.006 | $0.50 |
| gpt-5 (clave) | $0.10 | $2.30 |
| **Total mixto** | $0.026 avg | **$2.80** |

## Configuración (config.py)

```python
# Modelos
DEFAULT_MODEL = GPT_5_NANO           # gpt-5.6-luna
SENTENCIA_CLAVE_MODEL = GPT_5        # gpt-5.2-2025-12-11
REASONING_EFFORT = "medium"

# Procesamiento
BATCH_SIZE = 10                      # PDFs en paralelo
LLM_MAX_RETRIES = 4
LLM_BACKOFF_BASE = 1.8

# Rutas
DEFAULT_INPUT_DIR = PROJECT_ROOT / "sentencias"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"
KEY_SENTENCIAS_FILE = DEFAULT_INPUT_DIR / "sentencias_CLAVE.txt"
```

## Dependencias

```
openai>=1.0.0       # LLM API
pypdf>=5.0.0        # PDF extraction
pandas>=2.0.0       # DataFrames
openpyxl>=3.1.0     # Excel export
tqdm>=4.65.0        # Progress bars
python-dotenv>=1.0.0
aiohttp>=3.8.0
pydantic>=2.0.0
```

## Troubleshooting

| Problema | Solución |
|----------|----------|
| `OPENAI_API_KEY not set` | `export OPENAI_API_KEY="sk-..."` o crear `.env` |
| PDF sin texto | Solo PDFs con texto (no scans/OCR) |
| Rate limits | Reducir `BATCH_SIZE` o aumentar `LLM_BACKOFF_BASE` |
| JSON parse error | El pipeline auto-repara; revisar logs si persiste |
| Ejecución interrumpida | Usar `--skip-existing` para continuar |

## Estructura de Archivos

```
residenciafiscal/
├── residenciafiscal.py      # Pipeline principal
├── prompt.py                # System prompt + schema
├── config.py                # Configuración centralizada
├── ai_service_adapter.py    # Wrapper LLM
├── model_pricing.py         # Cálculo de costes
├── sentencias/              # 106 PDFs entrada
│   ├── sentencias_CLAVE.txt # 23 sentencias premium
│   └── readme.txt           # Inventario
├── output/                  # Resultados generados
├── requirements.txt
├── .env                     # API keys (gitignored)
└── CLAUDE.md                # Este archivo
```

## Referencias

- [Art. 9 LIRPF](https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764) - Residencia habitual
- [Modelo OCDE Art. 4](https://www.oecd.org/tax/treaties/) - CDI tie-breaker rules
- [CENDOJ](https://www.poderjudicial.es/search/) - Fuente de sentencias
- [OpenAI API](https://platform.openai.com/docs)

## 🔍 Cross-review con Codex (segundo par de ojos)

Tras una feature/cambio **relevante**, lanzar automáticamente `/codex:review --wait` como gate de IA antes del primer commit.

**Posición en el flujo**: tests/lint verdes → `/codex:review --wait` → (aplicar fixes) → `git add/commit/push`. Pre-commit (no pre-push) para que los fixes entren en el mismo commit y la historia git quede limpia.

**Lanzar SÍ**: features nuevas, refactors multi-archivo, cambios en lógica crítica/seguridad/auth, infra/deploy, migraciones DB, o cualquier cambio donde el coste de un bug sea alto.
**Lanzar NO**: typos, comentarios, logging, formateo, cambios de 1 línea o exploración.
**En duda**: lanzar (coste bajo, upside alto).

**Si hay hallazgos serios**: `/codex:rescue --resume "aplica los fixes propuestos"` antes de commit.

**Features grandes con commits incrementales**: una sola review al cerrar la feature con `--scope branch --base main`; los fixes van en un commit final "address codex review" antes del push.
