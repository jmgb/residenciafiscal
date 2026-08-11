# Persistencia del chat en Supabase

**Estado:** proyecto `residenciafiscal` configurado en `eu-west-1`; persistencia
conectada a producción el 31 de julio de 2026. Local y remoto coinciden hasta
`20260806015000_chat_history_possession.sql`: el historial, los turnos
editoriales y el hardening forward-only de posesión constan aplicados, y los
advisors de seguridad y rendimiento no devuelven incidencias.

Supabase es la persistencia privada de la V1 Netlify-only y del runtime FastAPI
cuando la migración supere sus gates. No participa en la
recuperación jurisprudencial ni sustituye al corpus: se usa para registrar las
consultas y guardar los mensajes y costes del comparador A/B y los resultados
asíncronos de investigación profunda C.

## Decisión de datos

La revisión de los proyectos de referencia mostró dos patrones útiles:

- `VirtualAssistant` conserva mensaje, tipo, estado, modelo, tokens y `meta`, y
  en sus jobs separa proveedor, modelo, razonamiento, latencia, tokens de caché,
  coste y errores;
- `presupuestor` usa una fila por mensaje con `session_id`, rol, contenido,
  modelo y coste/tokens, y además mantiene un ledger append-only para sumar el
  gasto sin recorrer artefactos heterogéneos.

Residencia Fiscal adapta esos patrones al experimento real. Una consulta A/B
aceptada produce con el mismo `request_id` y `conversation_id`:

1. pregunta del usuario;
2. una o dos respuestas activas: `current_structured` (A) y
   `gemini_file_search` (B).

Un turno resuelto desde el catálogo produce la pregunta y una respuesta
`editorial`; no se hace pasar por A ni por B.

Si el usuario lanza investigación profunda, su resultado añade de forma
asíncrona un mensaje adicional de asistente `deep_research` (C). Este mensaje queda
enlazado al job mediante `deep_research_job_id`; el vínculo con la comparación
A/B vive en el propio job, por lo que C no altera el ledger ni las métricas A/B.

No se guarda IP, user-agent, cookies, credenciales ni el diagnóstico bruto de los
proveedores. El historial completo del navegador tampoco se reenvía: Supabase
recibe una pregunta por turno y sus respuestas A/B o editorial, más C si se
solicita. En el turno siguiente la Function relee una proyección acotada de esas
mismas filas; no crea otra copia del historial.

## Modelo

Todas las tablas viven en el schema no expuesto `private`, tienen RLS habilitado
y no conceden permisos a `anon`, `authenticated` ni `service_role`:

| Tabla | Responsabilidad |
|---|---|
| `private.chat_conversations` | Agrupa turnos por UUID y guarda la jurisdicción y el SHA-256 del secreto de posesión |
| `private.chat_requests` | Registro idempotente de consulta, coste, estado y versión del experimento |
| `private.chat_messages` | Pregunta y respuestas A/B/C/editorial con contenido, fuentes, claims, diagnóstico acotado, límites y uso |
| `private.chat_comparison_votes` | Un voto ciego cerrado por petición completada |
| `private.chat_retention_purge_audit` | Auditoría de dry-run, límites y purgados, sin contenido |

Campos de cada respuesta: estrategia, estado, contenido, modelo efectivo,
`reasoning_effort` enviado al proveedor cuando se configuró explícitamente,
latencia, coste en microdólares, calidad de la medición (`ACTUAL`, `ESTIMATED`
o `UNAVAILABLE`), versión de precio, tokens de entrada/salida/documento, citas
exactas y límites declarados. El esfuerzo queda a `NULL` cuando no hubo llamada
al modelo o la estrategia no configuró un valor equivalente.

La columna `experiment` de `private.chat_requests` identifica
`experiment_version`, commit o deploy,
schema comparativo, versión del corpus estructurado, store de File Search y
versiones de ambos prompts. La columna `diagnostics` de
`private.chat_messages` conserva únicamente enums, contadores, filtro e IDs
públicos de sentencias; no guarda mensajes de error ni payloads de proveedor.
En A, `claims` enlaza cada afirmación con los índices de sus citas exactas.

