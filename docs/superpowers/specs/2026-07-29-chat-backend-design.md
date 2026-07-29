# Backend del chat de residenciafiscal.org — Diseño

**Fecha**: 2026-07-29
**Estado**: aprobado · fase 0 ejecutada el 2026-07-29 · **bloqueado en la fase 0b**
**Continúa**: [`2026-07-29-frontend-chatbot-design.md`](2026-07-29-frontend-chatbot-design.md), que dejó el backend explícitamente fuera de alcance

Las restricciones de plataforma se contrastaron con la documentación oficial y
después **se midieron** contra un Deploy Preview en el *spike* de la fase 0
(2026-07-29). Cuatro de los cinco criterios pasaron y la decisión de runtime
queda confirmada; el quinto invalidó el mecanismo de estado y abrió la fase 0b,
que bloquea la implementación. Mediciones completas en
[`docs/operations/NETLIFY_EDGE.md`](../../operations/NETLIFY_EDGE.md).

## 1. Objetivo

Sustituir el motor de chat simulado de residenciafiscal.org por uno real: un
endpoint que responda preguntas en lenguaje natural sobre las 106 sentencias ya
analizadas por el pipeline Python, citando únicamente sentencias del corpus.

Al terminar, `chatEngineMode` pasa de `'stub'` a `'live'` y el aviso de
«respuesta simulada» desaparece de la interfaz automáticamente.

## 2. Punto de partida

Contexto necesario para revisar este diseño sin releer el repositorio entero.

### Lo que ya existe

| Pieza | Estado |
|---|---|
| Pipeline Python (`residenciafiscal.py`) | Procesa PDFs por lotes. **No se toca.** |
| API FastAPI (`api/main.py`, 260 líneas) | Envuelve el pipeline: 1 PDF → análisis. Solo corre en local, no está desplegada. **No se toca.** |
| SPA React (`frontend/`) | Desplegada en Netlify. Estática, sin servidor. |
| `frontend/src/lib/chat-engine.ts` | Punto único de selección del motor. Hoy `chatEngineMode = 'stub'`. |
| `frontend/src/lib/chat-engine.stub.ts` | Motor simulado: texto pregrabado por tema, streaming falso, citas reales del corpus. |
| `frontend/src/types/chat.ts` | Contrato `ChatEngine` / `ChatChunk` / `ChatSource`, escrito pensando en este backend. |
| `frontend/scripts/build-corpus.mjs` | En el `prebuild`, genera `public/data/corpus.json` (30 KB, metadatos ligeros de las 106 sentencias). |
| `output/analisis_*.jsonl` | 106 líneas, 888 KB, ~8,4 KB por sentencia. **No se versiona** (`output/` está en `.gitignore`). |

### Forma de un registro del JSONL

Campos relevantes para la recuperación:

```
archivo                            "SAN_1071_2025.pdf"
identificadores                    { ROJ, ECLI }
organo                             "Audiencia Nacional. Sala de lo Contencioso…"
fecha_resolucion                   "2025-02-18"
es_caso_residencia_irpf            SI | NO
ejercicios_afectados               "2010 y 2011"
pais_alegado_residencia_pf         "Francia"
pais_CDI_aplicado                  "Francia"
se_invoca_CDI                      SI | NO
Criterios_residencia_detectados    [CRIT_*]
Criterio_decisivo                  [CRIT_*]
resumen_criterios                  texto
doctrina_citada                    [string]
carga_prueba                       { quien_tenia_carga, motivo, cumplida, cita }
razonamiento_residencia            texto largo
Pruebas_AEAT                       [ { categoria, subcategoria, detalle, aceptada, peso, cita, … } ]
Pruebas_contribuyente              [ ídem ]
categorias_admitidas_aeat          [CATEGORIA]
categorias_rechazadas_aeat         [CATEGORIA]
categorias_admitidas_contribuyente [CATEGORIA]
categorias_rechazadas_contribuyente[CATEGORIA]
Pruebas_rechazadas_clave           [ { parte, categoria, … } ]
Prueba_o_bala_de_plata             { parte, categoria, … }
resultado_final                    GANA_AEAT | GANA_CONTRIBUYENTE | PARCIAL |
                                   RETROACCION | INADMISION | OTROS | FUERA_DE_ALCANCE
frases_clave                       [ { tema, pagina, texto } ]
confianza_extraccion               ALTA | MEDIA | BAJA
```

Los enums canónicos (7 criterios `CRIT_*`, 12 categorías de prueba y 7
resultados) viven en `config.py`. El frontend solo tipa sus 5 resultados
mostrables más `DESCONOCIDO`; hoy `OTROS` y `FUERA_DE_ALCANCE` se mapean a este
último y los criterios siguen siendo `string[]`. El backend valida el catálogo
completo y mantiene esa adaptación explícita.

### Deuda documental detectada al escribir esto

`CLAUDE.md` está desactualizado en dos puntos que este diseño toca de lleno, y
conviene arreglarlo aparte para que no siga induciendo a error:

- Enumera **5 resultados finales**; `config.py:156-164` define **7**.
- Su tabla de costes da **$0.006 por PDF** con `gpt-5.6-luna`, pero
  `model_pricing.py:23` tarifa ese modelo a **$1/M de entrada y $6/M de salida**, y
  los registros reales del JSONL rondan **$0.017 por sentencia**. Esa cifra
  optimista es la misma que me llevó a estimar el coste del chat tres veces por
  debajo del real.

Ninguna de las dos correcciones pertenece a esta feature, pero cualquiera que
diseñe apoyándose en `CLAUDE.md` repetirá el mismo error.

### Restricciones de plataforma verificadas

Comprobadas en la documentación oficial de Netlify el 2026-07-29. **Condicionan
el diseño entero**, así que se vuelven a verificar al implementar si han pasado
más de 30 días.

