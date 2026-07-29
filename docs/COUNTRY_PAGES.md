# Páginas por país

## Estado actual

El frontend ya tiene una entrada por país para que la navegación y la arquitectura puedan
crecer sin rehacer el menú:

- `/` redirige a `/espana`.
- `/espana` conserva literalmente la experiencia que antes vivía en la home: el chat, las
  sugerencias de preguntas y el aviso del motor simulado.
- La barra lateral incluye España y las rutas reservadas para los principales países de
  Latinoamérica.
- Las rutas latinoamericanas muestran la misma plantilla: una **invitación a contribuir**
  personalizada con el nombre del país, no un simple aviso de «próximamente». La plantilla
  explica que el pipeline es agnóstico de la jurisdicción y enumera las tres aportaciones que
  necesita un país nuevo (fuente oficial, precepto de residencia y revisión humana).
- `/consulta` y `/c/:conversationId` conservan rutas directas para la interfaz de consulta
  existente. Las rutas futuras no apuntan automáticamente a ella porque todavía no existe un
  corpus nacional para esos países.
- La barra lateral muestra tres países al principio y `Mostrar más` despliega el resto. En modo
  rail queda un acceso compacto a la sección, como en el menú lateral de Presupuestor.

Las rutas reservadas actualmente son:

| País | Ruta |
| --- | --- |
| España | `/espana` |
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
- `frontend/src/pages/CountryPage.tsx` contiene la plantilla compartida, con la invitación a
  contribuir. `frontend/tests/CountryPage.test.tsx` fija su copy y el enlace de la issue.
- `frontend/src/lib/contribution.ts` construye la URL del formulario
  `.github/ISSUE_TEMPLATE/aportar_pais.yml` con el país prerrellenado. Es el único punto donde
  vive la URL del repositorio: si se renombra la plantilla, se cambia ahí.
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

Los nombres visibles conservan la ortografía española, pero las rutas canónicas usan slugs ASCII
para evitar problemas de codificación (`/espana`, `/mexico`, `/peru`, `/panama`). Las variantes
acentuadas históricas (`/españa`, `/perú`, `/méxico`, etc.) redirigen al slug canónico.

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
con el nombre del país y deja explícito que su corpus todavía no existe.

## La invitación a contribuir

El proyecto es colaborativo y las páginas sin corpus son su punto de entrada: en lugar de un
«próximamente» pasivo, piden lo que realmente falta. Un test lo fija para que el copy no se
degrade con el tiempo.

- El enlace lleva al formulario `aportar_pais.yml` con el título y el campo `pais` ya rellenados
  vía query params, así que quien llega desde `/chile` no tiene que explicar de qué país habla.
- La invitación es **abierta a cualquier jurisdicción**, no solo a los 20 países con ruta. El
  texto no promete fecha ni da por hecho que el país vaya a publicarse.
- El segundo CTA apunta a `CONTRIBUTING.md`, donde está el detalle operativo y los invariantes
  (no reescribir el texto de una resolución, no subir documentos antes de resolver su
  reutilización, aislamiento entre corpus).
- La `description` de cada ruta pendiente dice lo mismo que la página. Son `indexable: false`, así
  que no entran en el sitemap ni permiten indexación (`noindex, follow`), pero sí se prerenderizan:
  la tarjeta social de `/peru` compartida en redes tiene que invitar a contribuir, no anunciar
  contenido que no existe.

Al publicar un país, esta sección de su página desaparece junto con la plantilla.