Una respuesta puede no traer diagnóstico: la abstención determinista del router
no llama al modelo. En ese caso la clave se **omite** del payload de la RPC. Un
`diagnostics: null` explícito no vale: llega como jsonb `'null'`, que no es un
`NULL` de SQL, y `chat_messages_diagnostics_object_check` rechaza la fila
entera. Costó un 503 con la respuesta ya generada y la consulta atascada en
`processing`.

La Function no escribe tablas directamente. Solo puede invocar estas RPC de
`public`, todas `SECURITY DEFINER`, con
`search_path` fijo y `EXECUTE` revocado a `PUBLIC`, `anon` y `authenticated`:

- `authorize_chat_conversation`: crea un hilo protegido o comprueba que coinciden
  su jurisdicción y el SHA-256 del secreto antes de registrar otro turno;
- `create_chat_request`: registra de forma idempotente la consulta y la pregunta
  en una sola transacción;
- `complete_chat_request`: guarda A/B, el coste real y completa la petición en
  una sola transacción;
- `update_deep_research_job`: actualiza el estado de C y, cuando completa,
  persiste idempotentemente su salida como mensaje de asistente en la misma
  transacción;
- `fail_chat_request`: marca una consulta como `failed` o `timed_out` con un
  código técnico acotado, sin guardar el diagnóstico del proveedor;
- `record_chat_vote`: acepta una sola preferencia por petición completada, con
  veredicto `a`, `b`, `tie` o `both_bad` y un motivo de una allowlist cerrada;
- `read_chat_history`: devuelve los últimos turnos completados de una
  conversación como contexto del turno actual.

El historial se lee del ledger, nunca del cuerpo de la petición: el navegador
manda solo la pregunta actual y el servidor no puede dar por buenas unas
respuestas anteriores que el cliente podría haber alterado. `read_chat_history`
devuelve exclusivamente pregunta y texto de respuesta —ni coste, ni diagnóstico,
ni citas—, solo de peticiones `completed`, y deja fuera `deep_research`, que es
otro flujo. No amplía la superficie almacenada ni la retención: son las mismas
filas de siempre, purgadas a los 15 días.

El UUID aparece en la ruta local `/c/...` y **no autoriza** la lectura. Al crear
una conversación, el navegador genera además un secreto aleatorio de 256 bits y
lo conserva en `localStorage`; la Function calcula su SHA-256 y solo esa huella
llega a Supabase. `authorize_chat_conversation` fija la huella al crear el hilo y
rechaza después cualquier valor distinto; `read_chat_history` exige la misma
coincidencia. El secreto en claro no se persiste ni se registra en observabilidad.

Las conversaciones locales anteriores a este contrato no pueden reclamar una
fila antigua sin protección: al migrar el estado del navegador conservan su
historial visual y su URL local, pero reciben un `ledgerId` nuevo y un secreto
nuevo. El siguiente turno empieza por tanto un hilo de servidor nuevo, sin exponer
ni apropiarse del historial antiguo. Como los `comparisonId` y jobs remotos
anteriores siguen ligados al UUID abandonado, la migración retira esas referencias:
conserva los resultados de investigación ya terminados, pero convierte un job aún
activo en error recuperable para que el usuario lo inicie de nuevo.

Durante el despliegue, una pestaña que siga ejecutando el bundle anterior no manda
todavía `conversation_access_token`. La Function admite esa ausencia solo como
compatibilidad transitoria: ignora el `conversation_id` aportado, genera un UUID y
un secreto efímeros para esa petición y responde sin contexto previo. Un secreto
presente pero mal formado sigue siendo un `400`. Así el rollout no rompe pestañas
abiertas ni permite que un cliente antiguo reclame o lea un UUID visible.

La lectura es opcional y tiene un presupuesto de un segundo: un fallo o bloqueo
de Supabase degrada a hilo vacío antes de consumir el deadline de los
proveedores. El prompt admite como máximo seis turnos y 12 KiB en total; cada
pregunta se recorta a 500 caracteres y cada respuesta a 1.500. El contexto se
marca como conversación previa, nunca como evidencia, y su tamaño se descuenta
del presupuesto de evidencia estructurada de A.

