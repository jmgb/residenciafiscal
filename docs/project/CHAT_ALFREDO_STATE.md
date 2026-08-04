# Migración del chat a Alfredo — estado congelado y ruta de reanudación

**Estado:** pausada por prioridad, no por fallo. Todo lo implementado está
verificado; lo que falta está bloqueado por decisiones o por infraestructura,
no por código pendiente.
**Fecha de corte:** 2026-08-04.
**Qué autoriza este documento:** nada. Es el mapa para retomar el trabajo si
vuelve a ser prioritario, y el inventario de lo que quedó corriendo.

Los otros tres documentos siguen vigentes y no se repiten aquí:

| Documento | Qué contiene |
|---|---|
| [`CHAT_ALFREDO_MIGRATION_PLAN.md`](CHAT_ALFREDO_MIGRATION_PLAN.md) | Fases, gates, invariantes y matriz documental |
| [`ADR-20260804-chat-alfredo.md`](../decisions/ADR-20260804-chat-alfredo.md) | Decisiones D1–D8 y sus consecuencias |
| [`CHAT_ALFREDO_DELIVERY_MATRIX.md`](CHAT_ALFREDO_DELIVERY_MATRIX.md) | Qué está implementado y la evidencia de los smokes |

## 1. Quién sirve el chat hoy

**Producción sigue en la Netlify Function TypeScript.** El VPS no atiende
tráfico. Confundir ambas cosas es el error más fácil al retomar esto:

| Pieza | Dónde | Estado |
|---|---|---|
| Frontend y páginas prerenderizadas | Netlify | Producción |
| `POST /api/chat` que responde a usuarios | Netlify Function | Producción |
| Endpoints de voto e investigación profunda | Netlify Functions | Producción, fuera del alcance de la migración |
| Runtime FastAPI del chat | Host de operaciones | **Instalado y cerrado**: sin credenciales, sin persistencia, solo loopback |
| Fachada firmada Edge → FastAPI | `frontend/netlify/prototypes/` | Prototipo, no desplegada |

## 2. Lo que quedó corriendo en el host

Hay un contenedor **activo pero cerrado** en la máquina de operaciones. No
responde a nadie ni gasta dinero, pero existe y ocupa recursos, así que quien
retome esto —o quien decida abandonarlo— tiene que saberlo.

- se instala y actualiza con `scripts/deploy_chat_runtime.sh`;
- arranca con `CHAT_COMPARISON_ENABLED=false`, sin claves de proveedor y sin
  `SUPABASE_CHAT_RUNTIME_KEY`, escuchando solo en loopback;
- `POST /chat` devuelve `503` sin llamar a ningún proveedor;
- `/health/ready` verifica los hashes de la release incluso con el chat cerrado
  y declara qué versión está activa;
- **Sentry está inactivo ahí**: el env file no tiene DSN, así que el runtime
  falla cerrado y no reporta. Está declarado en `.autofix.yml` como cuarto
  proyecto, pero hoy no llega ningún evento.

Para retirarlo por completo basta con eliminar el contenedor, su imagen y el
directorio de releases del host; nada más depende de él.

## 3. Qué se verificó con llamadas reales

Cinco llamadas de pago el 4 de agosto de 2026, con preguntas sintéticas y de
banco. Detalle y cifras en la matriz de entregas. Lo esencial:

- `structured-claims-v4` sobrevive al modo estricto real, que era el riesgo
  principal del port;
- cada afirmación cita solo sus fuentes y el gate de relevancia retira las que
  no tienen respaldo literal;
- el gate de autoridad judicial funciona en A y en B;
- los filtros de File Search por autoridad y por sentencia devuelven resultados;
- el coste sale `ACTUAL` con importe y tokens, y baja a `ESTIMATED` cuando el
  proveedor no desglosa.

El smoke destapó cuatro divergencias del port que ninguna revisión estática
había detectado. Están cerradas, pero el método que las encontró fue comparar
constantes a mano y hacer una llamada real, no un banco sistemático. **Eso sigue
siendo el punto débil de la paridad.**

