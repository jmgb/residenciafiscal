# Plan de migración del chat A/B a Alfredo

**Estado:** propuesta ejecutable; no autoriza todavía el corte de producción.
La ejecución está **pausada por prioridad** desde el 4 de agosto de 2026: el
estado real, lo que quedó corriendo y la ruta de reanudación están en
[`CHAT_ALFREDO_STATE.md`](CHAT_ALFREDO_STATE.md).
**Fecha:** 2026-08-04.
**Baseline de aplicación:** pendiente de congelar en la fase 0. `34fe334`
(`fix(chat): harden A/B evidence responses`) es el punto de partida del análisis,
no un baseline válido: hay trabajo posterior sobre los propios ficheros que la
migración porta —`composition.ts`, `contracts.ts`, `runtime.ts` y
`chat-sse-protocol.ts`—. El baseline se fija sobre un commit ya en `main`, con
árbol limpio, y se registra junto al deploy de Netlify que lo sirve.
**Alcance:** mover el runtime síncrono de `POST /api/chat` desde una Netlify
Function TypeScript a un servicio FastAPI aislado en el VPS Alfredo.

Este repositorio es público. La documentación forma parte del producto y se
actualiza en la misma entrega que cada cambio de comportamiento. Ningún
documento, fixture, ejemplo, captura o log versionado puede revelar valores de
credenciales, IP, hostname privado, URL interna real, identificadores de cuenta,
rutas privadas del host, inventario de red o material de autenticación.

## 1. Resultado buscado

Al terminar la migración:

- el navegador seguirá llamando al mismo endpoint `/api/chat`;
- una fachada same-origin descartará abuso evidente, firmará la petición y
  transmitirá el stream, pero no contendrá lógica jurídica, cuota autoritativa
  ni credenciales de proveedores;
- FastAPI en Alfredo será el único composition root del chat A/B;
- A redactará mediante la fachada `gpt_request` →
  `GatewayChatWriter(get_gateway())` → `neutral-llm-gateway`;
- B seguirá usando Gemini File Search directamente mientras el gateway no
  soporte esa tool;
- Supabase conservará exactamente la misma reserva, persistencia, coste,
  diagnósticos e idempotencia visibles en la V1;
- A podrá declarar una cadena ordenada de modelos en el gateway; nunca habrá
  fallback cruzado ni cruce de contexto entre A y B;
- la implementación TypeScript del dominio se retirará después de una ventana
  de rollback, evitando dos runtimes activos a largo plazo.

Arquitectura objetivo inicial:

```text
Navegador
  POST /api/chat
        │
        ▼
Proxy same-origin fino
  descarte de abuso + tamaño + firma HMAC + streaming
        │
        ▼
Alfredo / residenciafiscal-chat
  FastAPI + límites de concurrencia + observabilidad
        │
        ├── reserva/idempotencia ──────────────────────── Supabase
        │
        ├── A: corpus v3 → GatewayChatWriter → OpenAI
        │
        └── B: Gemini File Search → verificación literal
        │
        ▼
  persistencia terminal → SSE protocolo 2 → navegador
```

La primera opción de proxy será la Edge Function ya prototipada en
`frontend/netlify/prototypes/chat-fastapi-edge-v2.ts`. La fase 0 debe demostrar en
Deploy Preview que mantiene un stream sintético de 90 segundos. Si ese gate
falla, se usará un Cloudflare Worker o Tunnel para `/api/chat`; no se reducirá el
timeout del backend para encajar artificialmente en Netlify.

### Frontera de propiedad

Este repositorio es público y el inventario de Alfredo no lo es. La migración
mantiene la misma separación que ya usa Deep Research:

- **Aquí** viven el código del runtime, el corpus derivado, los tests, el
  contrato del protocolo, el runbook parametrizado y el instalador reproducible.
- **En el registro operativo privado** viven hostname, DNS, rutas del host,
  unidades reales, reglas de red y localización de secretos.

El artefacto que cruza esa frontera se verifica por hash antes de activarse, y
el host no ejecuta nada que no proceda de un artefacto declarado.

## 2. Motivo de la migración

La V1 Netlify-only permitió lanzar el comparador con un único despliegue, pero
ha creado una segunda frontera de proveedor:

- A construye la petición y el schema estricto en TypeScript aunque el gateway
  Python ya resuelve esa responsabilidad;
- precios, errores, reintentos y capacidades de modelo deben mantenerse en dos
  runtimes;
- el límite de 60 segundos restringe razonamiento, reintentos y evolución;
- el plan Legacy de Netlify no permite limitar las credenciales al scope de
  Functions;
- un fallo de contrato de schema en producción mostró un coste real de esta
  duplicación. La fase 0 debe enlazar la incidencia concreta —commit de
  corrección y fecha— o retirar la afirmación: hoy no está registrada en ningún
  documento ni test de este repositorio, y un motivo sin evidencia no sostiene
  una migración.

Alfredo ya dispone de ejecución autenticada, Docker, callbacks HMAC y operación
para Deep Research. Eso reduce el trabajo de infraestructura, pero el chat
síncrono debe vivir en un servicio y contenedor propios: nunca compartirá
límites de CPU, memoria, cola o ciclo de vida con los jobs agentivos.

## 3. Invariantes que la migración no puede cambiar