| Runtime | Límite | Consecuencia |
|---|---|---|
| Functions con streaming | **10 s de ejecución** + 20 MB de respuesta | Insuficiente: router + redacción pueden superar 10 s y cortar la respuesta. |
| Functions estándar sin streaming | 60 s + 6 MB de respuesta | El tiempo bastaría, pero se perdería la experiencia de streaming. |
| Background Functions | 15 min | No sirven: devuelven `202` y no pueden streamear al cliente. |
| **Edge Functions** | **50 ms de CPU propio**, 40 s para cabeceras, 20 MB de bundle comprimido, streaming soportado | La espera de red no cuenta como CPU. Es el único runtime de Netlify que conserva streaming más allá de 10 s. |

Además:

- Netlify ofrece **rate limiting nativo en el `config` de la Edge Function** en
  todos los planes. El máximo de ventana documentado es 180 s: sirve de
  cortafuegos de ráfagas, pero no sustituye la cuota horaria ni el techo diario.
- **Netlify Blobs es accesible desde Edge Functions** y su consistencia fuerte
  funciona: una lectura refleja siempre la escritura anterior. Pero sus
  escrituras condicionales por ETag **no dan compare-and-swap bajo concurrencia**:
  varios escritores con el mismo `onlyIfMatch` reciben todos `modified: true` y
  se pisan. Medido en la fase 0; ver la sección 4.
- Las Edge Functions se evalúan **antes** que los redirects, así que el catch-all
  `/* → /index.html` de `netlify.toml` no intercepta la ruta del endpoint.
- La CSP de `netlify.toml` ya incluye `connect-src 'self'`: al ser el mismo
  origen, **no hay que tocarla**.
- El `ignore` de `netlify.toml` solo reconstruye si cambia `frontend/**` o el
  propio `netlify.toml`; las Edge Functions viven bajo `frontend/`, así que encaja.