Una referencia explícita como «ese caso» o «lo anterior» incorpora a la consulta
de recuperación la pregunta previa más cercana aunque el turno actual ya incluya
vocabulario del dominio. El resto de preguntas autosuficientes mantiene la
recuperación original; si el router no puede resolverlas, se reintenta con las
preguntas recientes. El adjetivo temporal aislado no activa esta vía: «el año
anterior» sigue siendo una pregunta autosuficiente, no una referencia al diálogo.

Cada estrategia recibe **su propio hilo**: A ve sus respuestas anteriores y B las
suyas. Compartirlo destruiría la independencia de la comparación A/B. Los turnos
en los que una estrategia no respondió se conservan con su pregunta, porque lo
que el usuario preguntó sigue siendo contexto suyo.

### Turnos editoriales

Las respuestas editoriales son texto revisado del repositorio que el chat muestra
sin llamar a ningún modelo, y hasta ahora se resolvían solo en el navegador: el
servidor no sabía que la conversación existía. `POST /api/chat-editorial` las
registra como un turno completo, así que un seguimiento sobre ellas ya llega con
antecedente.

El cuerpo solo dice **qué** respuesta se mostró: el texto sale del catálogo del
propio servidor (`src/data/editorialChatAnswers.json`), nunca del cliente. El
`request_id` se deriva del identificador del mensaje, de modo que un reintento no
duplica el turno.

En modo live el navegador muestra la respuesta al terminar la espera editorial,
pero mantiene el composer bloqueado hasta que acaba el registro, evitando que un
seguimiento inmediato adelante a la RPC. Si el usuario cancela durante esa
persistencia, la respuesta ya visible se conserva: una cancelación de `fetch` no
puede demostrar que el servidor no haya confirmado el turno. La espera se corta
a los tres segundos; si el ledger no responde, el composer se libera y el
siguiente turno degrada sin ese antecedente.

Se guardan con `strategy = 'editorial'`, coste cero y medición `ACTUAL` —no hubo
llamada, así que el cero es exacto—. **Nunca reutilizan la estrategia de A o de
B**: el ledger no puede atribuir a un modelo un texto que no escribió, y las
métricas del experimento deben excluirlas filtrando por `strategy`. En el
historial las ven las dos estrategias, marcadas como ajenas para que ninguna las
tome por doctrina propia.

Efecto conocido en el resumen diario: un turno editorial es una petición
`completed` más, así que `requests` y `by_status` lo cuentan aunque no haya
habido llamada a ningún modelo. `by_strategy` lo desglosa como `editorial`, con
coste cero; es ahí donde hay que mirar antes de leer el total como volumen de
consultas al modelo.

El voto no admite texto libre y el endpoint `/api/chat-vote` no expone acceso
directo a Supabase. Un segundo voto para el mismo `request_id` responde como
duplicado y no sobrescribe el primero.

Las operaciones de ciclo de vida viven en el schema privado y no se exponen por
la Data API:

- `private.purge_expired_chat_data(cutoff)`: elimina peticiones y mensajes
  anteriores al cutoff, y después conversaciones que ya no tienen peticiones.
- `private.delete_chat_conversation(conversation_id)`: suprime una conversación
  completa tras verificar la identidad fuera de la base de datos.

La migración inicial histórica es
`supabase/migrations/20260731161251_chat_persistence_and_budget.sql`;
`20260801104446_restore_chat_observability_only.sql` elimina la tabla y columnas
de presupuesto monetario y deja solo el coste real observado, y la migración
`20260801111630_chat_messages_reasoning_effort.sql` añade el esfuerzo de
razonamiento por respuesta;
`20260802215501_chat_experiment_ledger.sql` versiona el experimento y conserva
claims/diagnóstico; `20260802221008_chat_comparison_votes.sql` añade el voto
ciego; `20260805184500_chat_conversation_history.sql` añade la primera lectura
del historial conversacional; `20260805190000_chat_editorial_messages.sql`
admite la estrategia `editorial`; y la migración forward-only
`20260806015000_chat_history_possession.sql` añade el hash de posesión, sustituye
la firma de lectura insegura y conserva inmutables las migraciones ya aplicadas.
La segunda migración histórica retira un permiso público inseguro de
`rls_auto_enable()` que traía el proyecto nuevo. Las migraciones de ciclo de vida
serializan el borrado. Tras aplicar las dos migraciones del experimento, los
advisors de seguridad no devolvieron incidencias.

