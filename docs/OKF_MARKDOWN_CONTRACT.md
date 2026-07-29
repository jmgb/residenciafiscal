# Contrato del perfil jurisprudencial Markdown v2

Este documento define la representación canónica y regenerable de una sentencia
en `knowledge/jurisprudencia/sentencias/<slug>.md`. Complementa
[`OKF_PIPELINE.md`](OKF_PIPELINE.md): el pipeline explica cómo se construye y
este contrato fija qué significa cada parte del resultado.

La versión vigente es `residenciafiscal-okf/2`.

## Autoridad y naturaleza del contenido

El perfil Markdown no sustituye a la sentencia ni es una transcripción completa.
Combina tres clases de contenido que deben permanecer diferenciadas:

| Clase | Procedencia | Puede presentarse como texto de la sentencia |
|---|---|:---:|
| Fuente literal | Subcadena exacta del texto bruto extraído del PDF | Sí |
| Análisis derivado | Registro JSON producido por el pipeline de análisis | No |
| Anotación editorial | Sidecar YAML propuesto o aprobado | No, salvo su `source_anchor` literal |

El PDF identificado por `resource` y `source_sha256` es la fuente de máxima
autoridad. El perfil, el snapshot JSON y los índices se regeneran; no se editan
a mano.

## Nombre, identidad y ubicación

- Ruta: `knowledge/jurisprudencia/sentencias/<slug>.md`.
- El `slug` se deriva de `archivo`, no de la posición del documento en un lote.
- Las pruebas y citas tienen IDs estables basados en contenido.
- Insertar otra prueba o reordenar una lista no debe cambiar los IDs existentes.
- Una modificación sustantiva del elemento sí puede producir otro ID.

## Frontmatter obligatorio

El renderizador escribe siempre estos campos:

| Campo | Tipo | Semántica |
|---|---|---|
| `type` | string | Siempre `Sentencia fiscal`; requisito base de OKF |
| `title` | string | Título legible, hoy el ROJ |
| `description` | string | Descripción derivada y breve |
| `resource` | path | PDF original de la sentencia |
| `tags` | list[string] | Materia, resultado y criterios decisivos |
| `status` | enum | `draft` si hay warnings o citas pendientes; en otro caso `stable` |
| `roj` | string | Identificador ROJ fuente |
| `ecli` | string | Identificador ECLI fuente |
| `organo` | string | Órgano judicial del análisis estructurado |
| `fecha_resolucion` | string | Fecha ISO cuando la entrada la contiene así |
| `ejercicios_afectados` | list[int] | Ejercicios extraídos del campo fuente |
| `paises` | list[string] | España y país de residencia alegado, sin duplicados |
| `cdi_aplicado` | string | País del CDI indicado en el análisis |
| `criterios_detectados` | list[string] | Valores canónicos `CRIT_*` |
| `criterios_decisivos` | list[string] | Subconjunto declarado como decisivo |
| `resultado` | enum | Resultado global canónico |
| `confianza_extraccion` | string | Confianza declarada por el análisis |
| `source_sha256` | SHA-256 | Huella binaria del PDF |
| `analysis_sha256` | SHA-256 | Huella del snapshot JSON de este registro |
| `schema_version` | string | Hoy `residenciafiscal-okf/2` |
| `sources` | list[object] | PDF y snapshot estructurado |
| `generated` | object | Identificador del generador |
| `citation_verification` | object | Métricas de localización y literalidad |
| `human_reviewed` | boolean | Revisión humana integral según las reglas del sidecar |
| `legal_issues` | object | Conteo de cuestiones propuestas y aprobadas |

`citation_verification` contiene:

| Campo | Tipo | Semántica |
|---|---|---|
| `threshold` | number | Umbral de localización aproximada |
| `total` | int | Todas las citas anidadas evaluadas |
| `evidence_found` | int | Citas cuyos fragmentos se localizaron |
| `literal` | int | Citas publicables desde fragmentos brutos |
| `pending_review` | int | Entradas que no se pueden presentar como literales |

El hash del JSONL completo y la versión de `pypdf` se guardan en
`manifest.json`, no en el frontmatter del concepto. El hash histórico del prompt
solo podrá declararse cuando la ejecución de análisis lo haya persistido; no se
reconstruye retrospectivamente.

## Orden obligatorio del cuerpo

El cuerpo se renderiza en este orden:

