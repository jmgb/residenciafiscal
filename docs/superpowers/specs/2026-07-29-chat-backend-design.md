# Backend del chat de residenciafiscal.org — Diseño

**Fecha**: 2026-07-29
**Estado**: aprobado
**Continúa**: [`2026-07-29-frontend-chatbot-design.md`](2026-07-29-frontend-chatbot-design.md), que dejó el backend explícitamente fuera de alcance

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
resultado_final                    GANA_AEAT | GANA_CONTRIBUYENTE | PARCIAL | RETROACCION | INADMISION
frases_clave                       [ { tema, pagina, texto } ]
confianza_extraccion               ALTA | MEDIA | BAJA
```

Los enums canónicos (7 criterios `CRIT_*`, 12 categorías de prueba, 5 resultados)
viven en `config.py` y se replican en `frontend/src/types/chat.ts`.

### Restricciones de plataforma verificadas

Comprobadas en la documentación de Netlify el 2026-07-29. **Condicionan el diseño
entero**, así que quien revise esto debería cuestionarlas si tiene datos mejores.

| Runtime | Límite | Consecuencia |
|---|---|---|
| Functions con streaming | **10 s de ejecución** (no solo hasta el primer byte) + 20 MB de respuesta | Insuficiente: router + ~700 tokens de redacción se van a 15–25 s. Cortaría a media frase. |
| Functions estándar | 10 s, ampliable a 26 s bajo demanda en planes Pro/Enterprise | Mismo problema, y depende del plan. |
| Background Functions | 15 min | No sirven: devuelven `202` y no pueden streamear al cliente. |
| **Edge Functions** | **50 ms de CPU propio**, 40 s para cabeceras, 20 MB de bundle, streaming soportado | La espera a OpenAI **no** cuenta como CPU. Es el único runtime de Netlify donde esto cabe. |

Además:

- Netlify **no** ofrece rate limiting declarativo para Edge Functions (el `config`
  admite `path`, `excludedPath`, `pattern`, `method`, `header`, `cache`, `onError`
  y poco más). Hay que implementarlo a mano.
- **Netlify Blobs sí es accesible desde Edge Functions**, lo que da estado
  persistente sin añadir ningún proveedor externo al stack.
- Las Edge Functions se evalúan **antes** que los redirects, así que el catch-all
  `/* → /index.html` de `netlify.toml` no intercepta la ruta del endpoint.
- La CSP de `netlify.toml` ya incluye `connect-src 'self'`: al ser el mismo
  origen, **no hay que tocarla**.
- El `ignore` de `netlify.toml` solo reconstruye si cambia `frontend/**` o el
  propio `netlify.toml`; las Edge Functions viven bajo `frontend/`, así que encaja.

## 3. Decisiones tomadas

| Decisión | Elección | Motivo | Alternativas descartadas |
|---|---|---|---|
| Dónde corre | Edge Function en el mismo repo | Único runtime de Netlify donde cabe una respuesta larga en streaming. Mismo deploy, mismo origen, CSP intacta. | Function normal (10 s), ampliar la FastAPI (exige hosting + CORS + dominio), Cloudflare Workers (otro origen), Supabase Edge (proveedor extra) |
| Recuperación | Router LLM barato → filtro determinista | El corpus ya viene estructurado por el pipeline: las facetas hacen el trabajo pesado y el router solo traduce lenguaje natural a facetas | Solo léxico (falla si la pregunta no usa el vocabulario del corpus), tool use (latencia variable), embeddings (sobreingeniería para 106 documentos) |
| Corpus del servidor | Embebido en el bundle, no público | Cero latencia de red, y el análisis completo no queda descargable de un tirón | Publicarlo como estático, publicar una versión recortada |
| Gasto y abuso | Rate limit por IP + techo de gasto diario | El endpoint es la única pieza que cuesta dinero y está abierta | Solo límites blandos (sin contador propio), Upstash/Supabase (proveedor extra) |
| Estado de los contadores | Netlify Blobs | Persistente y sobrevive a cold starts sin añadir proveedor | En memoria del isolate (inservible: hay muchos isolates en muchas regiones) |
| Fiabilidad | Cerrada al corpus + validación de ROJ | Alucinar una sentencia es el peor fallo posible en una web jurídica | Solo instrucciones en el prompt, permitir conocimiento general |

### Modelos

| Paso | Modelo | Por qué |
|---|---|---|
| Router | `gpt-5.6-luna` | Clasificación con salida JSON estricta sobre ~500 tokens de entrada: ~$0.0003 por pregunta |
| Redacción | `gpt-5.6-luna` (`GPT_5_MINI`) | Mismo modelo que usa el pipeline por defecto; buena relación calidad/precio con ~25k de contexto |

Ambos pasos usan el mismo modelo **porque hoy no hay uno más barato disponible**:
en `config.py:43`, `GPT_5_NANO` es un alias de `gpt-5.6-luna`, igual que
`GPT_5_MINI`. No es una decisión de diseño, es el catálogo que hay. El router es
un paso barato por su tamaño de entrada, no por el modelo, y es el sitio donde
cambiar el ID el día que exista un modelo de clasificación más económico.

Las Edge Functions **no importan `config.py`**: los IDs de modelo y los enums
(`CRIT_*`, categorías de prueba, resultados) se duplican en TypeScript, igual que
ya ocurre en `frontend/src/types/chat.ts`. Es duplicación consciente entre dos
runtimes; el gate que la vigila es que el corpus generado se valide contra los
enums del TS en el `prebuild`.

**Coste esperado**: ~$0.008 por pregunta. El techo de $2/día son unas 250 preguntas.

## 4. Arquitectura

### Piezas

```
frontend/
├── netlify/
│   └── edge-functions/
│       ├── chat.ts             # endpoint: orquesta y streamea
│       ├── _corpus.ts          # GENERADO: índice + fichas (gitignored, con fallback versionado)
│       ├── _retrieval.ts       # filtro determinista — puro, sin globals de Deno
│       ├── _router.ts          # llamada al router + validación del JSON
│       ├── _limits.ts          # rate limit por IP y techo de gasto (Netlify Blobs)
│       └── _sse.ts             # construcción de eventos SSE
├── scripts/
│   └── build-corpus.mjs        # AMPLIADO: emite corpus público + corpus del servidor
└── src/lib/
    ├── chat-engine.ts          # chatEngineMode → 'live'
    ├── chat-engine.live.ts     # NUEVO: cliente SSE que cumple ChatEngine
    └── chat-engine.stub.ts     # se conserva para tests y dev sin claves
```

Netlify no publica como endpoint los ficheros con prefijo `_`: son módulos
internos del bundle.

Declaración en `netlify.toml` (raíz del repo):

```toml
[[edge_functions]]
  path = "/api/chat"
  function = "chat"
```

### Flujo de una pregunta

```
POST /api/chat  { messages: [...] }
  │
  ├─ 1. Guardarraíles (sin coste)
  │     pregunta ≤ 500 caracteres · historial recortado a los 6 últimos mensajes
  │     rate limit por IP · techo de gasto diario
  │
  ├─ 2. Router — gpt-5-nano, JSON estricto, sin streaming (~1 s, ~$0.0002)
  │     { criterios[], organo, resultado, anios[], categorias_prueba[],
  │       foco, terminos[] }
  │
  ├─ 3. Recuperación — determinista, sin red
  │     filtro duro por facetas → puntuación léxica → top 12
  │
  ├─ 4a. ¿0 resultados? → respuesta honesta, sin segunda llamada, sin gasto
  │
  ├─ 4b. Redacción — gpt-5.6-luna en streaming (~25k in / ~700 out, ~$0.008)
  │      Los tokens salen hacia el cliente conforme llegan.
  │
  └─ 5. Al cerrar el stream: se extraen los ROJ citados en el texto, se
        intersectan con el corpus y se emite el evento `sources`.
        Los ROJ inventados se descartan y se registran en el log.
```

### Presupuesto de CPU (50 ms)

Es el único límite de la plataforma que puede mordernos, así que el corpus
generado va en **dos niveles**:

- **Índice compacto** (~120 KB): identificadores, órgano, año, criterios
  detectados y decisivos, resultado, categorías admitidas/rechazadas, países, y
  los términos ya normalizados para la puntuación léxica. Se parsea **una vez**
  al arrancar el isolate y se reutiliza en las peticiones calientes.
- **Fichas completas**: un `Record<archivo, string>` donde cada valor es la ficha
  serializada. Solo se hace `JSON.parse` de las ~12 seleccionadas.

Ambos se emiten como `JSON.parse("…")` sobre literales de cadena, no como
literales de objeto: para ~1 MB, V8 lo parsea bastante más rápido.

Filtrar y puntuar 106 fichas es aritmética trivial; el coste real sería parsear
888 KB en cada petición, y con este reparto no ocurre.

### Recuperación (`_retrieval.ts`)

Dos fases sobre el índice:

1. **Filtro duro** por las facetas que devuelva el router (criterios, órgano,
   resultado, rango de años, categorías de prueba, país del CDI). Facetas
   ausentes no filtran. Si el resultado queda vacío, se relajan las facetas menos
   específicas antes de rendirse.
2. **Puntuación léxica** de los términos del router sobre `resumen_criterios`,
   `razonamiento_residencia`, `pruebas[].detalle` y `frases_clave[].texto`, con
   refuerzo si el criterio buscado aparece en `Criterio_decisivo` y no solo en
   `Criterios_residencia_detectados`.

Se devuelven las 12 mejores. El módulo es **puro y sin globals de Deno**, para
que se pueda probar con Vitest como cualquier otro módulo del frontend.

### Estado en Netlify Blobs

| Clave | Contenido | Uso |
|---|---|---|
| `rl:<hash(ip)>` | contador + inicio de ventana | 10 preguntas/hora por IP |
| `spend:<YYYY-MM-DD>` | coste acumulado del día | techo de $2 |

La IP se guarda **hasheada con un salt**; nunca en claro. El registro caduca al
rotar la ventana: es un contador, no un log de visitantes.

El coste se obtiene de `stream_options: { include_usage: true }`, que hace que
OpenAI incluya el bloque `usage` en el último chunk del stream. Así se contabiliza
el gasto real y no una estimación.

## 5. Contrato del endpoint

`POST /api/chat` → `text/event-stream`. Los eventos son exactamente los tres
tipos de `ChatChunk` que ya define `frontend/src/types/chat.ts`, más uno de error:

```
event: token    data: {"text":"El cómputo de los "}
event: sources  data: {"sources":[{…ChatSource}]}
event: done     data: {}
event: error    data: {"code":"upstream","message":"…"}
```

Sustituir el stub no obliga a tocar nada fuera de `src/lib/`, que es la promesa
que hace el comentario de cabecera de `chat-engine.ts`.

El `extracto` de cada `ChatSource` **no lo escribe el modelo**: se toma del
corpus — la `frases_clave` más afín al foco de la pregunta, o `resumen_criterios`
recortado. El panel de fuentes muestra así texto literal del pipeline, no una
reescritura del modelo.

### Disciplina de la respuesta

El *system prompt* de redacción impone tres reglas: responder solo con las
sentencias entregadas, citar el ROJ tras cada afirmación, y decir explícitamente
que no consta cuando el material no lo cubra.

Sobre eso hay una **validación determinista**: se extraen los ROJ del texto
generado, se intersectan con el corpus, y los que no existan se eliminan del
panel de fuentes y se registran. Es la única garantía que no depende de que el
modelo obedezca.

## 6. Errores

| Situación | Respuesta |
|---|---|
| Pregunta vacía o >500 caracteres | `400` |
| Cuota por IP agotada | `429` + `Retry-After` |
| Techo diario alcanzado | `503` con mensaje de cupo, sin llamar a OpenAI |
| Falta `OPENAI_API_KEY` | `503` |
| OpenAI falla **antes** del primer token | `502` |
| OpenAI falla **a mitad** del stream | Las cabeceras ya salieron y no hay status que cambiar: se emite `event: error` y el cliente conserva lo escrito con un aviso al pie |
| El usuario pulsa «detener» | El `AbortSignal` corta el `fetch` a OpenAI, así que se deja de pagar de inmediato |

El fallo a media respuesta es el caso que suele quedar sin cubrir y produce
respuestas truncadas sin explicación; entra en el contrato desde el principio.

## 7. Build y despliegue

`build-corpus.mjs` pasa a emitir dos artefactos desde el mismo JSONL:

| Artefacto | Destino | Visibilidad |
|---|---|---|
| `corpus.json` (30 KB) | `frontend/public/data/` | Público — índice de la UI, ya existe |
| `_corpus.ts` (~1 MB) | `frontend/netlify/edge-functions/` | Solo servidor |

El fallback versionado que ya existe para el corpus público **se replica para el
del servidor**: sin él, un clon limpio sin `output/` construiría un endpoint con
corpus vacío. Es la misma razón por la que hoy `corpus.json` está en git.

Variables nuevas en el panel de Netlify, ambas obligatorias:

| Variable | Uso |
|---|---|
| `OPENAI_API_KEY` | Llamadas al router y a la redacción |
| `CHAT_IP_SALT` | Salt del hash de IP de los contadores |

`netlify dev` sirve la Edge Function en local contra el mismo código.

Para poder desarrollar el frontend sin claves, `chatEngineMode` deja de ser una
constante escrita a mano y pasa a resolverse desde `import.meta.env`, con
`'live'` por defecto: solo un `.env.local` con la variable de escape puesta a
`stub` devuelve el motor simulado. El comportamiento en producción es idéntico al
de fijar `'live'` a mano, y el aviso de contenido simulado sigue apagándose solo.

## 8. Tests

Todo entra en `npm run fast-check`; el gate de Python no se toca.

| Qué | Cómo |
|---|---|
| `_retrieval.ts` | Vitest directo (módulo puro): facetas que filtran, orden de la puntuación, corpus vacío, filtro sin resultados, relajación de facetas |
| Validación de ROJ | Texto con un ROJ inventado → se cae del panel de fuentes |
| Parser SSE del cliente | Eventos partidos entre dos chunks de red, que es donde fallan estos parsers |
| Guardarraíles | Pregunta larga → 400; contador agotado → 429; techo → 503 sin llamada a OpenAI |
| `build-corpus.mjs` | Genera ambos artefactos; sin `output/` conserva los dos fallbacks |

`chat.ts` usa `Netlify.env` y necesita los tipos de `@netlify/edge-functions` como
devDependency, con su propio `tsconfig` (el runtime es Deno, no el DOM). Queda
deliberadamente delgado —solo orquestación— para que la lógica testeable viva en
los módulos puros.

## 9. Fuera de alcance

Sin embeddings ni base de datos vectorial, sin cuentas de usuario, sin historial
en servidor, sin caché de respuestas y sin panel de métricas. Con 106 sentencias
ninguna de esas piezas aporta nada hoy, y todas se pueden añadir después sin
rehacer lo anterior.

La API FastAPI (`api/main.py`) sigue siendo la vía para analizar PDFs nuevos y no
se modifica. El pipeline Python tampoco.

## 10. Riesgos abiertos

Lo que un revisor debería atacar primero:

1. **El presupuesto de 50 ms de CPU no está medido**, solo razonado. Si el
   arranque del isolate se pasa, el plan B es adelgazar el índice (menos términos
   normalizados) o mover la selección final a un segundo nivel de fichas más
   pequeñas. Conviene instrumentarlo en la primera versión desplegada.
2. **El router es un punto único de fallo de calidad**: si clasifica mal las
   facetas, el filtro duro puede dejar fuera la sentencia buena y el modelo
   responderá «no consta» con seguridad injustificada. La relajación de facetas
   lo mitiga, pero no lo resuelve; hace falta un banco de preguntas reales para
   medirlo.
3. **Netlify Blobs desde el edge añade latencia de red** antes del primer token
   (dos operaciones por petición). Si pesa, los contadores pueden pasar a
   escribirse de forma diferida tras responder.
4. **El techo de gasto es global, no por usuario**: un solo abusador que respete
   el límite por IP puede agotar el cupo diario de todos. Aceptado
   conscientemente para una web de nicho; si ocurre, el siguiente paso es un
   *challenge* de Cloudflare en `/api/chat`, que ya está delante del dominio.
5. **Los 10 s de las Functions con streaming son documentación, no medición.**
   Si resultara que el límite se aplica solo al primer byte, la opción de la
   Function normal volvería a estar sobre la mesa y sería más convencional que
   Deno.
