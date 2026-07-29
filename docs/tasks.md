# Tareas pendientes

Backlog operativo del proyecto. Las tareas SEO y de despliegue deben verificarse
contra el dominio público después de cada deploy.

## Prioridad alta

- [ ] Verificar el deploy público de `https://residenciafiscal.org/`: el build local está
  completo, pero la comprobación externa sigue dependiendo de Netlify y del WAF de Cloudflare.
- [x] Implementar la ruta pública `/metodologia` con el método, el corpus de 106
  sentencias y sus limitaciones.
- [x] Añadir `/metodologia` a `frontend/public/sitemap.xml`
  y enlazarla desde `frontend/public/llms.txt`.

## Producto y arquitectura

- [ ] Sustituir el motor `stub` del chat por un backend RAG real basado en el corpus,
  con respuestas fundamentadas, citas a sentencias, nivel de confianza y límites de coste.
- [ ] Diseñar las landings por país con un modelo de datos reutilizable, URLs canónicas
  ASCII (`/espana`, `/portugal`, etc.) y redirecciones para variantes con caracteres especiales.
- [ ] Definir el contrato del endpoint de chat, manejo de errores, cancelación de peticiones,
  límites de uso y estrategia de fallback del proveedor LLM.

## SEO y contenido

- [ ] Añadir metadatos, canonical, Open Graph, schema.org y enlaces internos específicos
  para cada landing de país.
- [ ] Mostrar en cada landing las fuentes legales, fecha de revisión, alcance y limitaciones
  del contenido, con un proceso editorial para mantenerlo actualizado.

## Seguridad y datos

- [ ] Exigir `RESIDENCIAFISCAL_API_TOKEN` en producción, proteger `/analizar` con rate
  limiting y evitar que las consultas sensibles aparezcan completas en logs o analítica.
- [x] Añadir validación automática del schema del corpus, detección de duplicados y
  trazabilidad de cada criterio hasta su sentencia de origen.

## Calidad y despliegue

- [x] Configurar CI con lint, typecheck, tests y build del frontend y la API.
- [ ] Añadir smoke tests de navegador para `/`, `/metodologia` y las landings públicas,
  incluyendo comprobación de redirecciones, sitemap, robots y corpus publicado.
- [x] Documentar y automatizar el pipeline reproducible de actualización del corpus y su deploy.

## SEO y operación

- [ ] Crear una landing específica por país (`/españa`, `/portugal`, etc.) con información detallada sobre la residencia fiscal, criterios, obligaciones y particularidades de cada país.
- [ ] Configurar Sentry y PostHog para el frontend y documentar sus variables de entorno.
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
