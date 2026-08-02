# API / MCP para agentes externos con créditos prepagados

**Fecha del diseño:** 2026-08-02 · **Estado:** diseño aceptado como dirección
futura; **sin implementar**. La tarea que lo activa vive en
[`docs/project/TASKS.md`](../project/TASKS.md) (sección «Producto y
arquitectura»).

## 1. Idea

Ofrecer el servicio de consulta jurídica del SaaS a **agentes de IA externos**
(asistentes de despachos, agentes de compliance, herramientas tipo Claude/GPT
con MCP) para que consulten la base jurisprudencial y normativa y las
conclusiones que produce el sistema, sin pasar por la web.

El agente externo:

1. **Crea una cuenta** y obtiene un **token de API** que lo autentica.
2. **Pre-paga créditos** (saldo prepago, sin suscripción).
3. Cada consulta **descuenta créditos** según su coste; sin saldo, el servicio
   deniega la petición (fail-closed).

Superficie doble sobre el mismo backend:

- **API REST** (`/api/v1/...`): integrable desde cualquier stack.
- **Servidor MCP remoto** (Streamable HTTP): el mismo servicio expuesto como
  *tools* que Claude, ChatGPT, Cursor u otros clientes MCP consumen
  directamente. MCP es el escaparate; la API es el contrato.

## 2. Qué se vende exactamente (catálogo de operaciones)

Dos niveles de producto con precios muy distintos, porque su coste marginal es
muy distinto:

| Nivel | Operación | Coste marginal | Precio orientativo |
|---|---|---|---|
| **Lookup** (sin LLM) | Recuperar sentencia/ficha, precepto, convenio por país, búsqueda estructurada por cuestión jurídica | ~0 (lectura de corpus) | 1 crédito |
| **Answer** (con LLM) | Pregunta en lenguaje natural → respuesta redactada con citas literales (sentencia, página, extracto) | Coste real del gateway (Luna `high`) | 10–50 créditos según tokens |

Como *tools* MCP (nombres provisionales):

- `buscar_jurisprudencia(cuestion, filtros)` — unidades de recuperación por
  cuestión del corpus v3 (las 74 unidades / 67 casos en recuperación). Lookup.
- `obtener_sentencia(id)` — proyección pública del caso (la allowlist de
  `public_judgment_projection`), nunca el schema interno. Lookup.
- `obtener_precepto(jurisdiccion, norma, articulo)` — Markdown del precepto de
  `knowledge/normativa/es/preceptos/`. Lookup.
- `convenio(pais)` — artículo de residencia del CDI aplicable y enlace BOE. Lookup.
- `responder(pregunta)` — la respuesta conversacional del chat (estrategia A,
  `current_structured`), con fuentes y extractos. Answer.
- `saldo()` — créditos restantes, gratis.

**Regla de honestidad heredada del proyecto:** toda respuesta y ficha viaja con
la etiqueta `AGENT_REVIEWED_ONLY` en los metadatos. La API nunca afirma revisión
humana inexistente; el contrato de la API lo declara explícitamente y es un
argumento de venta (trazabilidad literal a PDF), no una vergüenza a esconder.

## 3. Cuentas, tokens y autenticación

- **Cuenta = organización**, no persona: un despacho o un producto que integra
  agentes. Email verificado + datos de facturación mínimos.
- **API keys** con formato reconocible (`rf_live_...` / `rf_test_...`),
  mostradas una sola vez, almacenadas **solo como hash** (SHA-256) en Supabase.
  Varias claves por cuenta, revocables individualmente; prefijo visible para
  identificarlas en el panel.
- **MCP:** el cliente MCP se autentica con la misma API key vía cabecera
  (`Authorization: Bearer rf_live_...`). OAuth 2.1 (el flujo canónico de MCP
  remoto para clientes de consumo como claude.ai) se pospone a una fase
  posterior; las claves bastan para agentes programáticos.
- **Fail-closed en todo:** sin clave válida → 401; clave revocada → 401; sin
  saldo → 402 con el saldo actual y la URL de recarga en el cuerpo del error.

## 4. Créditos: modelo económico y contable

### Por qué créditos y no USD directos