1. A y B reciben la misma pregunta y empiezan en paralelo.
2. Ninguna estrategia recibe fuentes, candidatos, texto o estado de la otra.
3. La UI presenta A antes que B aunque B termine primero.
4. Una respuesta sustantiva sin evidencia verificable no se publica.
5. El coste incurrido se registra incluso si el proveedor o un gate posterior
   falla.
6. No existe fallback cruzado ni fallback silencioso: A solo usa los modelos
   explícitamente declarados en su cadena de `FallbackPolicy`.
7. El retry de B usa como máximo un segundo intento con el mismo modelo y store,
   bajo un presupuesto global, y suma ambos consumos.
8. Solo sale del navegador la última pregunta autosuficiente; el historial
   anterior sigue siendo local.
9. Los logs, Sentry y métricas nunca contienen pregunta, respuesta, citas ni
   credenciales.
10. Los PDF, páginas verbatim y corpus montados son inmutables y verifican sus
    hashes antes de aceptar tráfico.
11. El protocolo público continúa siendo `X-Chat-Protocol: 2` y mantiene los
    eventos y shapes vigentes.
12. El corte no exige una migración destructiva de base de datos.
13. El artefacto desplegado no contiene los PDF del CENDOJ ni ningún otro corpus
    de fuente con condiciones de reutilización propias. El runtime necesita el
    caso v3 y las páginas verbatim derivadas, no los originales; los PDF solo
    intervienen en operaciones offline —store de File Search y verificación de
    citas— y su redistribución dentro de una imagen sería una decisión legal
    distinta, no un detalle de empaquetado.
14. El contrato del ledger de coste no cambia. Los timers diarios que resumen y
    vigilan la frescura del coste leen Supabase y no saben quién escribió la
    fila; si la migración altera nombres, unidades o momento de escritura, deja
    de haber vigilancia de coste.
15. Alfredo nunca abre una conexión directa con el navegador ni aparece en
    ninguna respuesta, cabecera o error visible desde el cliente.

## 4. Fuera de alcance

- cambiar Luna, Gemini o sus esfuerzos por motivos de calidad;
- cambiar la cadena de fallback o sus modelos por motivos de calidad;
- mezclar el piloto Deep Research C con las respuestas rápidas A/B;
- rediseñar la experiencia visual o el voto ciego;
- añadir contexto multi-turn;
- mover backups, retención u otros timers a otro servidor;
- retirar Netlify como hosting del frontend;
- mover en esta primera migración endpoints independientes como Deep Research.

Los endpoints de voto pueden permanecer temporalmente en Netlify porque no
ejecutan modelos ni duplican el dominio del chat. Su migración, si se desea, se
decidirá después del corte de `/api/chat`.

## 5. Diferencias que deben cerrarse

| Capacidad | V1 TypeScript vigente | Prototipo Python actual | Trabajo requerido |
|---|---|---|---|
| Entrada HTTP | 500 caracteres, IDs, país, límite de bytes | 8.000 caracteres y contrato menor | Igualar exactamente la V1 |
| Cuota e idempotencia | RPC transaccionales en Supabase | No integradas | Portar sin cambiar semántica |
| Persistencia | pregunta, A/B, claims, citas, coste y diagnósticos | informe y JSONL locales | Usar las RPC vigentes |
| A | prompt v4, recuperación corregida | implementación Python anterior | Paridad de prompt, evidencia y gates |
| OpenAI | adaptador Node directo | `neutral-llm-gateway` | Hacer Python canónico |
| B | prompt v8, tool forzada y retry acotado | responder Python anterior | Portar reglas y coste acumulado |
| Store | rollout 106 con metadata de autoridad | recibo antiguo por defecto | Activar recibo authority-v2 |
| Protocolo | claims y diagnósticos completos | serialización parcial | Golden tests compartidos |
| Errores | aislamiento y texto público seguro | error terminal más genérico | Paridad exacta |
| Observabilidad | Sentry + eventos + Supabase | logs JSONL | Instrumentar FastAPI sin PII |
| Deadline | 52 s por límite de plataforma | sin presupuesto canónico | Definir presupuesto y cancelación |
| Despliegue | Netlify desde Git | proceso local | Artefacto verificado por hash y rollback |
| Rate limit | en la Function, mismo runtime | inexistente | Decidir dónde es autoritativo (D5) |
| Errores en producción | tres runtimes Sentry declarados | sin Sentry | Declarar el cuarto runtime y su autofix |
| Vigilancia externa | UptimeRobot sobre home y corpus | ninguna | Monitor del health del backend |
| Desarrollo local | `netlify dev` o build del frontend | `make dev` | Definir topología local (D8) |

## 6. Decisiones previas obligatorias

Estas decisiones deben quedar escritas en un ADR antes de tocar producción.

### D1. Proxy público

**Propuesta:** reutilizar primero la Edge Function, porque mantiene same-origin y
contrato ya probado. Gate: stream sintético de 90 segundos en Deploy Preview,
tres veces consecutivas.

Parte del trabajo ya está medida y no debe repetirse a ciegas.
[`docs/operations/NETLIFY_EDGE.md`](../operations/NETLIFY_EDGE.md) registra el
spike del 2026-07-29 contra un Deploy Preview real: cabeceras en 0,30 s —muy por
debajo del límite de 40 s— y un stream completo de 19,87 s, imposible en una
Function estándar. Lo que **no** está medido es el tramo de 20 a 90 segundos, que
es exactamente lo que esta migración necesita. El gate se limita a eso.

