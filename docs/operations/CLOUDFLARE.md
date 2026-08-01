# Cloudflare — residenciafiscal.org

Configuración aplicada el 2026-07-29 sobre la zona `residenciafiscal.org`.

## DNS y TLS

| Host | Tipo | Destino | Proxy |
| --- | --- | --- | --- |
| `residenciafiscal.org` | CNAME | `apex-loadbalancer.netlify.com` | Sí |
| `www.residenciafiscal.org` | CNAME | `residenciafiscal.netlify.app` | Sí |

- SSL/TLS: `Full (strict)`.
- TLS mínimo: `1.2`.
- HTTPS forzado: activado.
- HTTP/3, TLS 1.3, 0-RTT, Brotli y Early Hints: activados.
- HSTS: 180 días, `includeSubDomains`, sin `preload`, con `nosniff`.
- Caché: configuración de zona alineada con Presupuestor (`aggressive`, edge TTL 7200 s).

El origen Netlify presenta un certificado Let’s Encrypt válido para `residenciafiscal.org`
y `www.residenciafiscal.org`, vigente hasta el 2026-10-26. Netlify debe seguir renovándolo.

## WAF

- Ruleset gestionado: `residenciafiscal managed waf`
  (`bab006f201dc447b88bc9c1c077693ca`). Ejecuta el `Cloudflare Managed Free Ruleset`.
- Ruleset custom: `residenciafiscal custom firewall`
  (`655cbe842a2f4120aa857c3c7cb485b6`).
  - Bloquea User-Agents de scanners y probes de archivos sensibles.
  - Excluye `/assets/` y bots verificados de esa regla.
  - La regla de Managed Challenge geográfico para tráfico no verificado desde EE. UU.
    está desactivada desde el 2026-07-29. Bloqueaba verificadores públicos y usuarios
    legítimos con `403`, sin aportar una protección proporcional para un frontend estático.
  - Se mantienen activos el bloqueo de scanners y el ruleset gestionado de Cloudflare.
- La regla de bypass para la IP del VPS de Presupuestor no se copia: este proyecto no
  tiene un VPS/origen privado equivalente.

Las reglas de cache del sitemap y rate-limit de análisis de Presupuestor tampoco se
copian porque este dominio es un frontend estático y no expone esos endpoints.

## Agentes de LLM

El proyecto quiere aparecer en las respuestas de los asistentes, así que **todas
las protecciones antibot de Cloudflare que los afectan están desactivadas a
propósito**: `ai_bots_protection`, `crawler_protection`, `content_bots_protection`
y `fight_mode`. `is_robots_txt_managed` está en `false`, de modo que Cloudflare no
inyecta su propio bloque en `robots.txt` y lo servido es exactamente
`frontend/public/robots.txt`. Activar cualquiera de esas opciones desde el panel
anula la política declarada allí, sin que ningún test del repositorio lo detecte:

```bash
curl -s -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  https://api.cloudflare.com/client/v4/zones/$ZONE_ID/bot_management
```

La regla custom sí bloquea `curl`, `wget`, `python-requests`, `axios`, `okhttp`,
`go-http-client` y `headlesschrome`, pero lleva `not cf.client.bot`: los bots
verificados por Cloudflare —GPTBot, ClaudeBot, PerplexityBot, Googlebot y
compañía— quedan fuera del bloqueo. Lo que sí recibe `403` es un script propio o
un agente casero que se anuncie con uno de esos User-Agents genéricos; por eso el
`curl` de verificación de este documento lleva un User-Agent propio.

## Verificación

```bash
curl -A 'Mozilla/5.0 (compatible; residenciafiscal-verifier/1.0)' -I \
  https://residenciafiscal.org/
curl -A 'Mozilla/5.0 (compatible; residenciafiscal-verifier/1.0)' -I \
  https://www.residenciafiscal.org/
```

El apex es el dominio canónico. `www` debe redirigir al apex y ambas variantes
deben mantener TLS válido. Si el verificador recibe un challenge o un `403`, hay
que revisar primero las reglas custom del WAF antes de atribuirlo a Netlify.

Tras desactivar el challenge geográfico, una verificación distribuida devolvió
`200` en 30 de 30 nodos, incluidos cuatro nodos de Estados Unidos.