El coste marginal por respuesta LLM es variable (tokens) y la medición puede
ser `ACTUAL`, `ESTIMATED` o `UNAVAILABLE` (regla ya vigente en el proyecto). Un
crédito abstracto permite: precio estable de cara al cliente, margen implícito,
y redondeos sin renegociar tarifas cuando cambie el modelo del gateway.

- **1 crédito ≈ 0,01 € de PVP** (paquetes: 500 / 2.500 / 10.000 créditos, con
  descuento por volumen). Caducidad: 12 meses (revisar jurídicamente).
- **Pre-pago con Stripe Checkout** (fase 2; en fase 1, recarga manual contra
  factura). Stripe es un encargado nuevo → **hay que actualizar `/privacidad`
  en el mismo cambio** (regla del proyecto).

### Contabilidad (Supabase, schema `private`)

Mismo patrón que la persistencia actual del chat: tablas privadas con RLS, la
Function solo llama **RPC `SECURITY DEFINER` atómicas**, nunca escribe tablas.

| Tabla nueva | Responsabilidad |
|---|---|
| `private.api_accounts` | Cuenta, email verificado, estado |
| `private.api_keys` | Hash de la clave, prefijo, scopes, revocación |
| `private.credit_ledger` | **Append-only**: recargas (+) y consumos (−), con `request_id`, operación, coste observado en microUSD y calidad de medición |
| `private.api_usage_requests` | Registro idempotente por petición (análogo a `chat_requests`) |

El saldo es `SUM(ledger)` materializado, nunca una columna mutable suelta.

### Flujo de cobro por petición (reserva → liquidación)

1. `authorize_api_request(key_hash, op)` — RPC atómica: valida clave, comprueba
   `saldo ≥ precio_máximo(op)`, **reserva** ese máximo y registra la petición.
2. Se ejecuta la operación (lookup o llamada al gateway).
3. `settle_api_request(request_id, coste_real)` — liquida el precio final según
   tokens reales y **devuelve la reserva sobrante**. Si la medición del coste es
   `UNAVAILABLE`, se liquida el precio máximo tabulado de la operación — nunca
   cero (invariante del proyecto: un coste no calculable no se presenta como
   cero, y aquí además no se regala).
4. Fallo del proveedor antes de generar respuesta → `refund_api_request`:
   reserva devuelta íntegra, el cliente no paga errores nuestros.

Cada respuesta devuelve cabeceras `X-RF-Credits-Charged`, `X-RF-Credits-Balance`
y `X-RF-Cost-Measurement` (ACTUAL/ESTIMATED/UNAVAILABLE): el agente puede
presupuestar y auditar, coherente con cómo el chat ya muestra su coste.

**Nota sobre la regla «el coste nunca decide la admisión»:** esa regla protege
al usuario anónimo de la web. Aquí no aplica: en un servicio prepago la admisión
depende del saldo *del cliente*, que es exactamente lo contratado. Documentarlo
para que no parezca una contradicción.

## 5. Arquitectura técnica

**Recomendación: reutilizar el runtime existente, no crear un backend nuevo.**

```text
Agente externo ──HTTP──▶ Netlify Function `api` (REST v1)
Cliente MCP ────HTTP──▶ Netlify Function `mcp` (Streamable HTTP)
                              │  ambas componen los mismos módulos:
                              ├─ auth (hash de clave + RPC authorize)
                              ├─ metering (reserva/liquidación en ledger)
                              ├─ retrieval (structured-retrieval.ts existente)
                              ├─ answer (current-structured-strategy.ts + gateway)
                              └─ Supabase (RPC atómicas, schema private)
```

- La lógica de recuperación y redacción **ya existe** en
  `frontend/netlify/functions/chat/`; se extrae lo compartible a módulos
  comunes y las nuevas Functions los componen. No se duplica la estrategia A.
- La API **no expone la estrategia B** (Gemini File Search): es una pata del
  experimento comparativo, no un producto.
- Deadline: mismas restricciones de Netlify (~60 s síncronos). Los lookups son
  instantáneos; `responder` cabe en el deadline actual del chat. Si algún día
  no cabe, el prototipo FastAPI local ya está señalado en el proyecto como
  arquitectura futura para >60 s — no se resuelve ahora (YAGNI).