Dos hallazgos de aquel spike cambian de signo en esta arquitectura y hay que
declararlo:

- El p95 de CPU de 15,3 ms se midió con un corpus de 891 KB embebido. Aquí la
  Edge Function no lleva corpus, así que el límite de 50 ms de CPU deja de ser la
  restricción dominante.
- El compare-and-swap de Netlify Blobs **no es atómico**: cinco escrituras
  concurrentes dejaron el contador en 2. Eso invalida cualquier cuota
  autoritativa en el borde y obliga a decidir D5 antes de escribir la fachada.

Si el gate falla, elegir Cloudflare Worker/Tunnel; el dominio ya está en
Cloudflare, así que la alternativa no introduce un proveedor nuevo. El navegador
nunca llamará a un hostname de Alfredo ni conocerá secretos internos.

**Trampa operativa conocida:** `netlify dev` y `netlify deploy --build` no
arrancan en este árbol por un choque de `ts-api-utils` con el TypeScript
hoisteado. El workaround documentado —instalar el CLI fuera del proyecto— es
requisito de cualquier tarea de fases 0, 5 y 6 que despliegue un preview.

### D2. Credencial de Supabase

**Propuesta:** no copiar `SUPABASE_SECRET_KEY` al nuevo contenedor. Crear un rol
Postgres específico, representado públicamente como `<chat-runtime-role>`,
accesible por Supavisor TLS, sin permisos directos sobre tablas y con `EXECUTE`
únicamente sobre las RPC que reserven, completen o fallen una petición. El
identificador efectivo se mantendrá en el inventario operativo privado.

El gate de seguridad debe demostrar que ese rol:

- puede ejecutar solo las RPC necesarias;
- no puede seleccionar, insertar, actualizar ni borrar tablas directamente;
- no puede leer otros schemas privados;
- no puede crear objetos ni asumir otros roles.

Si esta opción resulta incompatible con las RPC `SECURITY DEFINER`, debe
documentarse la alternativa y su superficie antes de usar una clave global.

### D3. Presupuesto temporal

**Propuesta inicial:** 90 segundos de backend por petición, con subpresupuestos
que nunca sobrevivan a la cancelación global. El valor final solo se aprobará
después del spike de proxy y del banco pagado.

### D4. Rollback

**Propuesta:** conservar la Function TypeScript congelada durante 14 días tras
alcanzar 100 % de tráfico en Alfredo. Solo sirve como rollback; no recibe nuevas
features. Después se retira junto con las credenciales de proveedor en Netlify.

### D5. Dónde es autoritativo el límite de tráfico

El spike demuestra que el borde no puede contar bien. **Propuesta:** el límite
autoritativo vive en FastAPI, con la misma semántica que hoy aplica la Function,
y el borde conserva solo un descarte barato de abuso evidente, declarado como
best-effort y sin pretensión de exactitud. Ninguna petición rechazada en el borde
puede haber iniciado ya una llamada pagada.

La alternativa —mantener la cuota en el borde con una clave por petición y
recuento por prefijo— está medida y funciona, pero añade 130–420 ms antes del
primer token y sigue sin ser transaccional. No se elige por defecto: el backend
ya tiene una base de datos transaccional para lo mismo.

### D6. Distribución del artefacto

**Propuesta:** reutilizar el patrón ya validado de Deep Research —artefacto
construido aquí, verificado por hash en el host, instalado en un directorio de
release y activado por rename atómico— en lugar de introducir un registro de
imágenes nuevo. Publicar una imagen en un registro público añadiría un canal de
distribución con implicaciones de licencia para los corpus de fuente y una
credencial más que rotar.

Si aun así se elige imagen con digest, el ADR debe decir en qué registro vive,
quién la construye, cómo se verifica su procedencia y por qué el corpus incluido
puede redistribuirse. En cualquiera de las dos formas rige el invariante 13: los
PDF no viajan.

### D7. Comportamiento cuando Alfredo no responde

**Propuesta:** fallo cerrado con error público seguro y sin coste, más vuelta
manual a `CHAT_BACKEND_PERCENT=0`. Un enrutado automático a la Function
congelada es defendible durante la ventana de rollback y **no** viola el
invariante 6, porque es fallback de infraestructura y no de modelo; pero duplica
la superficie viva y exige demostrar que no puede ejecutar las dos estrategias
dos veces para la misma petición. El ADR elige una de las dos y lo justifica.

### D8. Desarrollo local

**Propuesta:** `make dev` sigue levantando FastAPI y Vite, y el frontend apunta a
la API local sin pasar por proxy ni firma; la firma HMAC solo se ejerce en
preview y producción, con su propio test de contrato. Hay que decidirlo
explícitamente: si el camino local no atraviesa la fachada, la fachada solo se
prueba desplegada, y eso debe ser una elección consciente y no un descubrimiento
de la fase 6.

## 7. Fases de ejecución

Cada fase termina en un gate. No se empieza la siguiente si el gate anterior
falla o si el rollback de esa fase no está probado.

### Fase 0 — Congelar baseline y validar plataforma

Objetivo: convertir las suposiciones de infraestructura en evidencia.

- [ ] Integrar o descartar el trabajo en curso sobre los ficheros del chat y
      congelar el baseline sobre un commit de `main` con árbol limpio.