## Credenciales y fronteras

El runtime FastAPI no debe copiar `SUPABASE_SECRET_KEY`. Usa
`SUPABASE_CHAT_RUNTIME_KEY`, un rol de operación representado públicamente por
`<chat-runtime-role>`, con `EXECUTE` únicamente sobre las tres RPC de ciclo de
vida (`create_chat_request`, `complete_chat_request` y `fail_chat_request`). El
rol no puede leer, insertar, actualizar ni borrar tablas directamente ni crear
objetos. Los grants efectivos y el DSN se verifican en el entorno privado, no se
publican aquí.

La Function necesita `SUPABASE_URL` y `SUPABASE_SECRET_KEY`. La segunda es un
secreto de backend que omite siempre el prefijo `VITE_`; nunca se importa desde
`frontend/src/` ni se envía al navegador.

`SUPABASE_ACCESS_TOKEN`, `SUPABASE_DB_PASSWORD` y `SUPABASE_REF` sirven solo
para administrar migraciones desde una máquina autorizada. No son variables del
runtime de Netlify.

La clave publicable no es necesaria en esta V1: el navegador no consulta
Supabase y no existe acceso de usuario a las tablas.

La cuenta Netlify está en un plan Legacy que no permite scopes específicos. Por
decisión explícita de producto, `SUPABASE_SECRET_KEY` y las claves de proveedor
se guardan como variables ordinarias limitadas al contexto `production`, pero
disponibles a todos los scopes. No llevan prefijo `VITE_` y Vite no las incluye
en el cliente. La contrapartida aceptada es que administradores y procesos de
build autorizados en Netlify pueden leerlas. Si la cuenta pasa a Pro, deben
convertirse a secretos de scope Functions y rotarse.

## Operación

```bash
# Requiere los accesos locales en .env
supabase migration list --linked
supabase db advisors --linked --type security
supabase db advisors --linked --type performance
```

Una comprobación real ejecutada mediante la API guardó una consulta, tres
mensajes y dos respuestas, registró 2.000 microdólares de coste observado y
eliminó después los registros sintéticos. La idempotencia de la consulta se
prueba reutilizando el mismo par `conversation_id`/`user_message_id`; no se
crean filas duplicadas ni se reserva dinero. No imprimir claves ni cuerpos
reales al validar producción.

El smoke productivo del 31 de julio devolvió protocolo 2 y HTTP 200 en 20,23 s;
por contrato, el handler solo responde 200 después de completar las dos RPC. A
usó Luna `high` en 18,16 s y costó 2.849 microdólares `ACTUAL`; B usó Gemini
File Search en 6,41 s y costó 1.693 microdólares `ESTIMATED`. Total observado:
4.542 microdólares (0,004542 USD). Las dos estrategias se ejecutaron en
paralelo.

### Una migración aplicada no se edita

Se corrige **hacia delante**, con una migración nueva. Editar en sitio el fichero
de una migración que producción ya aplicó deja la base de datos con la redacción
anterior y el repositorio declarando otra, y nada avisa.

`supabase migration list --linked` **no lo detecta**: compara versiones, no
contenido. El 11 de agosto de 2026 daba las dieciocho migraciones en verde
mientras cinco objetos de producción seguían siendo los de la redacción original
de `20260803120000` y `20260803123000`, editadas en sitio ocho días antes. La
deriva salió por la puerta de al lado: `purge-chat-data.sh` llamaba a
`private.purge_expired_deep_research_jobs` con tres argumentos y en producción
esa función solo tenía uno, así que el timer de retención habría fallado en su
siguiente ejecución. Con ella viajaban una supresión por derechos que no borraba
los jobs C y dos validaciones ausentes.

