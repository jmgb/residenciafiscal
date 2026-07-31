# Netlify — residenciafiscal.org

## Configuración del sitio

El fichero [`netlify.toml`](../../netlify.toml) configura:

- base `frontend`, comando `npm run build` y publicación de `dist`;
- Node.js 24;
- Functions estándar desde `frontend/netlify/functions/`;
- reconstrucción cuando cambia `frontend/` o `netlify.toml`;
- fallback SPA `/*` → `/index.html`;
- rewrites a los HTML prerenderizados antes del fallback: las rutas estáticas
  (`/manifiesto`, `/metodologia`, `/espana/fuentes`, `/colaborar`) viven en `netlify.toml`; las rutas de país y
  las redirecciones 301 de los slugs acentuados históricos se generan desde
  `frontend/src/data/countryRoutes.json` en `frontend/public/_redirects` y Vite las copia a
  `dist/`. `tests/test_frontend_seo_assets.py` comprueba que el fichero generado sigue alineado
  con su fuente;
- cabeceras de seguridad, CSP compatible con GA4 y caché de assets;
- redirecciones a `404.html` para `/assets/*` y `/data/*` **antes** del fallback,
  para que un fichero ausente no devuelva la shell HTML con 200;
- `frontend/public/data/corpus.json` como corpus versionado de respaldo.

Las reglas de caché por ruta, el manifiesto `/version.json` y la detección de
versión nueva en el navegador están en
[`CACHE_AND_RELEASES.md`](CACHE_AND_RELEASES.md). Es lectura obligatoria antes de
tocar cualquier bloque `[[headers]]` o el fallback: las dos reglas que parecían
correctas no se aplicaban a las URL reales.

El build usa `output/analisis_*.jsonl` si existe en el checkout. Como `output/`
se ignora por contener resultados generados, el prebuild conserva el corpus
versionado cuando Netlify construye desde un clon limpio.

## Function del chat

La V1 expone `/api/chat` mediante una Function estándar autosuficiente. Ejecuta
en paralelo la estrategia A estructurada y Gemini File Search B, aplica rate
limit, reserva presupuesto atómico en Supabase y devuelve el protocolo
SSE 2 como cuerpo bufferizado. Las claves de proveedor solo existen como
variables de Functions; `VITE_CHAT_MODE` es únicamente el selector de build del
cliente. El endpoint y el frontend permanecen cerrados por separado hasta
superar los gates. Variables, migración, activación y rollback están en
[`CHAT_DEPLOYMENT.md`](CHAT_DEPLOYMENT.md).
El modelo privado de mensajes y costes se documenta en
[`SUPABASE_CHAT.md`](SUPABASE_CHAT.md).

El antiguo proxy Edge → FastAPI vive fuera del camino productivo en
`frontend/netlify/prototypes/chat-fastapi-edge.ts`. Sus límites reales —CPU,
streaming y Blobs— están **medidos**, no leídos de la documentación, en
[`NETLIFY_EDGE.md`](NETLIFY_EDGE.md). Léelo antes de escribir una edge function
en este proyecto: incluye tres trampas que cuestan un deploy cada una (los
ficheros de la raíz son todos endpoints, el compare-and-swap de Blobs no es
atómico y `netlify dev` no arranca aquí).

## Dominio y DNS

En Netlify deben estar configurados como dominios personalizados:

- `residenciafiscal.org` como dominio primario;
- `www.residenciafiscal.org` como dominio adicional con redirección al primario.

En Cloudflare, ambos registros están proxied:

```text
residenciafiscal.org      CNAME  apex-loadbalancer.netlify.com
www                       CNAME  residenciafiscal.netlify.app
```

Cloudflare aplana el CNAME del apex automáticamente. Netlify debe emitir y
renovar el certificado TLS de ambos nombres.

## Verificación después de un deploy

Desde la raíz del repositorio:

```bash
cd frontend
npm run typecheck
npm test
npm run build
cd ..
build_dir=$(mktemp -d /tmp/residenciafiscal-functions.XXXXXX)
netlify functions:build --src frontend/netlify/functions --functions "$build_dir"
```

En producción comprobar:

1. `https://residenciafiscal.org/` responde `200` y `www` redirige al dominio primario.
2. La navegación directa a una ruta SPA no devuelve `404`.
3. `/data/corpus.json` contiene sentencias y no `[]`.
4. DevTools → Network muestra `gtag/js` y peticiones de GA4.
5. Con el chat cerrado, `POST /api/chat` responde `503` sin consumir presupuesto.
6. En Deploy Preview live, una consulta devuelve A y B antes de 60 s y crea un
   registro de coste sin pregunta, respuesta ni citas.

Las rutas públicas sin barra final deben servir sus metadatos prerenderizados, no
la shell de la home. `test_frontend_seo_assets.py` protege el orden de esos rewrites.