- [ ] Registrar commit, deploy de Netlify, versiones de prompts, modelo, store,
      schema de Supabase y hashes del corpus de producción.
- [ ] Enlazar la incidencia de schema citada en la sección 2 o retirarla.
- [ ] Congelar un banco de regresión que incluya:
  - gimnasio + teléfono;
  - ausencias esporádicas;
  - prueba exigida por Tribunal Supremo;
  - consulta a una sentencia identificada;
  - ausencia de evidencia;
  - fallo de clave y fallo transitorio de cada proveedor.
- [ ] Medir en la V1 al menos p50/p95 de latencia, tasa de error por estrategia,
      coste, tokens y porcentaje de respuestas sustantivas con cita verificada.
- [ ] Ejecutar el spike de stream de 90 segundos a través del proxy candidato
      con `uv run python scripts/chat_stream_spike.py <url-preview> --repeat 3`,
      partiendo de las cifras ya publicadas del spike de 2026-07-29 y midiendo
      solo el tramo aún desconocido. El cliente cuenta latidos, evento terminal
      y duración; no envía preguntas reales.
- [ ] Verificar cancelación del navegador y cierre de conexión aguas arriba.
- [ ] Comprobar si el proveedor del VPS ya trata datos personales por el piloto
      de investigación profunda y no figura entre los encargados publicados. Si
      es así, es un incumplimiento vigente e independiente de esta migración: se
      corrige por su cuenta y no se arrastra al plan.
- [ ] Crear el ADR con D1–D8 y la decisión de continuar o parar.
- [ ] Abrir la matriz documental de la sección 12 y asignar a cada entrega sus
      documentos públicos afectados.
- [ ] Crear un inventario operativo privado, fuera del repositorio, para IP,
      hostname, DNS, rutas, usuarios, unidades reales y localización de secretos.

**Gate F0**

- tres streams sintéticos de 90 segundos completos o proxy alternativo elegido;
- baseline reproducible y sin preguntas/respuestas en logs;
- rollback de routing diseñado antes de desplegar FastAPI.

### Fase 1 — Contrato compartido y caracterización

Objetivo: impedir que el port cambie silenciosamente el producto.

- [ ] Crear fixtures neutrales del protocolo 2 para:
  - respuesta A completa, parcial y error;
  - respuesta B completa, parcial, abstención y error;
  - claims, fuentes, límites, coste actual/estimado/no disponible;
  - cierre global correcto e incorrecto.
- [ ] Ejecutar los mismos fixtures contra serializadores TypeScript y Python.
- [ ] Igualar en Python límites de bytes, mensajes y caracteres.
- [ ] Transportar `conversation_id`, `user_message_id`, `country_path` y
      `request_id` sin reinterpretarlos.
- [ ] Añadir tests de caracterización de las RPC y de su idempotencia.
- [ ] Prohibir que los fixtures contengan textos fiscales reales o secretos.
- [ ] Documentar públicamente el contrato estable y sus límites con valores
      sintéticos; no copiar payloads reales de producción.

**Archivos principales**

- `frontend/netlify/functions/chat/contracts.ts`
- `frontend/netlify/functions/chat/chat.ts`
- `frontend/src/lib/chat-sse-protocol.ts`
- `src/api/chat.py`
- `src/chat_strategy_models.py`
- `schemas/` para fixtures versionados, si procede

**Gate F1**

- paridad byte a byte donde el protocolo lo exige;
- paridad semántica en campos no ordenados;
- cero llamadas de proveedor en toda la fase.

### Fase 2 — Paridad del dominio Python

Objetivo: hacer que FastAPI produzca las mismas respuestas publicables y
aplique los mismos cierres de seguridad.

- [x] Portar la recuperación léxica y el análisis de facetas vigentes,
      incluida la tabla de sinónimos y la expansión de términos al elegir
      anclajes. Sin ambas, la pregunta de gimnasio no alcanzaba
      `san-2347-2022` y el redactor se abstenía por falta de extracto.
- [x] Portar la selección y expansión de anclajes verbatim. La cita se
      amplía con su contexto de la misma página bruta y se comprueba que
      sigue conteniendo el anclaje; sin ello se publicaba la línea suelta.
- [x] Portar `structured-claims-v4` y su gate de relevancia literal.
- [x] Configurar A exclusivamente mediante `GatewayChatWriter(get_gateway())`.
- [x] Configurar A con `gpt-5.6-luna` + `high` y fallback explícito en el gateway.
- [ ] Activar el store con metadata exacta de autoridad y verificar 106/106 PDF.
- [x] Portar `file-search-authority-v8`, con pistas terminológicas y filtro por sentencia.
- [ ] Forzar File Search en B cuando el SDK Python lo permita; si el SDK no
      expone el control, caracterizarlo y documentar la alternativa.
- [ ] Portar el segundo y último intento de B solo ante respuesta sustantiva sin
      cita verificable.
- [ ] Sumar uso y coste de todos los intentos, incluso si el último falla.
- [ ] Igualar diagnósticos públicos y privados sin guardar mensajes de proveedor.
- [x] Añadir el smoke opt-in con doble confirmación de coste:
      `make smoke-chat-schema CONFIRM_PAID=1 CONFIRM_SMOKE=1 CHAT_QUESTION=...`
      ejecuta una sola llamada de A. Su gate offline —que el contrato v4
      sobrevive al modo estricto— está en `tests/test_chat_schema_strict_mode.py`.
