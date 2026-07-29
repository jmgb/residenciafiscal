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

- `frontend/src/data/countryRoutes.ts` es la fuente única de nombres y rutas.
- `frontend/src/pages/CountryPage.tsx` contiene la plantilla compartida.
- `frontend/src/pages/SpainPage.tsx` es el punto de entrada específico de España y reutiliza
  `ChatView`.
- `frontend/src/App.tsx` registra las rutas de país a partir de `COUNTRY_ROUTES`.
- `frontend/src/components/layout/SidebarContent.tsx` reutiliza la misma lista para el menú
  lateral de escritorio y móvil.
- `frontend/scripts/prerender.mjs` prerenderiza `/españa` para SEO. Las páginas aún no
  publicadas no entran en el sitemap.

## Cómo activar un país

Cuando exista la documentación nacional revisada y trazable:

1. Añadir el corpus y su pipeline de recuperación aislados del corpus español.
2. Definir el contrato del motor de consulta para que reciba el país y no pueda consultar por
   accidente documentos de otro país.
3. Añadir tests de aislamiento: una consulta de México no puede devolver una cita de España.
4. Sustituir la plantilla de preparación por contenido y CTA propios del país, manteniendo la
   ruta de `CountryRoute`.
5. Añadir el prerender y el sitemap solo cuando la página tenga contenido público real.
6. Actualizar el estado de esta documentación y ejecutar `npm run fast-check` dentro de
   `frontend/`.

La plantilla actual no afirma que una página tenga jurisprudencia disponible: el mensaje se
personaliza con el nombre del país y deja explícito que el corpus correspondiente está en
preparación.