- **Rate limiting por clave** además del saldo (p. ej. 60 req/min lookup,
  10 req/min answer): el saldo protege el dinero, el rate limit protege el
  servicio.
- Observabilidad: mismo patrón Sentry sin SDK de la Function del chat (envelope
  a mano, sin pregunta/respuesta/PII), y el consumo entra en el resumen diario
  de coste sobre el ledger.

### Alternativas consideradas

- **A (recomendada):** Functions nuevas `api` + `mcp` componiendo los módulos
  del chat. Mínimo código nuevo, una sola fuente de verdad de retrieval.
- **B:** backend FastAPI dedicado (el prototipo local ya existe). Más control y
  sin límite de 60 s, pero añade un runtime que operar, desplegar y respaldar;
  prematuro sin demanda que lo justifique.
- **C:** pasarela de terceros de monetización de API (Stripe metered billing
  puro, o marketplaces de tools). Menos código de créditos, pero pierde el
  ledger propio auditable, encaja mal con prepago y añade otro encargado de
  datos. Descartada para V1.

## 6. Privacidad y marco legal (bloqueante, no decorativo)

- Las preguntas de agentes son **dato fiscal** igual que las del chat: misma
  política — no van a Sentry, retención acotada (¿los mismos 15 días para el
  contenido, ledger contable sin contenido conservado más tiempo por
  obligación mercantil?), sin IP ni user-agent en tablas de contenido.
- `/privacidad` debe ampliarse en el mismo cambio: nueva finalidad (servicio
  API), nueva base jurídica (ejecución de contrato), Stripe como encargado,
  retención diferenciada del ledger.
- **Términos de servicio del API** (nuevo documento): no es asesoramiento
  jurídico, análisis generado por modelo (`AGENT_REVIEWED_ONLY`), sin garantía
  de exhaustividad, límites de uso, política de reembolso de créditos.
- Los avisos legales de CENDOJ y BOE ya cubren la reutilización del corpus;
  revisar que la reventa vía API respeta sus condiciones (el texto judicial y
  normativo es reutilizable, pero conviene dejarlo escrito).

## 7. Dependencias y orden de fases

**Dependencia dura:** el chat de producción debe estar plenamente operativo y
estabilizado antes de vender su salida por API; el despliegue y su operación se
rigen por [`CHAT_DEPLOYMENT.md`](../operations/CHAT_DEPLOYMENT.md). Además, el
corpus sigue `AGENT_REVIEWED_ONLY` sin aprobación jurídica humana: vender acceso
no cambia ese estado y los ToS deben declararlo.

- **F1 — Piloto manual (diseño validable ya):** tablas + RPC de ledger, una
  API key creada a mano para 1–3 clientes de confianza, recarga manual, solo
  endpoints lookup + `responder`. Sin panel, sin Stripe. Objetivo: validar que
  alguien paga por esto.
- **F2 — Self-service:** registro con email verificado, panel mínimo de claves
  y saldo, Stripe Checkout, facturas. Actualización de `/privacidad` y ToS.
- **F3 — MCP remoto público:** Function MCP Streamable HTTP, listado en
  directorios de servidores MCP, OAuth 2.1 si aparecen clientes de consumo.

## 8. Riesgos y preguntas abiertas

1. **¿Hay demanda?** F1 existe para responderlo barato antes de construir F2.
2. **Precio del crédito y de `responder`:** exige medir el coste real medio por
   respuesta (el ledger del chat ya lo registra) y decidir margen.
3. **Fiscalidad de la venta** (Intangible Land LLC, EE. UU., clientes UE, IVA
   de servicios electrónicos B2B/B2C): pregunta para el asesor, no para el código.
4. **Caducidad de créditos** y reembolsos: revisar validez legal en UE.
5. **Abuso:** scraping masivo del corpus vía lookups baratos → rate limits y,
   si hace falta, precios por volumen que lo hagan antieconómico.
6. **¿`responder` expone el corpus completo o solo lo publicable?** Propuesta:
   mismas fuentes que el chat web en cada momento; la API nunca adelanta
   contenido que la web no haya promocionado (respeta los gates jurídicos
   existentes).