## 4. Qué bloquea cada cosa

| Pendiente | Bloqueado por | Quién decide |
|---|---|---|
| Gate F0: 90 s de stream | Requiere un Deploy Preview; el cliente de medida es `scripts/chat_stream_spike.py` | Operación |
| Persistencia contra Supabase real | El rol restringido de Postgres (D2) no existe | Producto y datos |
| Rol restringido de Postgres | Hay que crearlo, dar `EXECUTE` solo sobre las tres RPC y probar privilegios negativos | Producto y datos |
| Abrir el contenedor a tráfico | Los dos anteriores | Producto |
| Monitor externo del health | UptimeRobot rechaza escrituras por API en el plan contratado; alta manual | Operación |
| Sentry del cuarto runtime | Falta DSN en el env file del host y el registro en el control plane | Operación |
| Retry de B en real | Exige forzar una respuesta sustantiva sin ninguna cita verificable | Calidad |
| Banco de regresión congelado | No existe como artefacto ejecutable; es la fase 0 del plan | Calidad |
| Página de privacidad | Deliberado: es prerrequisito del canary y el canary está a 0 % | Legal |

## 5. Decisión de arquitectura que sigue abierta

Si el gate F0 falla, la salida **no es que el navegador llame directamente al
VPS**. La fachada compra cuatro cosas que se pierden con la llamada directa:

1. no publicar el host de operaciones, que además sirve otros productos, en la
   CSP y en el bundle;
2. mantener la cuota de plataforma y el WAF por delante, en vez de exponer la
   máquina a cualquier escáner;
3. rollback en una variable, sin redesplegar un bundle que las pestañas abiertas
   conservan durante días;
4. same-origin: sin CORS, sin preflight y sin tocar la enumeración de
   destinatarios de la página de privacidad.

Lo que la fachada **no** compra: la firma HMAC autentica el salto, no al
usuario. El endpoint es anónimo con fachada y sin ella; lo que impide es que
quien descubra el backend se salte el borde.

**Recomendación si F0 falla:** mover la fachada a un Worker o un Tunnel de
Cloudflare sobre un subdominio propio, no eliminarla. Conserva las cuatro
ventajas y desaparece el límite de stream. Llamar directo solo tendría sentido
con usuarios autenticados y coste atado a una cuenta.

## 6. Política de modelo de A

La deuda documental del commit `f2e7633` está cerrada. La configuración vigente
del runtime Python es:

- primario: `gpt-5.6-luna`;
- esfuerzo: `high`;
- fallback explícito: `gpt-5.6-terra`;
- ejecución y atribución de todos los intentos: `neutral-llm-gateway`.

`CHAT_MODEL` y `CHAT_FALLBACK_MODELS` permiten cambiar la política sin tocar el
adaptador, y `GET /config` la publica. El fallback nunca cruza entre A y B ni
se elige silenciosamente: solo usa los modelos declarados en la cadena.

## 7. Orden de reanudación

Cada paso deja evidencia y ninguno depende del siguiente para ser útil.

1. Cerrar la deuda documental del fallback de modelo, o revertirlo.
2. Congelar el baseline sobre un commit limpio de `main` y materializar el banco
   de regresión de la fase 0. Sin él, la paridad seguirá dependiendo de
   inspecciones manuales.
3. Medir el gate F0 con `scripts/chat_stream_spike.py` contra un Deploy Preview.
   Si falla, aplicar la recomendación de la sección 5.
4. Crear el rol restringido de Postgres y sus tests de privilegios negativos.
5. Abrir el contenedor del host contra ese rol y comparar filas con el runtime
   vigente para el mismo fixture.
6. Dar de alta el monitor externo y el DSN de Sentry del cuarto runtime.
7. Actualizar la página de privacidad **en el mismo cambio** que enrute al
   primer usuario real, y solo entonces empezar el canary.

Si la migración se abandona en lugar de retomarse, el paso único es retirar el
contenedor y su directorio de releases del host, y borrar este documento junto
con el plan y el ADR, dejando constancia de la decisión.
