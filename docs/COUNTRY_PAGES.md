# Páginas por país

## Estado actual

El frontend ya tiene una entrada por país para que la navegación y la arquitectura puedan
crecer sin rehacer el menú:

- `/` redirige a `/españa`.
- `/españa` conserva literalmente la experiencia que antes vivía en la home: el chat, las
  sugerencias de preguntas y el aviso del motor simulado.
- La barra lateral incluye España y las rutas reservadas para los principales países de
  Latinoamérica.
- Las rutas latinoamericanas muestran la misma plantilla y el mismo mensaje de preparación,
  personalizado solo con el nombre del país.
- `/consulta` y `/c/:conversationId` conservan rutas directas para la interfaz de consulta
  existente. Las rutas futuras no apuntan automáticamente a ella porque todavía no existe un
  corpus nacional para esos países.
- La barra lateral muestra tres países al principio y `Mostrar más` despliega el resto. En modo
  rail queda un acceso compacto a la sección, como en el menú lateral de Presupuestor.

Las rutas reservadas actualmente son:

| País | Ruta |
| --- | --- |
| España | `/españa` |
| Argentina | `/argentina` |
| Bolivia | `/bolivia` |
| Brasil | `/brasil` |
| Chile | `/chile` |
| Colombia | `/colombia` |
| Costa Rica | `/costa-rica` |
| Cuba | `/cuba` |
| Ecuador | `/ecuador` |
| El Salvador | `/el-salvador` |
| Guatemala | `/guatemala` |
| Haití | `/haiti` |
| Honduras | `/honduras` |
| México | `/mexico` |
| Nicaragua | `/nicaragua` |
| Panamá | `/panama` |
| Paraguay | `/paraguay` |
| Perú | `/peru` |
| República Dominicana | `/republica-dominicana` |
| Uruguay | `/uruguay` |
| Venezuela | `/venezuela` |

## Organización del código

- `frontend/src/data/countryRoutes.json` es la fuente única de nombres, rutas y metadata SEO.
- `frontend/src/data/countryRoutes.ts` tipa esa fuente para el frontend.
- `frontend/src/pages/CountryPage.tsx` contiene la plantilla compartida.
- `frontend/src/pages/SpainPage.tsx` es el punto de entrada específico de España y reutiliza
  `ChatView`.
- `frontend/src/App.tsx` registra las rutas de país a partir de `COUNTRY_ROUTES`.
- `frontend/src/components/layout/SidebarContent.tsx` reutiliza la misma lista para el menú
  lateral de escritorio y móvil.
- `frontend/src/types/chat.ts` define `ChatRequestContext`, que acompaña cada consulta con el
  país seleccionado.
- `frontend/src/lib/chat-engine.ts` bloquea el uso del corpus español cuando recibe un país sin
  corpus registrado.
- `frontend/scripts/prerender.mjs` prerenderiza todas las rutas de país con título, descripción y
  canonical propios.
- `frontend/scripts/build-sitemap.mjs` genera el sitemap usando solo las rutas con
  `indexable: true`. Por eso los placeholders tienen SEO preparado, pero no se publican como
  contenido indexable hasta que exista su corpus.
- `netlify.toml` mantiene un redirect estático por ruta hacia su HTML prerenderizado.

## Política de URLs y SEO

Los nombres visibles conservan la ortografía española, pero las rutas nuevas usan slugs ASCII
para evitar problemas de codificación (`/mexico`, `/peru`, `/panama`). Se mantiene `/españa`
porque es la ruta pública solicitada y ya forma parte del canonical del proyecto.

Para publicar un país, completa su `description`, cambia `indexable` a `true` y sustituye la
plantilla de preparación por su experiencia real. El prerender y el sitemap se actualizan desde
la fuente JSON durante `npm run build`; no hay que editar el sitemap a mano.

## Cómo activar un país

Cuando exista la documentación nacional revisada y trazable:

1. Añadir el corpus y su pipeline de recuperación aislados del corpus español.
2. Registrar el corpus en el motor y mantener el contrato `ChatRequestContext` para que no pueda
   consultar por accidente documentos de otro país.
3. Añadir tests de aislamiento: una consulta de México no puede devolver una cita de España.
4. Sustituir la plantilla de preparación por contenido y CTA propios del país, manteniendo la
   ruta de `CountryRoute`.
5. Añadir el prerender y el sitemap solo cuando la página tenga contenido público real.
6. Actualizar el estado de esta documentación y ejecutar `npm run fast-check` dentro de
   `frontend/`.

Las páginas futuras no afirman que tengan jurisprudencia disponible: el mensaje se personaliza
con el nombre del país y deja explícito que el corpus correspondiente está en preparación.