- [ ] Actualizar la documentación del gateway y de estrategias en el mismo
      cambio, manteniendo el runtime vigente descrito como Netlify-only hasta
      que se autorice el corte.

**Regresiones obligatorias**

- la pregunta de gimnasio recupera `san-2347-2022`, página 7;
- el móvil queda como límite si no aparece evidencia específica;
- el verbo genérico «apunta» no activa términos de gimnasio;
- una cita no literal se retira;
- el coste del primer intento se conserva si falla el retry;
- un `401` en A deja que el gateway aplique la cadena declarada y no elimina B;
- la ausencia de una credencial tiene el comportamiento decidido en el ADR.

**Gate F2**

- suites Python y frontend verdes;
- banco determinista sin red verde;
- smoke real A/B completo con fuentes verificadas;
- diferencias de calidad revisadas antes de continuar.

### Fase 3 — Persistencia, presupuesto e idempotencia

Objetivo: mover el composition root sin perder garantías económicas ni datos.

- [ ] Implementar un repositorio Python detrás de un `Protocol`; la ruta HTTP no
      hará consultas directas.
- [ ] Reutilizar las RPC vigentes para reservar, completar y fallar peticiones.
- [ ] Mantener la deduplicación por conversación y mensaje.
- [ ] Persistir versiones de experimento, prompts, commit/artefacto y store.
- [ ] Persistir A y B aunque una de las dos falle.
- [ ] Conservar coste `ACTUAL`, `ESTIMATED` o `UNAVAILABLE` sin convertir lo
      desconocido en cero.
- [ ] Garantizar que una cancelación terminal reconcilia la reserva.
- [ ] Verificar que el resumen diario de coste y su comprobación de frescura
      siguen leyendo las mismas filas y produciendo el mismo mensaje con
      peticiones originadas en el nuevo runtime.
- [ ] Crear y probar el rol restringido descrito en D2.
- [ ] Ejecutar advisors de Supabase y tests de privilegios negativos.
- [ ] Actualizar el contrato público de persistencia, retención y privacidad sin
      publicar DSN, nombres de host, roles efectivos ni grants de producción.

**Gate F3**

- mismas filas y campos para un fixture en ambos runtimes;
- doble envío idempotente;
- reserva siempre cerrada en éxito, error, timeout y cancelación;
- rol del runtime incapaz de leer o modificar tablas directamente.

### Fase 4 — Servicio aislado en Alfredo

Objetivo: convertir el prototipo en un servicio operable y recuperable.

- [ ] Construir el artefacto según D6, con inventario declarado y verificación
      de hashes en el host antes de activarlo.
- [ ] Incluir solo código de runtime, corpus derivado y verbatim necesarios;
      excluir `.git`, `.env`, frontend, credenciales, output histórico, los PDF
      de fuente y otros repos.
- [ ] Activar la release por rename atómico, de forma que ningún arranque pueda
      combinar código y corpus de versiones distintas.
- [ ] Ejecutar como usuario sin privilegios, rootfs de solo lectura y `tmpfs`
      acotado.
- [ ] Eliminar capabilities, privilegios adicionales y acceso al socket Docker.
- [ ] Montar corpus/verbatim en solo lectura y verificar hashes al arrancar.
- [ ] Asignar CPU, memoria, PIDs y concurrencia independientes de Deep Research.
- [ ] Configurar restart policy y parada ordenada que cancele proveedores.
- [ ] Exponer únicamente el puerto interno detrás de TLS/Caddy o del ingress ya
      autorizado de Alfredo.
- [ ] Implementar `/health/live` y `/health/ready` sin llamadas pagadas.
- [ ] Configurar Sentry del backend y logs JSON sin contenido fiscal. Es el
      cuarto runtime del proyecto: hay que decidir si reutiliza el proyecto del
      chat o abre uno propio, y declararlo además en `.autofix.yml` y en el
      registro del control plane. Instrumentarlo no lo hace resoluble.
- [ ] Guardar secretos en un env file `0600` del servicio, no en el artefacto
      ni en el checkout.
- [ ] Restringir egress a OpenAI, Gemini, Supabase/Supavisor, Sentry y DNS/NTP
      indispensables.
- [ ] Añadir al runbook público comandos parametrizados con placeholders; los
      nombres, rutas, dominios e inventario reales permanecerán en el registro
      operativo privado.
- [ ] Actualizar `.env.example` solo con nombres y descripciones de variables,
      nunca con valores que se parezcan a credenciales reales.

**Gate F4**

- escaneo del artefacto y de secretos limpio;
- health checks, restart y shutdown verificados;
- saturación controlada devuelve `429/503` sin iniciar llamadas pagadas extra;
- caída del worker Deep Research no afecta al chat y viceversa.

### Fase 5 — Proxy same-origin y autenticación interna

Objetivo: mantener el VPS fuera del contrato público.

- [ ] Promover el prototipo a una fachada soportada sin lógica jurídica.
- [ ] Mantener validación de método, bytes y content type en el borde.
- [ ] Aplicar el límite de tráfico según D5, sin presentar como cuota exacta un
      recuento que la plataforma no puede garantizar.
- [ ] Sustituir el secreto estático simple por firma HMAC de timestamp,
      request-id y hash del body, reutilizando el patrón ya validado con Alfredo.