Lo que sí lo detecta es preguntar a la base de datos por la definición viva —el
cuerpo de la función en `pg_proc`, la restricción con `pg_get_constraintdef`, las
columnas en `information_schema`— y compararla con lo que declara el repositorio.
De las firmas de las RPC del contrato se encarga ya `check-database-contract.sh`
cada noche, contra `scripts/backup/database-contract.txt`; lo demás sigue siendo
manual, así que merece la pena mirarlo cuando una migración se editó después de
aplicarse, aunque el listado salga limpio.

La reparación es también una migración hacia delante:
`20260811073000_deep_research_review_gaps_forward.sql` sirve de plantilla
—idempotente, sin tocar datos y con el motivo escrito en la cabecera—. Si además
limpia filas para imponer una restricción, la restricción entra `NOT VALID`
primero y se valida al final, como en
`20260811100000_deep_research_jobs_conversation_fk.sql`: al revés, cualquier
escritura concurrente durante la limpieza tumba la migración entera.

## Retención y supresión

Persistir contenido cambia el contrato anterior, que solo guardaba métricas.
La página `/privacidad` declara pregunta, respuestas, citas y costes. El plazo
real se configura mediante `CHAT_RETENTION_DAYS`; el timer falla cerrado si falta
esa variable. La operación actual del VPS usa 15 días, con el borrado activado
tras la autorización operativa explícita del proyecto; esto no sustituye la
aprobación jurídica formal ni cambia lo que debe declarar `/privacidad`.

El job sigue el patrón operativo de Presupuestor:

- `CHAT_RETENTION_PURGE_ENABLED=false` por defecto: el timer no hace nada hasta
  activar explícitamente la política aprobada.
- `CHAT_RETENTION_DRY_RUN=true` por defecto: primero cuenta candidatos y registra
  la ejecución, sin borrar.
- `CHAT_RETENTION_BATCH_LIMIT=500` por defecto: si cualquiera de las tres
  familias supera el límite, la ejecución se rechaza completa y queda auditada
  como `batch_overflow`.

Cada ejecución escribe solo contadores, cutoff, modo y estado en
`private.chat_retention_purge_audit`; nunca guarda ni imprime preguntas,
respuestas o diagnósticos de proveedores. La tabla es backend-only y se incluye
en el dump del schema `private`.

Instalación del purgado diario en el VPS:

```bash
sudo bash scripts/privacy/install-chat-retention-timer.sh
sudo systemctl start residenciafiscal-chat-retention.service
```

La instalación del timer no activa el borrado. La secuencia segura es: instalar,
observar dry-run durante el periodo acordado, revisar la auditoría con compliance
y solo entonces configurar `CHAT_RETENTION_PURGE_ENABLED=true` y, cuando proceda,
`CHAT_RETENTION_DRY_RUN=false`.

Estado operativo a 2026-08-01: `CHAT_RETENTION_DAYS=15`, job habilitado,
`CHAT_RETENTION_DRY_RUN=false` y primera ejecución real completada con cero
candidatos y cero borrados. El timer diario queda activo en el VPS `alfredo`.

El procedimiento de supresión requiere verificación de identidad fuera de la
base de datos y un ticket operativo. Se usa la referencia técnica que
`/privacidad` muestra desde el estado local —el `ledgerId` en un historial
migrado—, no se pide el secreto y el UUID visible por sí solo no prueba identidad:

```bash
bash scripts/privacy/delete-chat-conversation.sh \
  --conversation-id referencia-tecnica-del-ledger \
  --ticket PRIV-123 \
  --confirm-delete
```

La función elimina la copia primaria de Supabase. Las copias R2 no se reescriben
individualmente; el backup que contenga el registro desaparece al aplicar
`BACKUP_RETENTION_DAYS` (o `CHAT_RETENTION_DAYS` si no hay override). La respuesta
al solicitante debe informar de ese límite y no afirmar borrado inmediato de los
backups.

`/privacidad` ya publica el responsable (Intangible Land LLC), la base jurídica
por finalidad, la tabla de encargados con su ubicación, las transferencias fuera
del EEE, el plazo de 15 días y el límite de las copias. Siguen pendientes fuera
del código: los contratos de encargo verificados con Supabase, OpenAI y Google,
la validación jurídica formal del texto, el consentimiento previo de la analítica
y la decisión sobre el representante del art. 27 RGPD.
