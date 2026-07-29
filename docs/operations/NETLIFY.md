# Netlify — residenciafiscal.org

## Configuración del sitio

El fichero [`netlify.toml`](../../netlify.toml) configura:

- base `frontend`, comando `npm run build` y publicación de `dist`;
- Node.js 24;
- reconstrucción cuando cambia `frontend/` o `netlify.toml`;
- fallback SPA `/*` → `/index.html`;
- cabeceras de seguridad, CSP compatible con GA4 y caché de assets;
- `frontend/public/data/corpus.json` como corpus versionado de respaldo.

El build usa `output/analisis_*.jsonl` si existe en el checkout. Como `output/`
se ignora por contener resultados generados, el prebuild conserva el corpus
versionado cuando Netlify construye desde un clon limpio.

## Dominio y DNS

En Netlify deben estar configurados como dominios personalizados:

- `www.residenciafiscal.org` como dominio primario;
- `residenciafiscal.org` como dominio adicional con redirección al primario.

En Cloudflare, ambos registros permanecen DNS-only:

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
```

En producción comprobar:

1. `https://www.residenciafiscal.org/` responde `200` y el apex redirige al
   dominio primario.
2. La navegación directa a una ruta SPA no devuelve `404`.
3. `/data/corpus.json` contiene sentencias y no `[]`.
4. DevTools → Network muestra `gtag/js` y peticiones de GA4.

El despliegue seguirá fallando hasta que existan `frontend/src/main.tsx` y
`frontend/src/App.tsx`, que son el punto de entrada y la composición de la SPA
pendientes de implementar.
