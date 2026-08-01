# Persistencia del chat en Supabase

**Estado:** proyecto `residenciafiscal` configurado en `eu-west-1`; migraciones
aplicadas y verificadas, y persistencia conectada a producción el 31 de julio
de 2026.

Supabase es la persistencia privada de la V1 Netlify-only. No participa en la
recuperación jurisprudencial ni sustituye al corpus: se usa para reservar el
presupuesto de forma atómica y guardar los mensajes y costes del comparador A/B.

## Decisión de datos

La revisión de los proyectos de referencia mostró dos patrones útiles:

- `VirtualAssistant` conserva mensaje, tipo, estado, modelo, tokens y `meta`, y
  en sus jobs separa proveedor, modelo, razonamiento, latencia, tokens de caché,
  coste y errores;
- `presupuestor` usa una fila por mensaje con `session_id`, rol, contenido,
  modelo y coste/tokens, y además mantiene un ledger append-only para sumar el
  gasto sin recorrer artefactos heterogéneos.

Residencia Fiscal adapta esos patrones al experimento real: una consulta aceptada
produce tres mensajes persistidos con el mismo `request_id` y `conversation_id`:

1. pregunta del usuario;
2. respuesta `current_structured` (A);
3. respuesta `gemini_file_search` (B).

No se guarda IP, user-agent, cookies, credenciales ni el diagnóstico bruto de los
proveedores. El historial completo del navegador tampoco se reenvía: Supabase
recibe solo la última pregunta autosuficiente y las dos respuestas generadas para
ese turno.

## Modelo

Todas las tablas viven en el schema no expuesto `private`, tienen RLS habilitado
y no conceden permisos a `anon`, `authenticated` ni `service_role`:

| Tabla | Responsabilidad |
|---|---|
| `private.chat_conversations` | Agrupa turnos mediante un UUID aleatorio local y jurisdicción |
| `private.chat_daily_budgets` | Contador diario bloqueado durante cada reserva |
| `private.chat_requests` | Reserva, coste reconciliado, estado e idempotencia del mensaje |
| `private.chat_messages` | Pregunta y respuestas A/B con contenido, fuentes, límites y uso |

Campos de cada respuesta: estrategia, estado, contenido, modelo efectivo,
latencia, coste en microdólares, calidad de la medición (`ACTUAL`, `ESTIMATED`
o `UNAVAILABLE`), versión de precio, tokens de entrada/salida/documento, citas
exactas y límites declarados.

La Function no escribe tablas directamente. Solo puede invocar con
`SUPABASE_SECRET_KEY` estas RPC de `public`, ambas `SECURITY DEFINER`, con
`search_path` fijo y `EXECUTE` revocado a `PUBLIC`, `anon` y `authenticated`:

- `reserve_chat_request`: bloquea la fila diaria, comprueba el techo, reserva y
  guarda la pregunta en una sola transacción;
- `complete_chat_request`: guarda A/B, reconcilia el coste real y completa la
  petición en una sola transacción.
- `fail_chat_request`: marca una reserva como `failed` o `timed_out` con un
  código técnico acotado, sin guardar el diagnóstico del proveedor ni liberar
  la reserva potencialmente consumida.

Las operaciones de ciclo de vida viven en el schema privado y no se exponen por
la Data API:

- `private.purge_expired_chat_data(cutoff)`: elimina peticiones y mensajes
  anteriores al cutoff, y después conversaciones que ya no tienen peticiones.
- `private.delete_chat_conversation(conversation_id)`: suprime una conversación
  completa tras verificar la identidad fuera de la base de datos.

La migración canónica es
`supabase/migrations/20260731161251_chat_persistence_and_budget.sql`. La segunda
migración retira un permiso público inseguro de `rls_auto_enable()` que traía el
proyecto nuevo. Las migraciones de ciclo de vida añaden el índice de la FK de
presupuesto y serializan el borrado. `db lint` no devuelve errores de esquema;
los advisors mantienen avisos informativos esperables para tablas privadas con
RLS sin políticas públicas y, mientras el índice recién creado no acumula uso,
su posible infrautilización.

## Credenciales y fronteras

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

Una comprobación real ejecutada mediante la API guardó una reserva, tres
mensajes y dos respuestas, reconcilió 2.000 microdólares y eliminó después los
registros sintéticos. Una segunda prueba lanzó doce reservas simultáneas contra
un techo de cinco: pasaron exactamente cinco y las otras siete fueron rechazadas;
el contador terminó en el techo. Sus datos sintéticos también se eliminaron. No
imprimir claves ni cuerpos reales al validar producción.

El smoke productivo del 31 de julio devolvió protocolo 2 y HTTP 200 en 20,23 s;
por contrato, el handler solo responde 200 después de completar las dos RPC. A
usó Luna `high` en 18,16 s y costó 2.849 microdólares `ACTUAL`; B usó Gemini
File Search en 6,41 s y costó 1.693 microdólares `ESTIMATED`. Total observado:
4.542 microdólares (0,004542 USD). Las dos estrategias se ejecutaron en
paralelo.

## Retención y supresión

Persistir contenido cambia el contrato anterior, que solo guardaba métricas.
La página `/privacidad` declara pregunta, respuestas, citas y costes. El plazo
real se configura mediante `CHAT_RETENTION_DAYS`; el timer falla cerrado si falta
esa variable. No se publica ni se promete un plazo hasta aprobarlo jurídicamente.

Instalación del purgado diario en el VPS:

```bash
sudo bash scripts/privacy/install-chat-retention-timer.sh
sudo systemctl start residenciafiscal-chat-retention.service
```

El procedimiento de supresión requiere verificación de identidad fuera de la
base de datos y un ticket operativo. El UUID visible de la URL no es una prueba
suficiente:

```bash
bash scripts/privacy/delete-chat-conversation.sh \
  --conversation-id conversation-... \
  --ticket PRIV-123 \
  --confirm-delete
```

La función elimina la copia primaria de Supabase. Las copias R2 no se reescriben
individualmente; el backup que contenga el registro desaparece al aplicar
`BACKUP_RETENTION_DAYS` (o `CHAT_RETENTION_DAYS` si no hay override). La respuesta
al solicitante debe informar de ese límite y no afirmar borrado inmediato de los
backups.

Siguen pendientes fuera del código: identidad legal del responsable, base
jurídica, transferencias y contratos verificados con Supabase, OpenAI y Google.