- [ ] Usar un secreto y una ruta distintos de los del canal de jobs agentivos.
      Compartir el secreto convertiría una filtración del chat en capacidad para
      encolar trabajos, y el chat no necesita esa autoridad.
- [ ] Rechazar firmas antiguas, bodies alterados y request-id inválidos.
- [ ] No seguir redirects del backend.
- [ ] Propagar cancelación, `cache-control`, protocolo y content type.
- [ ] No registrar body ni cabeceras sensibles.
- [ ] Añadir routing estable por conversación para canary 0–100 %.
- [ ] Asegurar que cada petición se ejecuta en un único runtime; no hacer shadow
      de preguntas reales porque duplicaría coste y tratamiento de datos.
- [ ] Documentar el modelo de confianza y el procedimiento de rotación sin
      publicar el secreto, la URL interna ni detalles reutilizables del entorno.

**Gate F5**

- ataques de replay y firma inválida rechazados antes del dominio;
- descarte de abuso y máximo de body verificados en el borde, y cuota
  autoritativa verificada en el backend;
- stream/cancelación E2E verdes;
- `CHAT_BACKEND_PERCENT=0` devuelve todo el tráfico al runtime anterior.

### Fase 6 — Deploy Preview y batería real

Objetivo: validar el recorrido completo sin tocar usuarios de producción.

- [ ] Desplegar FastAPI con `CHAT_COMPARISON_ENABLED=false`.
- [ ] Comprobar health y que `/chat` no llama a proveedores.
- [ ] Activar únicamente el contexto Deploy Preview.
- [ ] Ejecutar contrato HTTP, HMAC, rate limit, timeout y cancelación.
- [ ] Ejecutar el banco congelado con confirmación explícita de coste.
- [ ] Comparar fuentes, límites, estados, tokens, costes y persistencia.
- [ ] Confirmar en Supabase que cada petición crea exactamente los registros
      esperados.
- [ ] Confirmar en Sentry/logs que no aparece contenido fiscal.
- [ ] Probar rollback al runtime TypeScript.
- [ ] Revisar el diff documental y ejecutar detector de secretos antes de
      publicar cualquier informe o evidencia del preview.

**Gate F6**

- 100 % de respuestas sustantivas con al menos una cita verificada;
- 100 % de costes con medición correcta o indisponibilidad explícita;
- cero divergencias de contrato o persistencia;
- p95 y tasa de error no peores que el baseline acordado;
- rollback probado en menos de cinco minutos.

### Fase 7 — Canary de producción

Objetivo: aumentar tráfico sin salto irreversible.

**Prerrequisito bloqueante.** La primera petición de un usuario real que se
ejecute en Alfredo cambia dónde y por quién se tratan sus datos. La página de
privacidad enumera hoy ocho encargados con su ubicación y atribuye a Netlify la
ejecución del endpoint del chat; en cuanto el canary supere el 0 %, esa
enumeración deja de ser cierta. El proveedor de alojamiento del VPS y su
ubicación deben estar publicados **en el mismo cambio** que enruta al primer
usuario, no en la limpieza documental posterior. La regla del proyecto es que la
lista describe lo que ocurre hoy, y una lista incompleta es peor que ninguna.

- [ ] Publicar el encargado y la ubicación nuevos y actualizar el flujo técnico
      descrito en la página de privacidad.
- [ ] Empezar en 0 % y verificar únicamente health/readiness.
- [ ] Pasar a 5 % con routing estable por conversación.
- [ ] Observar al menos 24 horas o el mínimo de solicitudes acordado.
- [ ] Pasar secuencialmente a 25 %, 50 % y 100 % solo si los gates se mantienen.
- [ ] Comparar diariamente latencia, errores, citas, coste y cancelaciones.
- [ ] Mantener las versiones de prompts/modelos constantes durante el canary.
- [ ] Detener y volver a 0 % ante cualquier criterio de rollback.
- [ ] Publicar únicamente métricas agregadas y saneadas; no versionar request
      IDs, trazas, capturas de paneles ni extractos de conversaciones reales.

**Criterios de rollback inmediato**

- filtración de pregunta, respuesta, cita o secreto a logs;
- pérdida o duplicación de persistencia;
- respuesta sustantiva sin cita verificada;
- coste cobrado pero registrado como cero;
- aumento material de `5xx`, timeouts o errores por estrategia;
- saturación que afecte Deep Research, backups u otros servicios de Alfredo;
- imposibilidad de cancelar una petición desconectada;
- el resumen diario de coste o su comprobación de frescura dejan de reflejar el
  tráfico real.

### Fase 8 — Consolidación y retirada de la V1 TypeScript

Objetivo: terminar con una sola implementación del dominio.

- [ ] Mantener 100 % en Alfredo durante 14 días sin criterio de rollback.
- [ ] Retirar recuperación, prompts, adaptadores de proveedor y cálculo de coste
      de la Function TypeScript.
- [ ] Eliminar SDK de OpenAI/Gemini del frontend si ningún otro runtime Node los
      necesita.
- [ ] Añadir un test de arquitectura que impida nuevas llamadas directas de A a
      proveedores fuera del gateway Python.
- [ ] Conservar los fixtures de contrato de la fase 1 como regresión permanente
      del protocolo, aunque desaparezca el serializador TypeScript del dominio:
      el navegador sigue consumiendo el mismo contrato.
