# ADR-20260804: migración reversible del chat A/B a Alfredo

**Estado:** aceptado para implementación local y Deploy Preview; no autoriza
tráfico de usuarios ni cambios de privacidad productivos.

**Alcance:** mover el composition root de `POST /api/chat` a un servicio FastAPI
aislado, manteniendo el endpoint público, el protocolo SSE 2 y las RPC vigentes.

## Decisión

1. **Proxy (D1).** La primera candidata es la Edge Function firmada
   `frontend/netlify/prototypes/chat-fastapi-edge-v2.ts`. El gate pendiente son
   tres streams sintéticos de 90 segundos en Deploy Preview. Si falla, se
   evaluará Cloudflare Worker/Tunnel sin cambiar el contrato del navegador.
2. **Supabase (D2).** El runtime usará `SUPABASE_CHAT_RUNTIME_KEY`, que representa
   un rol operativo restringido y solo ejecutará las RPC públicas de ciclo de
   vida. El nombre efectivo, grants y DSN pertenecen al inventario privado; no
   se copia la clave global `SUPABASE_SECRET_KEY` al artefacto.
3. **Tiempo (D3).** El presupuesto inicial del backend es 90 segundos. No se
   reduce para adaptarlo a límites de Netlify; el valor definitivo requiere el
   spike de proxy y el banco pagado con doble confirmación.
4. **Rollback (D4/D7).** Alfredo falla cerrado con error público seguro. El
   rollback se hace manualmente fijando `CHAT_BACKEND_PERCENT=0`; la Function
   TypeScript permanece congelada durante 14 días después de un eventual 100 %.
   No se activa fallback automático que pueda duplicar una petición pagada.
5. **Cuota (D5).** La cuota autoritativa vive en FastAPI, con la clave que firma
   la fachada (`x-chat-client-key`, hash de la IP de conexión). El backend no
   lee `X-Forwarded-For`, que el cliente puede fijar. En el borde el descarte de
   abuso lo aplica la cuota nativa de Netlify con la misma ventana que la V1; no
   se implementa un contador propio sobre Blobs, cuyo compare-and-swap pierde
   incrementos. `CHAT_RATE_LIMIT_ENABLED` sigue en `false` por defecto para no
   limitar el camino local, y es obligatoria al abrir tráfico.
6. **Artefacto (D6).** Se construye un tar.gz reproducible con allowlist,
   manifiesto y hashes, se verifica en el host y se activa mediante release
   versionada más rename atómico. No incluye PDF de CENDOJ, `.env`, frontend,
   credenciales ni checkout Git.
7. **Desarrollo local (D8).** `make dev` sirve FastAPI y Vite directamente; la
   firma HMAC se exige en preview/producción, no en el camino local. La fachada
   se prueba con contrato y Deploy Preview separados.

## Consecuencias

- El backend tiene un único composition root para A/B: A pasa por
  `GatewayChatWriter(get_gateway())`; B conserva File Search y su gate literal.
- La persistencia Python depende de un `Protocol` y llama a
  `create_chat_request`, `complete_chat_request` y `fail_chat_request`; no hay
  consultas directas al schema `private`.
- El coste desconocido se representa como `UNAVAILABLE`, nunca como cero.
- La primera petición real queda bloqueada hasta actualizar privacidad,
  encargados y ubicación del proveedor del VPS en el mismo cambio del canary.

## Gates que siguen abiertos

- baseline limpio de `main`, incidencia de schema y métricas V1 reproducibles;
- streams de 90 segundos y cancelación upstream;
- privilegios negativos del rol de Supabase;
- banco paid smoke, contrato completo de persistencia y rollback probado;
- privacidad, monitor externo y operación real del host.