Fuentes: [límites de Edge Functions](https://docs.netlify.com/build/edge-functions/limits/),
[streaming y límites de Functions](https://docs.netlify.com/build/functions/api/#streaming-responses),
[rate limiting](https://docs.netlify.com/manage/security/secure-access-to-sites/rate-limiting/)
y [consistencia/escrituras condicionales de Blobs](https://docs.netlify.com/build/data-and-storage/netlify-blobs/).

## 3. Decisiones tomadas

| Decisión | Elección | Motivo | Alternativas descartadas |
|---|---|---|---|
| Dónde corre | Edge Function en el mismo repo | Único runtime de Netlify donde cabe una respuesta larga en streaming. Mismo deploy, mismo origen, CSP intacta. | Function con streaming (10 s), ampliar la FastAPI (exige hosting + CORS + dominio), Cloudflare Workers (otro origen), Supabase Edge (proveedor extra) |
| Recuperación | Router LLM barato → filtro determinista | El corpus ya viene estructurado por el pipeline: las facetas hacen el trabajo pesado y el router solo traduce lenguaje natural a facetas | Solo léxico (falla si la pregunta no usa el vocabulario del corpus), tool use (latencia variable), embeddings (sobreingeniería para 106 documentos) |
| Corpus del servidor | Embebido en el bundle y no servido como asset | Cero latencia de lectura y despliegue atómico con el código | Publicarlo como asset, cargarlo de Blobs en cada petición |
| Gasto y abuso | Límite nativo de ráfaga + cuota horaria + reserva de gasto diaria | El endpoint es la única pieza que cuesta dinero y está abierta | Solo límites del proveedor, contador no atómico |
| Estado de cuotas y presupuesto | Netlify Blobs, consistencia fuerte y compare-and-swap | Persistente y correcto entre isolates/regiones sin añadir proveedor | Memoria del isolate, `get` + `set` no atómico |
| Recuperación robusta | Unión de búsqueda léxica global y candidatos por facetas | Un error del router no puede excluir por sí solo la sentencia relevante | Filtro duro dependiente solo del router |
| Citas | Marcadores internos `[S1]` resueltos por servidor | El modelo nunca decide el ROJ/ECLI mostrado al usuario | Extraer ROJ libres del texto una vez ya emitido |

### Modelos

| Paso | Modelo | Por qué |
|---|---|---|
| Router | `gpt-5.6-luna` | Clasificación con salida JSON estricta; recibe el historial acotado para resolver preguntas de seguimiento |
| Redacción | `gpt-5.6-luna` (`GPT_5_MINI`) | Mismo modelo que usa el pipeline por defecto; contexto total limitado a 48 KB y salida a 1.200 tokens, incluido razonamiento |

Ambos pasos usan el mismo modelo **porque hoy no hay uno más barato disponible**:
en `config.py:43`, `GPT_5_NANO` es un alias de `gpt-5.6-luna`, igual que
`GPT_5_MINI`. No es una decisión de diseño, es el catálogo que hay. El router es
un paso barato por su tamaño de entrada, no por el modelo, y es el sitio donde
cambiar el ID el día que exista un modelo de clasificación más económico.

Las dos llamadas usan la **Responses API**, con `store: false`. El router usa
Structured Outputs con JSON Schema estricto; la redacción consume únicamente
eventos `response.output_text.delta`, y toma tokens/uso del
`response.completed`. `stream_options.include_usage` pertenece a Chat
Completions y no forma parte de este contrato.

Las Edge Functions **no importan `config.py`**. Los IDs, precios y enums
(`CRIT_*`, categorías de prueba, resultados) se duplican en un JSON pequeño que
Zod valida y TypeScript tipa al cargar. La misma librería valida el request y la
salida del router; no se mantiene un validador JSON casero. Es duplicación
consciente entre runtimes y lleva un test de contrato contra `config.py` y
`model_pricing.py`; no se confía solo en que el corpus casualmente contenga todos
los valores.

**Coste orientativo corregido**: ~$0.02–0.026 por pregunta si los 48 KB se
traducen en ~12–16k tokens de entrada, el router recibe hasta ~3k y la salida
visible ronda 700 tokens. A
`$1/M` de entrada y `$6/M` de salida, una petición con 25k tokens de contexto ya
costaría cerca de `$0.03`, no `$0.008`. Con el contexto acotado, el techo de
`$2/día` equivale aproximadamente a 75–100 preguntas medias, no a 250.

El presupuesto no convierte esa media en una cuota: antes de llamar al modelo se
reserva el coste máximo acotado de la petición y al terminar se reconcilia con el
uso real de ambas respuestas.

Referencia de la API: [Responses API — creación, streaming, Structured Outputs y
uso](https://developers.openai.com/api/reference/resources/responses/methods/create).

## 4. Arquitectura

### Piezas

```
frontend/
├── tsconfig.edge.json          # tipos del runtime Edge, separado del DOM de React
├── netlify/
│   └── edge-functions/
│       ├── chat.ts             # ÚNICO endpoint: valida, orquesta y streamea
│       └── lib/                # módulos compartidos; el bundler NO los escanea
│           ├── chat-config.json    # modelos, precios, enums y límites
│           ├── chat-config.ts      # valida/tipa la configuración JSON
│           ├── corpus.ts           # GENERADO Y VERSIONADO: índice + fichas
│           ├── corpus-types.ts     # tipos compartidos con el generador
│           ├── retrieval.ts        # recuperación y ranking — módulo puro
│           ├── router.ts           # Responses API + validación del JSON
│           ├── budget.ts           # cuota horaria y reserva diaria
│           ├── citations.ts        # valida [S<n>] y resuelve identificadores
│           └── sse.ts              # serialización del protocolo SSE
├── scripts/
│   └── build-corpus.mjs        # AMPLIADO: emite corpus público + corpus del servidor
└── src/lib/
    ├── chat-engine.ts          # chatEngineMode → 'live'
    ├── chat-engine.live.ts     # NUEVO: cliente SSE que cumple ChatEngine
    └── chat-engine.stub.ts     # se conserva para tests y dev sin claves
```

Los módulos compartidos van en **`lib/`, no en la raíz con prefijo `_`**. Netlify
trata todo `.ts` de la raíz de `netlify/edge-functions/` como una edge function y
exige que exporte por defecto una función: un `_corpus.ts` ahí rompe el build con
`Default export … must be a function`. El subdirectorio no se escanea.

Medido en el spike de la fase 0; ver
[`docs/operations/NETLIFY_EDGE.md`](../../operations/NETLIFY_EDGE.md).

La ruta y el límite nativo se declaran en el propio `chat.ts`; `rateLimit` no se
puede declarar en `netlify.toml`:

```ts
export const config: Config = {
  path: '/api/chat',
  rateLimit: {
    windowLimit: 8,
    windowSize: 180,
    aggregateBy: ['ip', 'domain'],
  },
};
```

El límite de 8/180 s frena ráfagas antes de ejecutar código sin romper una
conversación normal: un usuario que encadena cuatro o cinco preguntas de
seguimiento en pocos minutos es el comportamiento esperado, no un ataque. Quien
pone el techo real es la cuota horaria; la ventana nativa solo evita que un bucle
llegue a ejecutar código. Con un límite de 3 por ventana, el propio caso de uso
que describe el manifiesto —repreguntar hasta acotar un criterio— se bloquearía a
sí mismo.

La cuota de 10/hora se mantiene aparte porque la ventana nativa no llega a una
hora. Ojo al presupuesto de reglas por plan: Free/Starter admite **2 reglas por
proyecto**, así que esta consume la mitad del cupo disponible. Se omite
`method` para que el propio handler pueda devolver `405` a cualquier método
distinto de `POST`; si se limitara la invocación a `POST`, el catch-all de la SPA
podría convertir un `GET /api/chat` en un `200` con `index.html`.

### Contrato de entrada

El body es JSON con forma `{ "messages": [...] }`. El servidor no acepta campos
desconocidos y valida:

- `Content-Type: application/json`; máximo 32 KB de body.
- Entre 1 y 6 mensajes, alternando `user`/`assistant`, y el último debe ser
  `user`. Nunca se aceptan roles `system`, `developer` ni `tool`.
- La última pregunta tiene entre 1 y 500 caracteres; cada respuesta histórica,
  como máximo 4.000; el total de contenido, como máximo 12.000.
- Solo se envían al modelo `role` y `content`: IDs, timestamps, fuentes guardadas
  y cualquier otro metadato del navegador se descartan.

Estos límites protegen coste y contexto y evitan que un cliente convierta
metadatos persistidos en instrucciones.

El límite de body se aplica primero a `Content-Length` cuando existe y siempre
con un lector incremental que corta a 32 KB; no se llama a `request.json()` sobre
un body `chunked` sin cota.

### Flujo de una pregunta

```
POST /api/chat  { messages: [...] }
  │
  ├─ 0. Rate limit nativo de Netlify (antes de invocar la función)
  │
  ├─ 1. Validación + cuotas (sin coste LLM)
  │     body/roles/tamaños · 10 preguntas/hora por IP
  │     reserva atómica del coste máximo dentro del techo diario
  │
  ├─ 2. Router — gpt-5.6-luna, JSON Schema estricto, sin streaming
  │     { criterios[], organo, resultado, anios[], categorias_prueba[],
  │       foco, terminos[] }
  │     Si falla o su salida no valida → ruta léxica, no error al usuario
  │
  ├─ 3. Recuperación — determinista, sin red
  │     léxico global ∪ candidatos por facetas relajables → reranking
  │     top 8–12 dentro de un presupuesto de contexto explícito
  │
  ├─ 4a. ¿0 resultados? → respuesta honesta, sin segunda llamada;
  │                       se contabiliza solo el router
  │
  ├─ 4b. Redacción — gpt-5.6-luna, max_output_tokens acotado
  │      El modelo cita solo marcadores [S1]…[S12].
  │      Cada párrafo se valida y el servidor sustituye el marcador por el ROJ
  │      real antes de emitirlo al cliente.
  │
  └─ 5. Cierre
        done · reconciliación de la reserva con usage · log estructurado
```

El router recibe el historial validado, no solo la última frase, para entender
seguimientos como «¿y si fuera Francia?». Su schema usa enums cerrados del
catálogo, rangos numéricos acotados y arrays con máximo; `terminos` no puede
contener más de 8 elementos. La salida se valida de nuevo aunque el proveedor
prometa Structured Outputs.

### Presupuesto de CPU (50 ms)

Es el límite más incierto de la plataforma. El corpus generado va en **dos
niveles**:

- **Índice compacto** (~120 KB): identificadores, órgano, año, criterios
  detectados y decisivos, resultado, categorías admitidas/rechazadas, países, y
  los términos ya normalizados para la puntuación léxica. Se parsea **una vez**
  al arrancar el isolate y se reutiliza en las peticiones calientes.
- **Fichas completas**: un `Record<archivo, string>` donde cada valor es la ficha
  serializada. Solo se hace `JSON.parse` de las candidatas seleccionadas. De cada
  ficha se construye después una tarjeta de prompt con metadatos y fragmentos
  relevantes; no se envían los 8,4 KB medios completos por sentencia.

El generador puede emitir `JSON.parse("…")` o literales de objeto, pero la
elección se decide con benchmark, no por intuición. El gate del *spike* mide
arranque frío y petición caliente con el bundle real. Objetivo: p95 de CPU propio
< 40 ms en Deploy Preview, dejando 10 ms de margen.

### Recuperación (`_retrieval.ts`)

El router ayuda, pero no tiene poder de exclusión total:

1. **Baseline léxico global** sobre todos los registros con
   `es_caso_residencia_irpf = SI`, siempre ejecutado, con términos de la pregunta
   y sin depender del router. Los casos fuera de alcance nunca llegan al prompt.
2. **Candidatos por facetas**: criterios, órgano, resultado, rango de años,
   categorías de prueba y país del CDI. Si hay pocos resultados, se relajan
   primero órgano/resultado, después año/país y por último criterios/categorías.
3. **Unión y reranking** de ambos conjuntos. La puntuación usa
   `resumen_criterios`,
   `razonamiento_residencia`, `pruebas[].detalle` y `frases_clave[].texto`, con
   refuerzo si el criterio buscado aparece en `Criterio_decisivo` y no solo en
   `Criterios_residencia_detectados`.

El ranking devuelve 12 candidatas. El *context packer* incluye primero las 8
mejores con un máximo de 4 KB por tarjeta y añade `S9`…`S12` solo mientras quepan.
El prompt completo —instrucciones, historial y corpus— no puede superar 48 KB
UTF-8. Se recortan fragmentos por puntuación, no con un `slice` ciego que pueda
separar texto y fuente. No se confía en truncación automática del proveedor. El
módulo es **puro y sin globals de Deno**, para que se pueda probar con Vitest.

### Estado en Netlify Blobs

> ⛔ **Esta sección está invalidada por la medición de la fase 0 y necesita una
> decisión antes de implementarse.** El compare-and-swap en el que se apoya no
> es atómico. Ver
> [`docs/operations/NETLIFY_EDGE.md`](../../operations/NETLIFY_EDGE.md) y la
> subsección «Qué hacer» más abajo.

El diseño original era:

| Clave | Contenido | Uso |
|---|---|---|
| `rl:<YYYY-MM-DD-HH>:<hash(ip)>` | `{ count }` | 10 preguntas por hora natural UTC e IP |
| `spend:<YYYY-MM-DD>` | `{ spentMicros, reservations }` | techo global por día UTC |

La IP se guarda **hasheada con un salt**; nunca en claro. El registro caduca al
rotar la hora: es un contador, no un log de visitantes. Esa parte se conserva sea
cual sea la decisión.

Cada mutación seguía este algoritmo:

1. Lectura con consistencia fuerte y obtención de ETag.
2. Cálculo del nuevo estado.
3. `setJSON(..., { onlyIfMatch: etag })`; para la primera escritura,
   `onlyIfNew: true`.
4. Si otro isolate ganó la carrera, releer y reintentar hasta 3 veces. Si sigue
   habiendo contención o Blobs falla, devolver `503` **sin llamar a OpenAI**.

#### Por qué no funciona

Medido el 2026-07-29 contra un Deploy Preview: cinco peticiones concurrentes
sobre un contador a 0 lo dejaron en **2**. Tres de ellas leyeron el mismo valor
con el mismo ETag, escribieron con `onlyIfMatch` sobre ese ETag y **las tres
recibieron `modified: true`**. Nadie pierde la carrera, así que el paso 4 nunca
se ejecuta y las escrituras se pisan.

Los ETag además son deterministas por contenido —escribir `{n:1}` produce siempre
el mismo hash—, así que no son tokens de versión.

Consecuencia: la cuota horaria tendría fugas y **el techo de gasto podría
superarse**, que es la única garantía que protege el dinero.

#### Qué hacer

La alternativa validada en el mismo spike es **una clave por petición**: cada
petición escribe su propia clave bajo un prefijo y el recuento se obtiene
listando. Dos escritores nunca tocan la misma clave, así que el *lost update* es
imposible por construcción. Medido: 50 peticiones concurrentes → 50 entradas
exactas.

Cuesta 130–420 ms de latencia de red antes del primer token, obliga a iterar el
listado con `paginate: true`, y deja una ventana entre contar y escribir que
permite sobrepasar el techo por aproximadamente el factor de concurrencia.

Opciones sobre la mesa, pendientes de decisión:

| Opción | A favor | En contra |
|---|---|---|
| Clave por petición y recuento por listado | Sin proveedor nuevo, sin pérdidas | +130–420 ms por comprobación; el techo puede rebasarse por el factor de concurrencia |
| Almacén con atomicidad real (Upstash Redis, Supabase) | `INCR` atómico de verdad | Añade un proveedor externo al stack, que el spec evitaba a propósito |
| Cuotas best-effort y protección dura solo en el límite nativo | Cero coste añadido | El techo de gasto deja de ser una garantía |

Antes del router se añade a `reservations[requestId]` un importe conservador
calculado con los máximos de entrada/salida de las dos llamadas. Para no depender
de un tokenizer pesado en el edge, el límite superior de tokens de entrada usa
el tamaño UTF-8 en bytes —conservador para un tokenizer byte-level— y añade el
máximo de salida. Importes y precios se convierten a **microdólares enteros** y
se redondean hacia arriba; no se acumulan floats monetarios. Solo se acepta si
`spentMicros + sum(reservations)` no supera `CHAT_DAILY_BUDGET_USD`. Al recibir
`response.completed`, se elimina la reserva y se suma el coste real. Si la
petición termina sin datos de uso, la reserva se convierte en gasto: el límite
prefiere infrautilizar presupuesto a excederlo.

La reserva de gasto se obtiene antes de incrementar la cuota horaria. Si la
cuota ya está agotada, se libera mediante otra escritura condicional. No hay una
transacción entre ambas claves; un fallo entre pasos puede dejar una reserva
conservadora hasta el final del día, pero nunca abrir gasto no reservado.

## 5. Contrato del endpoint

`POST /api/chat` → `text/event-stream`. Los eventos son exactamente los tres
tipos de `ChatChunk` que ya define `frontend/src/types/chat.ts`, más uno de error:

```
event: token    data: {"text":"El cómputo de los días… (ROJ: STS 107/2018)"}
event: sources  data: {"sources":[{…ChatSource}]}
event: done     data: {}
event: error    data: {"code":"upstream_interrupted","message":"…","retryable":true}
```

Cada evento ocupa una sola línea `data:` con JSON y termina en una línea en
blanco. La respuesta incluye `Content-Type: text/event-stream; charset=utf-8`,
`Cache-Control: no-store` y `X-Chat-Protocol: 1`.

`error` es un detalle del protocolo HTTP, **no** un cuarto `ChatChunk`. El cliente
`chat-engine.live.ts` lo convierte en una excepción tipada; `ChatView` ya captura
errores y conserva el texto parcial. Así se respeta el contrato actual sin tocar
`src/types/chat.ts` ni componentes.

El parser no usa `EventSource` porque la petición es `POST`. Lee `fetch().body`,
tolera UTF-8 y eventos partidos entre chunks de red, rechaza versiones de
protocolo desconocidas y exige que el terminal sea exactamente uno de `done` o
`error`. Un EOF sin ninguno es error, no éxito silencioso.

El `extracto` de cada `ChatSource` **no lo escribe el modelo**: se toma del
corpus — la `frases_clave` más afín al foco de la pregunta, o `resumen_criterios`
recortado. El panel de fuentes muestra así texto literal del pipeline, no una
reescritura del modelo.

### Disciplina de la respuesta

El prompt de redacción impone cuatro reglas: responder solo con las fichas
entregadas, citar al menos un marcador `[S<n>]` en cada párrafo sustantivo, no
escribir ROJ/ECLI libres y decir explícitamente que no consta cuando el material
no cubra la pregunta.

Las fichas se etiquetan en servidor (`S1`…`S12`). Corpus e historial se
serializan dentro de secciones delimitadas y se describen como **datos no
confiables**, no como instrucciones; la llamada no dispone de tools.

La salida se amortigua por párrafos:

1. Solo se aceptan marcadores que existan en el conjunto recuperado.
2. El servidor reemplaza cada marcador por el ROJ/ECLI de esa ficha antes de
   emitir el párrafo.
3. Tras cada párrafo que añade una cita, emite un evento `sources` con la lista
   acumulada. Así una interrupción conserva también las fichas de los párrafos
   que el usuario ya vio.
4. Un párrafo sustantivo sin marcador válido se retiene y registra. Si no queda
   contenido válido, se devuelve una respuesta honesta sin fuentes.
5. `sources` contiene únicamente las fichas realmente citadas en texto emitido.

Esto garantiza que **los identificadores mostrados existen y proceden del
corpus**. No demuestra por sí solo que cada inferencia del modelo esté
jurídicamente respaldada; esa calidad se mide con el banco de evaluación de la
sección 10 y se explica en la metodología pública.

#### Consecuencia sobre el streaming, y regla de vaciado

Amortiguar por párrafos **cambia la granularidad de lo que ve el usuario**: ya no
es token a token como en el stub, sino párrafo a párrafo. Es el precio de que el
servidor sustituya `[S<n>]` por el ROJ antes de emitir, y es un intercambio
correcto —un identificador inventado es peor que un streaming menos fluido—, pero
hay que nombrarlo para que no se diagnostique después como un fallo del cliente.
El indicador de escritura de `ChatView` cubre las pausas entre párrafos.

Sin una regla de vaciado, un modelo que emita un único párrafo largo dejaría al
usuario sin nada en pantalla hasta el final, **y el timeout de 15 s sin eventos no
saltaría**: los eventos del proveedor sí están llegando; lo que no ocurre es la
emisión hacia el cliente. Por eso el búfer se vacía en cuanto se cumple lo
primero de:

- fin de párrafo (doble salto de línea);
- 1.200 caracteres acumulados;
- 3 s sin haber emitido nada al cliente.

En los vaciados que no son fin de párrafo se emite todo el texto **hasta el
último marcador ya resuelto**, y el resto queda en el búfer: así nunca se manda a
pantalla un `[S<n>]` sin sustituir ni se parte una cita por la mitad. Existe
además un tope duro de búfer (8 KB) que, de alcanzarse, se trata como respuesta
malformada del modelo y produce `event: error`.

## 6. Errores

| Situación | Respuesta |
|---|---|
| Método distinto de `POST` | `405` |
| Content-Type/body/schema inválido | `400` o `415`, según el caso |
| Pregunta vacía o >500 caracteres | `400` |
| Límite nativo de Netlify agotado | `429` **generado por la plataforma, sin ejecutar la función**: no es SSE ni JSON de este contrato |
| Cuota horaria por IP agotada | `429` emitido por el handler, con `Retry-After` y cuerpo JSON |
| Techo diario alcanzado | `503` con mensaje de cupo, sin llamar a OpenAI |
| Blobs no disponible o CAS agotado | `503`, fail-closed, sin llamar a OpenAI |
| Falta `OPENAI_API_KEY` | `503` |
| Corpus ausente, inválido o con 0 casos | El build falla; defensa runtime `503` |
| Router falla o no valida | Fallback a recuperación léxica; no se aborta la consulta |
| OpenAI falla **antes** del primer token | `502` |
| OpenAI falla **a mitad** del stream | Las cabeceras ya salieron y no hay status que cambiar: se emite `event: error` y el cliente conserva lo escrito con un aviso al pie |
| OpenAI termina `incomplete` o hay EOF sin `done` | `event: error`; nunca se presenta como respuesta completa |
| El usuario pulsa «detener» | El `AbortSignal` cancela el fetch y reduce trabajo posterior; puede existir uso ya generado y facturable |

El fallo a media respuesta es el caso que suele quedar sin cubrir y produce
respuestas truncadas sin explicación; entra en el contrato desde el principio.

Los dos `429` **no son intercambiables** y el cliente tiene que distinguirlos. El
de la plataforma llega antes de que exista función: no lleva el `Content-Type` de
este protocolo, el cuerpo no es JSON propio y la documentación de Netlify no
garantiza `Retry-After`. Por eso `chat-engine.live.ts` comprueba el status y el
`Content-Type` **antes** de intentar parsear SSE, y trata cualquier respuesta que
no sea `text/event-stream` como error tipado a partir del status, sin leer el
cuerpo como si fuera del contrato. Un parser que asuma SSE en cuanto la petición
resuelve fallaría justo en el caso de abuso, que es cuando más importa responder
con algo comprensible.

Las esperas externas tienen límites propios y un deadline previo a cabeceras:
operaciones de Blobs, router y apertura del stream de redacción no pueden sumar
más de 30 s. El router dispone de 8 s y cada operación de Blobs de 2 s; el tiempo
restante queda para reintentos y apertura de redacción. Una vez iniciado el
stream, 15 s sin ningún evento del proveedor se consideran interrupción. Todos
los timeouts usan `AbortSignal` y producen los errores anteriores.

## 7. Build y despliegue

`build-corpus.mjs` pasa a emitir dos artefactos desde el mismo JSONL:

| Artefacto | Destino | Visibilidad |
|---|---|---|
| `corpus.json` (30 KB) | `frontend/public/data/` | Público — índice de la UI, ya existe |
| `_corpus.ts` (~1 MB) | `frontend/netlify/edge-functions/` | No se sirve como asset; sí es visible en el repositorio público |

`_corpus.ts` se genera y se versiona, igual que el fallback público. Esta es una
decisión de disponibilidad, no de confidencialidad: cualquiera puede descargar
el análisis desde el repositorio público. Si ese contenido no debe ser público,
esta arquitectura deja de ser válida y hay que cargar el corpus en un
Deploy Store privado durante un proceso autenticado.

En un clon limpio sin `output/`, el prebuild conserva los dos artefactos
versionados, pero los **valida**. El artefacto privado incluye
`schemaVersion`, `recordCount`, `sourceSha256` y fecha de generación. El build
falla si falta, no parsea, no contiene exactamente el número esperado de
registros o incumple enums/schema; nunca despliega silenciosamente un chat vacío
o un corpus público y otro privado de distinta versión.

Variables nuevas en el panel de Netlify:

| Variable | Uso |
|---|---|
| `OPENAI_API_KEY` (obligatoria) | Llamadas al router y a la redacción |
| `CHAT_IP_SALT` (obligatoria) | Salt del hash de IP de los contadores |
| `CHAT_DAILY_BUDGET_USD` (default `2.00`) | Techo diario reservado antes de cada consulta |

Se añaden `@netlify/edge-functions`, `@netlify/blobs`, el SDK oficial `openai` y
`zod`; `netlify-cli` queda como devDependency y el script `dev:netlify` ejecuta
`netlify dev` con una versión fijada en el lock. Las dependencias npm en Edge
siguen marcadas como beta por Netlify, de modo que el *spike* verifica que el
bundle Deno carga los cuatro paquetes de runtime. Netlify Dev sirve la Edge
Function y un Blob store local; no demuestra los límites ni la latencia del edge
real.

Para poder desarrollar el frontend sin claves, `chatEngineMode` deja de ser una
constante escrita a mano y pasa a resolverse desde
`VITE_CHAT_ENGINE_MODE=stub|live`. El default es **`stub`** en cualquier entorno:
producción solo se activa al configurar explícitamente `live` después de superar
los gates. Esto hace que un deploy incompleto falle hacia contenido marcado como
simulado, no hacia un endpoint roto. La variable no es secreta.

## 8. Tests

La lógica del pipeline Python no se toca. Los módulos TS entran en
`npm run fast-check`; además se añade un test Python de contrato porque el CI
Python ya corre tanto cuando cambia `config.py` como cuando cambia `frontend/**`.
El gate completo de la feature es `make fast-check` **y**
`cd frontend && npm run fast-check && npm run build`.

| Qué | Cómo |
|---|---|
| `_retrieval.ts` | Léxico global, facetas, relajación, unión sin duplicados, orden estable, límites de contexto y fallback si el router falla |
| `_citations.ts` | `[S1]` válido se resuelve al ROJ real; marcador inventado o párrafo sin fuente no se emite; `sources` coincide con el texto |
| Parser SSE del cliente | UTF-8 y eventos partidos entre chunks; error tipado; EOF sin `done`; versión incompatible |
| Validación de entrada | Roles prohibidos, alternancia, tamaños, campos extra y metadatos descartados |
| Cuota horaria | Dos incrementos concurrentes no pierden cuenta; conflictos ETag reintentan; al agotarse, no hay llamada a OpenAI |
| Presupuesto | Reservas concurrentes no superan techo; éxito reconcilia uso; aborto sin uso carga la reserva; Blobs caído falla cerrado |
| API OpenAI | Router con JSON Schema; `store: false`; `response.completed` aporta usage; `incomplete` produce error |
| `build-corpus.mjs` | Genera ambos artefactos y manifiesto; sin `output/` valida fallbacks; corpus ausente, divergente o inválido rompe el build |
| Contratos cruzados | Pytest lee `_chat-config.json` y comprueba modelos/precios/enums contra `config.py`, `model_pricing.py` y `frontend/src/types/chat.ts` |
| Integración local | `netlify dev` + OpenAI mock: POST completo, streaming, abort, 429/503 y cabeceras |

`chat.ts` usa `Netlify.env` y necesita los tipos de `@netlify/edge-functions` como
devDependency, con su propio `tsconfig` (el runtime es Deno, no el DOM). Queda
deliberadamente delgado —solo orquestación— para que la lógica testeable viva en
los módulos puros. El script `typecheck` pasa a ejecutar tanto el proyecto React
como `tsc --noEmit -p tsconfig.edge.json`; añadir el fichero sin integrarlo al
script dejaría el código de producción fuera del gate.

No se añaden llamadas reales a OpenAI al CI. El smoke real es manual, con un
presupuesto pequeño y una clave de desarrollo, igual que los tests LLM de
Python.

## 9. Observabilidad y privacidad

Cada petición genera un `requestId` aleatorio y un único log estructurado al
cerrar. Campos permitidos:

- resultado (`ok`, `no_results`, `rate_limited`, `budget_exhausted`,
  `upstream_error`, `aborted`);
- tiempos de router, recuperación, primer párrafo y total;
- número de candidatos y fuentes emitidas;
- tokens y coste de router/redacción cuando haya `usage`;
- número de párrafos retenidos por citas inválidas;
- intento de CAS y región de ejecución.

No se registran pregunta, historial, texto de respuesta, contenido del corpus,
IP, hash estable de IP ni API key. Los errores externos se reducen a código,
status y `requestId`; no se vuelcan bodies del proveedor. La cuota usa el hash
solo como clave efímera del Blob horario.

Umbrales operativos iniciales:

- cualquier ROJ/ECLI inválido emitido: objetivo **0**, prioridad alta;
- >5 % de `upstream_error` en 15 minutos;
- >10 % de respuestas sin resultados;
- p95 de tiempo al primer párrafo >8 s;
- gasto diario >80 % del techo.

Durante las primeras 24 horas se revisan en los logs/observabilidad de Netlify.
Automatizar alertas o añadir un panel queda fuera de esta iteración.

### Lo que el usuario escribe sale del dominio

No registrar la pregunta en los logs es correcto, pero **no es lo mismo que no
tratarla**: la pregunta viaja a OpenAI en las dos llamadas. Con el motor en stub
no salía nada de Netlify; con el motor real sí, y eso cambia lo que la web tiene
que declarar. Antes de activar `live` hay que cubrir tres cosas, que no son
opcionales ni aplazables a «cuando haya tráfico»:

1. **Aviso de que no es asesoramiento jurídico**, visible junto al chat y no solo
   en una página enlazada. La respuesta sale de un análisis automático de 106
   sentencias y no valora el caso de nadie. Hoy ese papel lo cumple el aviso de
   contenido simulado, que desaparece precisamente al activar `live`: si no se
   sustituye por el aviso legal, la activación **quita** una advertencia en vez de
   cambiarla.
2. **Política de privacidad** que diga que el texto de la consulta se envía a
   OpenAI como encargado del tratamiento, que se manda con `store: false` y que no
   se conserva en el servidor. Los criterios de residencia fiscal invitan a
   escribir datos personales —dónde vive uno, dónde está su familia—, así que
   asumir que las consultas serán anónimas es una apuesta perdida de antemano.
3. **Aviso en la caja de entrada** de no incluir datos identificativos. Es la
   mitigación más barata y la única que actúa antes de que el dato salga.

Los dos primeros puntos son texto de producto y encajan con
`sentencias/AVISO_LEGAL.md` y con la página de metodología; el tercero es una
línea de UI. Ninguno es trabajo de backend, y por eso mismo se cuelan: quedan
anotados aquí como **condición de la fase 3**, no como sugerencia.

## 10. Plan de entrega y criterios de aceptación

### Fase 0 — *spike* de plataforma — EJECUTADA (2026-07-29)

Ejecutada contra un Deploy Preview con un corpus sintético de 891 KB, el tamaño
que tendrá el real. Resultados completos y metodología en
[`docs/operations/NETLIFY_EDGE.md`](../../operations/NETLIFY_EDGE.md).

| # | Criterio | Objetivo | Medido | |
|---|---|---|---|---|
| 1 | Carga de `openai`, `zod` y `@netlify/blobs` en Deno | los tres | los tres `true` | ✅ |
| 2 | p95 de CPU propio en frío y caliente | < 40 ms | 15,3 ms | ✅ |
| 3 | Streaming de más de 10 s sin corte | > 10 s | 19,87 s | ✅ |
| 4 | Cabeceras dentro del límite | < 10 s | 0,30 s | ✅ |
| 5 | CAS correcto con 20 peticiones concurrentes | exacto | incrementos perdidos | ❌ |

**La decisión de runtime se confirma**: los criterios 1 a 4 validan que las Edge
Functions soportan esta arquitectura. El criterio 5 no invalida el runtime, sino
el mecanismo de estado, y su alternativa está validada en el mismo spike.

Dos correcciones que el spike obligó a hacer sobre este documento:

- El reparto del corpus en dos niveles **no es una optimización, es obligatorio**:
  parsear las 106 fichas en el arranque da 46,6 ms en frío y llega a 53,9 ms, por
  encima del límite duro de 50.
- Los módulos compartidos van en `lib/`, no en la raíz con prefijo `_`.

### Fase 0b — decisión sobre el estado de cuotas y presupuesto (BLOQUEANTE)

Antes de la fase 1 hay que elegir entre las tres opciones de la sección 4. La
implementación de `budget.ts` depende por completo de esa decisión, y con ella la
única garantía que impide que el endpoint gaste sin techo.

### Fase 1 — implementación detrás de `stub`

Se desarrolla con TDD, se ejecutan `npm run fast-check` y `npm run build`, y se
prueba el flujo completo con OpenAI mock. Producción sigue en
`VITE_CHAT_ENGINE_MODE=stub`.

`netlify dev` **no funciona en este proyecto**: el CLI arrastra `ts-api-utils` vía
`precinct`, incompatible con el TypeScript 7 del repositorio. El workaround
—instalar el CLI fuera del árbol— está en `NETLIFY_EDGE.md`.

### Fase 2 — evaluación

Se crea un banco versionado de al menos 40 preguntas representativas: 183 días,
ausencias, centro de intereses, familia, CDI, carga de prueba, pruebas concretas,
preguntas comparativas, fuera de corpus y entradas adversariales. Cada caso
anota sentencias esperadas y, cuando aplique, hechos que la respuesta debe o no
debe afirmar.

Los gates se separan en dos grupos, porque tienen coste y naturaleza muy
distintos y mezclarlos bloquea la entrega sin ganar seguridad.

**Bloqueantes (seguridad y corrección).** Binarios, automatizables y baratos: o
pasan o no se activa.

- 100 % de identificadores emitidos pertenecen al corpus recuperado;
- 0 párrafos sustantivos emitidos sin una fuente válida;
- techo diario no superado bajo el test concurrente;
- 0 llamadas a OpenAI cuando validación, cuota, presupuesto o Blobs fallan;
- comportamiento correcto en los casos **fuera de corpus** y **adversariales**:
  responde que no consta y no obedece instrucciones inyectadas en la pregunta o
  en el propio corpus;
- p95 al primer párrafo <8 s y p95 total <30 s en Deploy Preview;
- los tres requisitos legales y de privacidad de la sección 9.

Para este grupo basta un núcleo de **12–15 preguntas**, en su mayoría negativas o
adversariales: es donde el fallo es grave y la respuesta correcta es inequívoca.

**Medidos, no bloqueantes (calidad de recuperación).** `recall@12` ≥90 % sobre 40
preguntas exige etiquetar a mano qué sentencias «deberían» salir en cada una, y
para una pregunta abierta como «¿qué pruebas convencen sobre el centro de
intereses?» esa verdad de referencia es en buena parte opinable. El riesgo no es
que el umbral sea exigente: es que **un gate caro y difuso acabe rebajándose para
poder lanzar**, que es la peor forma posible de tener un gate.

El banco de 40 preguntas se construye igual, se ejecuta igual y su resultado se
guarda como artefacto versionado —incluida la comparación contra el baseline
léxico puro, que sí puede ganar al conjunto reranqueado dentro del top 12—, pero
se publica como **línea base medida**, no como condición de activación. A partir
de ahí funciona como test de regresión: un cambio que empeore el recall respecto
a la línea base anterior sí bloquea.

La revisión humana de 20 respuestas se mantiene, y también fuera del camino
crítico: es un muestreo de calidad jurídica cuyo resultado alimenta el prompt y
el banco, no un semáforo de despliegue. Lo que sí bloquea es lo que esa revisión
pueda destapar como fallo de seguridad, que ya está en el primer grupo.

Los umbrales se calculan siempre sobre el banco completo y se guardan como
artefacto; no se aprueba con ejemplos escogidos a mano.

### Fase 3 — activación y rollback

Tras los gates, se configura `VITE_CHAT_ENGINE_MODE=live` y se despliega. Durante
las primeras 24 horas se usa un presupuesto bajo y se revisan errores, latencia,
respuestas sin resultados y gasto. El rollback es cambiar la variable a `stub`
y redesplegar; el stub y su aviso se conservan precisamente para este camino.

## 11. Fuera de alcance

Sin embeddings ni base de datos vectorial, sin cuentas de usuario, sin historial
en servidor, sin caché de respuestas y sin panel de métricas. Con 106 sentencias
ninguna de esas piezas aporta nada hoy, y todas se pueden añadir después sin
rehacer lo anterior.

La API FastAPI (`api/main.py`) sigue siendo la vía para analizar PDFs nuevos y no
se modifica. El pipeline Python tampoco.

## 12. Riesgos abiertos

Lo que un revisor debería atacar primero:

1. **~~El presupuesto de 50 ms de CPU puede invalidar Edge.~~ RESUELTO.** Medido
   el 2026-07-29: p95 de 15,3 ms y ninguna petición por encima de 50 ms con el
   corpus en dos niveles. Queda un margen de 9,4 ms en el peor caso medido, y la
   implementación real hará más trabajo que el spike, así que conviene volver a
   medir al cerrar la fase 1.
2. **La recuperación puede tener recall insuficiente sin embeddings.** La unión
   léxico/facetas elimina el router como punto único de exclusión, pero no
   garantiza semántica. El banco de evaluación decide con datos si 106
   documentos siguen justificando el diseño simple.
3. **El compare-and-swap de Blobs no es atómico. CONFIRMADO Y BLOQUEANTE.** No
   es un riesgo de latencia como se pensaba, es de corrección: cinco peticiones
   concurrentes dejaron un contador de 5 incrementos en 2, y todas creyeron haber
   escrito. La alternativa de clave por petición está validada pero cuesta
   130–420 ms por comprobación. Es la decisión de la fase 0b y bloquea la
   implementación de `budget.ts`.
4. **El techo de gasto es global, no por usuario**: un solo abusador que respete
   el límite por IP puede agotar el cupo diario de todos. Aceptado
   conscientemente para una web de nicho; si ocurre, el siguiente paso es un
   *challenge* de Cloudflare en `/api/chat`, que ya está delante del dominio.
5. **El corpus embebido es público en GitHub.** «No servido como asset» evita la
   descarga casual desde la web, no aporta confidencialidad. Si cambia el
   criterio legal o de producto, hay que moverlo a almacenamiento privado.
6. **Una cita válida no prueba entailment.** Los marcadores impiden inventar
   identificadores, pero el modelo aún puede atribuir a una sentencia algo que
   la ficha no respalda. Evaluación humana, prompt cerrado y transparencia en
   metodología reducen el riesgo; no lo eliminan.
7. **Sacar el recall del camino crítico traslada riesgo al post-lanzamiento.** Es
   una decisión consciente: los gates bloqueantes cubren que no se inventen
   identificadores ni se responda fuera del corpus, pero no que se responda
   *bien*. Se puede lanzar con un recall mediocre y no enterarse hasta leer las
   conversaciones. La contrapartida es que el umbral bloqueante que sí queda es
   barato de cumplir honestamente, en vez de caro y susceptible de rebajarse. Si
   el muestreo de las primeras semanas revela recuperación pobre, la respuesta
   correcta es reabrir la decisión de embeddings del riesgo 2, no relajar nada.