- [ ] Retirar `OPENAI_API_KEY` y `GEMINI_API_KEY` de Netlify.
- [ ] Conservar en Netlify únicamente URL/clave del proxy y configuración
      pública necesaria.
- [ ] Eliminar el routing de rollback y la Function congelada.
- [ ] Actualizar arquitectura, runbook, observabilidad, privacidad y backlog.
- [ ] Actualizar README, índice documental, estructura del repositorio y guía de
      desarrollo para que no quede ninguna instrucción Netlify-only vigente.
- [ ] Marcar los planes y experimentos históricos como superados sin reescribir
      sus resultados originales.
- [ ] Ejecutar comprobación de enlaces, detector de secretos y búsqueda de
      referencias obsoletas antes del cierre.
- [ ] Archivar la evidencia de canary y la decisión final.

**Gate F8 / definición de terminado**

- un único composition root de A/B en FastAPI;
- ninguna credencial LLM en Netlify;
- ninguna llamada directa de A fuera de `neutral-llm-gateway`;
- B documentada como excepción File Search con frontera propia;
- operación, alertas, backup de configuración y rollback documentados;
- Netlify continúa sirviendo frontend/proxy, pero no ejecuta dominio LLM.

## 8. Matriz mínima de pruebas

| Nivel | Prueba | Red/coste |
|---|---|---:|
| Unitario | recuperación, prompts, schemas, citas, coste y retry | no |
| Contrato | TypeScript/Python/SSE/RPC con fixtures | no |
| Seguridad | HMAC, replay, límites, roles DB, logs y secretos | no |
| Contenedor | hashes, readonly, recursos, shutdown y health | no |
| Integración | proxy → FastAPI → Supabase con proveedores fake | no |
| Paid smoke | pregunta gimnasio/teléfono A/B | sí, opt-in doble |
| Banco congelado | calidad, cobertura, latencia y coste | sí, autorizado |
| Canary | tráfico real en porcentajes crecientes | sí |

Comandos finales mínimos antes de cada promoción:

```bash
make fast-check
cd frontend && npm run fast-check
gitleaks git --log-opts="--all --remotes"
docker inspect <contenedor-chat>   # usuario, mounts, health y límites esperados
```

El comando de construcción del artefacto depende de D6 y se documentará con
placeholders cuando la decisión esté tomada; no se fija aquí una forma de
empaquetado antes de elegirla.

Los tests pagados requerirán simultáneamente `CONFIRM_PAID=1` y una bandera
específica del smoke. Nunca formarán parte del gate ordinario ni de CI.

## 9. Observabilidad y operación

El servicio debe emitir, sin contenido fiscal:

- `request_id`, versión del artefacto desplegado y experimento;
- estrategia, modelo efectivo, versión de prompt y store;
- latencia por reserva, A, B, persistencia y total;
- tokens y coste por intento y estrategia;
- número de citas candidatas/verificadas;
- tipo de fallo saneado y estado terminal;
- saturación, cola y cancelaciones.

Alertas mínimas:

- health/readiness caído;
- `invalid_api_key` o `invalid_json_schema`;
- coste incompleto o desviación respecto a proveedor;
- respuesta sustantiva retirada por citas;
- reserva sin reconciliar;
- p95, timeouts, `5xx`, memoria o CPU por encima del umbral;
- artefacto desplegado distinto del hash autorizado.

Alfredo se convierte en dependencia productiva del chat. Debe añadirse un
monitor externo del endpoint de health y un smoke sintético sin proveedor. La
disponibilidad del frontend no debe ocultar una caída del backend.

El monitor se crea a mano en la interfaz de UptimeRobot: la API v2 rechaza toda
escritura en el plan contratado, así que no hay forma automatizada de darlo de
alta ni de versionar su configuración. Debe quedar registrado en el inventario
operativo privado como cualquier otro monitor.

## 10. Riesgos principales

| Riesgo | Mitigación |
|---|---|
| El prototipo Python está detrás de la V1 | Golden tests y paridad por fases |
| Dos implementaciones divergen durante el canary | Congelar TypeScript; una sola dirección de cambios |
| Alfredo se vuelve punto único de fallo | health, restart, monitor, límites y rollback 0 % |
| Deep Research agota recursos | contenedor y cuotas totalmente independientes |
| El proxy corta streams largos | spike F0 y alternativa Cloudflare |
| Más superficie de Supabase en el VPS | rol DB restringido y tests negativos |
| Firma interna reutilizable | timestamp + request-id + hash body + ventana corta |
| Retry duplica coste | presupuesto global y suma por intento |
| Desconexión sigue gastando | cancelación propagada y reconciliación terminal |
| Logs capturan PII fiscal | allowlist de campos y tests de observabilidad |
| Checkout o artefacto quedan atrás | activación por hash y readiness que declara la versión |
| La página de privacidad deja de ser cierta al abrir el canary | publicarla en el mismo cambio que enruta al primer usuario |
| El límite de tráfico se cree exacto y tiene fugas | límite autoritativo en el backend (D5) |
| La migración rompe en silencio la vigilancia de coste | verificar timers de coste y frescura en F3 y F6 |
| Un secreto compartido convierte el chat en encolador de jobs | secreto y ruta propios para la fachada |
| El plan se ejecuta con un baseline que ya no existe | congelar sobre commit limpio de `main` en F0 |

## 11. Orden recomendado de entregas