1. Regla de lectura.
2. `# Cuestión jurídica`.
3. `# Hechos relevantes`.
4. `# Posición de la Administración`.
5. `# Posición del contribuyente`.
6. `# Pruebas valoradas`.
7. `# Carga de la prueba`.
8. `# Normas y jurisprudencia citadas`.
9. `# Razonamiento y ratio decidendi`.
10. `# Fallo`.
11. `# Resultado por cuestiones jurídicas`.
12. `# Anotaciones y correcciones`.
13. `# Citas literales verificadas`.
14. `# Citas pendientes de revisión`.
15. `# Trazabilidad de citas`.
16. `# Calidad y procedencia`.
17. Nota al PDF original.

Las secciones se mantienen aunque no haya elementos. La ausencia se expresa con
un texto explícito, no eliminando la sección.

## Pruebas valoradas

Cada fila conserva:

- ID estable;
- subcategoría o nombre de la prueba;
- categoría canónica;
- criterio normalizado;
- valor exacto recibido como criterio de origen;
- valoración y motivo derivados;
- peso estructurado.

Una normalización nunca elimina el valor de origen. Por ejemplo, un criterio no
canónico puede publicarse como `CRIT_OTRO`, pero el valor recibido y la regla de
normalización permanecen trazables.

## Citas y fidelidad

### Citas literales verificadas

Solo entran aquí verificaciones `exact` o `exact_with_ellipsis` que tengan
`source_excerpt_verbatim` para todos sus fragmentos. Antes de renderizar, cada
fragmento se comprueba como subcadena exacta de la página bruta correspondiente.

El prefijo Markdown `>` y la línea de procedencia son formato editorial. Si la
cita contiene omisiones explícitas, el renderizador inserta `[…]` entre
fragmentos exactos. No corrige ortografía, ligaduras, puntuación, mayúsculas ni
saltos de línea del fragmento recuperado.

### Citas pendientes

Un match fuzzy, parcial o no localizado:

- no recibe un extracto literal reconstruido;
- no se muestra en bloque de cita;
- conserva el texto del análisis;
- se etiqueta como «Texto del análisis; no es una cita literal»;
- registra estado, fidelidad y puntuación para revisión.

### Trazabilidad

Cada cita conserva:

- ID propio;
- ID del elemento propietario;
- campo de origen en el JSON;
- estado de evidencia;
- fidelidad literal;
- puntuación;
- índices físicos del PDF.

La puntuación ayuda a localizar y priorizar revisión. No mide validez jurídica.

## Sidecars y revisión humana

El sidecar vive en `knowledge/annotations/<slug>.yaml` y nunca se genera dentro
del bundle para evitar que una regeneración borre decisiones editoriales.

Los estados son:

- `proposed`: visible, pendiente y sin efecto sobre el dato canónico;
- `approved`: puede modificar únicamente un metadato permitido y exige
  `reviewed_by` y `reviewed_at`.

`human_reviewed: true` exige que todas las anotaciones existentes estén
aprobadas y que cada identidad de revisión empiece por `human:`. Una aprobación
automática o de proceso no se presenta como humana.

Está prohibido corregir mediante sidecar el PDF, el texto de una cita,
`source_excerpt_verbatim`, `analysis_quote`, `resumen_criterios` o
`razonamiento_residencia`.

## Versionado y compatibilidad

Hay tres versiones independientes:

| Contrato | Versión vigente | Cuándo incrementarla |
|---|---|---|
| OKF externo | `0.2` | Cuando cambie la especificación adoptada |
| Perfil jurídico | `residenciafiscal-okf/2` | Cambio incompatible en frontmatter o cuerpo |
| Sidecar | `schema_version: 1` | Cambio incompatible en anotaciones |

Añadir un campo opcional compatible no obliga siempre a subir la versión. Cambiar
el significado de un campo, eliminarlo, hacerlo obligatorio o alterar qué se
considera cita literal sí exige nueva versión, migración y tests de contrato.

## Ejemplo canónico

El ejemplo real y versionado es
[`knowledge/jurisprudencia/sentencias/san-1071-2025.md`](../knowledge/jurisprudencia/sentencias/san-1071-2025.md).
Los tests de `test/test_okf_normalization.py` y `test/test_okf_bundle.py` son el
contrato ejecutable y tienen prioridad si una descripción narrativa queda
desactualizada.
