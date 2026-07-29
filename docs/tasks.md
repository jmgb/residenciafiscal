# Tareas pendientes

Backlog operativo del proyecto. Las tareas SEO y de despliegue deben verificarse
contra el dominio público después de cada deploy.

## Prioridad alta

- [ ] Resolver el `404` de `https://residenciafiscal.org/` en Netlify y completar el
  build del frontend. El estado actual referencia `frontend/src/main.tsx` y
  `frontend/scripts/build-corpus.mjs`, que deben existir en el build publicado.
- [ ] Implementar la ruta pública `/metodologia` con el método, el corpus de 106
  sentencias y sus limitaciones.
- [ ] Cuando `/metodologia` devuelva `200`, añadirla a `frontend/public/sitemap.xml`
  y enlazarla desde `frontend/public/llms.txt`.

## SEO y operación

- [ ] Tras un deploy correcto, comprobar que `robots.txt`, `sitemap.xml` y `llms.txt`
  devuelven `200` desde `https://residenciafiscal.org/`.
- [ ] Registrar `https://residenciafiscal.org/sitemap.xml` en Google Search Console
  y revisar la primera descarga y los errores de cobertura.
- [ ] Revisar durante varios días los eventos del WAF. Ajustar la regla custom si
  los User-Agents genéricos (`curl`, `axios`, `python-requests`) bloquean monitores
  o integraciones legítimas.

## Criterio de cierre SEO

- El home y `/metodologia` responden `200` y tienen canonical propia.
- El sitemap sólo contiene URLs públicas, canónicas y rastreables.
- `/c/` permanece fuera del índice por ser contenido de conversación dinámico.
- El WAF no bloquea Googlebot, crawlers LLM ni monitores autorizados.