1. ADR y spike de proxy.
2. Fixtures de contrato y caracterización.
3. Paridad del dominio Python.
4. Persistencia y rol restringido de Supabase.
5. Artefacto y servicio aislado en Alfredo.
6. Proxy firmado y routing de canary.
7. Deploy Preview y banco pagado.
8. Actualización de la página de privacidad y del monitor externo.
9. Canary gradual y observación.
10. Retirada del dominio TypeScript y secretos de Netlify.

Cada entrega debe ser reversible y no mezclar cambios de modelo, prompt o corpus
ajenos a la migración. Un fallo de gate detiene el plan; no se compensa
relajando la verificación jurídica o la contabilidad de coste.

## 12. Plan documental para un repositorio público

La creación de este plan no cambia todavía la arquitectura vigente. Hasta que
se autorice el corte, los documentos canónicos deben seguir describiendo la V1
Netlify-only como producción y enlazar esta migración únicamente como propuesta.

La documentación se actualiza junto al código que hace verdadera cada
afirmación, según esta matriz:

| Momento | Documento público | Cambio requerido |
|---|---|---|
| ADR aprobado | `docs/ARCHITECTURE.md` | Añadir la decisión futura y sus gates, sin presentarla como desplegada |
| Contrato | `docs/jurisprudence/CHAT_SYSTEM_ARCHITECTURE.md` | Mantener invariantes A/B, protocolo, evidencia y coste |
| Persistencia | `docs/operations/SUPABASE_CHAT.md` | Explicar el nuevo consumidor y privilegio mínimo |
| Artefacto/VPS | `docs/REPOSITORY_STRUCTURE.md` | Registrar código, artefactos y frontera de despliegue |
| Preview | `docs/operations/CHAT_DEPLOYMENT.md` | Añadir preflight, promoción y rollback parametrizados |
| Observabilidad | `docs/operations/CHAT_OBSERVABILITY.md` | Añadir health, métricas, Sentry y alertas del backend |
| Antes del primer usuario real | `frontend/src/pages/PrivacyPage.tsx` | Publicar el encargado y la ubicación nuevos; bloquea el canary |
| Tratamiento de datos | `docs/operations/PRIVACY_AND_LEGAL.md` | Reflejar ubicación, flujo, acceso y retención sin datos internos |
| Errores | `.autofix.yml`, `docs/operations/AUTOFIX.md` | Declarar el cuarto runtime de Sentry o no será resoluble |
| Vigilancia | `docs/operations/UPTIMEROBOT.md` | Registrar el monitor manual del health del backend |
| Canary | `docs/experiments/` | Publicar metodología y métricas agregadas, nunca conversaciones |
| Corte | `README.md`, `docs/README.md`, `CLAUDE.md`, `frontend/CLAUDE.md` | Cambiar el runtime vigente y los comandos operativos |
| Cierre | `docs/project/TASKS.md` | Cerrar gates, registrar pendientes y enlazar evidencia |
| Retirada | Planes históricos relevantes | Añadir aviso de superación y enlace a la decisión vigente |

### 12.1 Información permitida en Git

- diagramas lógicos y fronteras de confianza;
- nombres de variables sin valores;
- comandos con placeholders como `<chat-image>` o `<backend-origin>`;
- nombres públicos de proveedores y versiones necesarias;
- contratos, schemas y fixtures completamente sintéticos;
- hashes de artefactos públicos que ya estén versionados;
- métricas agregadas que no permitan reconstruir una conversación.

### 12.2 Información que queda fuera de Git

- IP, hostname interno, SSH alias o URL privada real;
- valores de `.env`, secretos HMAC, claves, DSN o tokens;
- rutas exactas del host que revelen el inventario operativo;
- reglas efectivas de firewall, inventario de puertos o allowlists privadas;
- nombres o identificadores de cuentas y proyectos no públicos;
- dumps de Netlify, Supabase, Sentry, Docker o systemd;
- request IDs, payloads, respuestas, citas o trazas de usuarios reales;
- capturas de paneles con datos operativos.

El inventario exacto de despliegue se guarda en el sistema privado de
operaciones autorizado, no en este repositorio. El runbook público describe el
procedimiento reproducible mediante parámetros y cómo verificar el resultado,
pero no los valores concretos de producción.

### 12.3 Gate documental por entrega

Cada PR o commit de la migración debe responder explícitamente:

1. qué afirmación pública cambia;
2. qué documento canónico se actualiza en el mismo cambio;
3. si el estado descrito es propuesto, desplegado en preview o productivo;
4. qué documentación histórica queda superada;
5. cómo se verificó que el diff no contiene secretos ni datos reales.

Antes de promover una fase:

- comprobar enlaces Markdown y rutas citadas;
- ejecutar `gitleaks git --log-opts="--all --remotes"` sobre todas las refs, no
  solo sobre `main`;
- revisar `.env.example`, fixtures, logs y capturas;
- buscar afirmaciones obsoletas como `Netlify-only`, `prototipo FastAPI` o
  límites de 60 segundos y conservarlas solo donde sean historia;
- confirmar que los documentos públicos usan placeholders para valores
  operativos;
- incluir la documentación en la definición de terminado de la fase.

La migración no se considera completa si el código está desplegado pero README,
arquitectura, runbooks, privacidad, observabilidad o backlog siguen describiendo
el runtime anterior.
