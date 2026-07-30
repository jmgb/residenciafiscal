# Páginas por país

## Estado actual

El frontend ya tiene una entrada por país para que la navegación y la arquitectura puedan
crecer sin rehacer el menú:

- `/` redirige a `/espana`.
- `/espana` conserva literalmente la experiencia que antes vivía en la home: el chat, las
  sugerencias de preguntas y el aviso del motor simulado.
- La barra lateral incluye España y las rutas reservadas para las jurisdicciones prioritarias
  de Europa, Estados Unidos y Latinoamérica.
- Las rutas pendientes muestran la misma plantilla: una **invitación a contribuir**
  personalizada con el nombre del país, no un simple aviso de «próximamente». La plantilla
  explica que el pipeline es agnóstico de la jurisdicción y enumera las tres aportaciones que
  necesita un país nuevo (fuente oficial, precepto de residencia y revisión humana).
- `/consulta` y `/c/:conversationId` conservan rutas directas para la interfaz de consulta
  existente. Ambas se resuelven como contexto español en la cabecera porque consultan
  `SPAIN_ROUTE`. Las rutas futuras no apuntan automáticamente a ella porque todavía no existe un
  corpus nacional para esos países.
- La cabecera de marca describe el contexto real: `España · Art. 9 LIRPF` para el corpus
  español, `<País> · Sin corpus` para una jurisdicción pendiente y `Jurisprudencia por país`
  en las páginas institucionales.
- La barra lateral muestra tres países al principio y `Mostrar más` despliega el resto. En modo
  rail queda un acceso compacto a la sección, como en el menú lateral de Presupuestor.

Las rutas reservadas actualmente son:

| País | Ruta |
| --- | --- |
| España | `/espana` |
| Estados Unidos | `/estados-unidos` |
| Portugal | `/portugal` |
| Francia | `/francia` |
| Reino Unido | `/reino-unido` |
| Alemania | `/alemania` |
| Suiza | `/suiza` |
| Andorra | `/andorra` |
| Italia | `/italia` |
| México | `/mexico` |
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
| Nicaragua | `/nicaragua` |
| Panamá | `/panama` |
| Paraguay | `/paraguay` |
| Perú | `/peru` |
| República Dominicana | `/republica-dominicana` |
| Uruguay | `/uruguay` |
| Venezuela | `/venezuela` |

## Organización del código

- `frontend/src/data/countryRoutes.json` es la fuente única de nombres, rutas, estado del corpus,
  metadata SEO y referencias jurídicas validadas.
- `frontend/src/data/countryRoutes.ts` valida esa fuente al cargarla, la tipa para el frontend y
  resuelve el contexto de las rutas de consulta.
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
  `indexable: true`. `indexable` solo gobierna SEO; no debe usarse para inferir si existe corpus.
- `frontend/scripts/build-netlify-redirects.mjs` genera `frontend/public/_redirects` desde la
  fuente JSON. Vite lo copia a `dist/`, que es el directorio publicado por Netlify, así que no
  hay que duplicar las rutas de país en `netlify.toml`.

## Política de URLs y SEO

Los nombres visibles conservan la ortografía española, pero las rutas canónicas usan slugs ASCII
para evitar problemas de codificación (`/espana`, `/mexico`, `/peru`, `/panama`). Las variantes
acentuadas históricas (`/españa`, `/perú`, `/méxico`, etc.) redirigen al slug canónico.

Cada entrada de `countryRoutes.json` mantiene dos estados independientes:

- `corpusStatus`: `pending` o `published`. Controla si la interfaz anuncia corpus y qué muestra
  la cabecera.
- `indexable`: decisión editorial de SEO. Controla robots y sitemap, no la disponibilidad del
  corpus.

`legalReferences` es una lista porque no todas las jurisdicciones concentran la residencia en un
único artículo. Cada referencia conserva:

- `kind`: `domestic-residence` o `tax-treaty`;
- `shortCitation`: texto compacto y verificable para la interfaz;
- `title`: título oficial de la norma;
- `officialUrl`: enlace a la fuente pública oficial.

La primera referencia es la principal y alimenta el subtítulo compacto de una jurisdicción
publicada. No se incorporan equivalencias obtenidas de blogs, memoria o búsquedas automáticas:
las valida un especialista de la jurisdicción. Un país `pending` muestra siempre `Sin corpus`,
aunque ya tenga referencias documentadas, para no confundir normativa localizada con
jurisprudencia publicada.

## Cómo activar un país

Cuando exista la documentación nacional revisada y trazable:

1. Añadir el corpus y su pipeline de recuperación aislados del corpus español.
2. Registrar el corpus en el motor y mantener el contrato `ChatRequestContext` para que no pueda
   consultar por accidente documentos de otro país.
3. Añadir tests de aislamiento: una consulta de México no puede devolver una cita de España.
4. Registrar al menos una referencia jurídica oficial validada en `legalReferences`, dejando
   primero la que deba identificar el marco nacional en superficies compactas.
5. Cambiar `corpusStatus` a `published`.
6. Sustituir la plantilla de preparación por contenido y CTA propios del país, manteniendo la
   ruta de `CountryRoute`.
7. Decidir `indexable` de forma independiente y añadir la ruta al sitemap solo cuando tenga
   contenido público real.
8. Actualizar el estado de esta documentación y ejecutar `npm run fast-check` dentro de
   `frontend/`.

Las páginas futuras no afirman que tengan jurisprudencia disponible: el mensaje se personaliza
con el nombre del país y deja explícito que su corpus todavía no existe.

## La invitación a contribuir

El proyecto es colaborativo y se nutre de la contribución de **expertos en fiscalidad y
tributación internacional** —abogados y asesores fiscales, académicos, documentalistas jurídicos,
traductores jurídicos, economistas, además de desarrolladores—, no solo de código. Las páginas sin
corpus son su punto de entrada: en lugar de un «próximamente» pasivo, piden lo que realmente falta.

**El registro es profesional a propósito.** El copy no dice que el corpus «lo pueda abrir
cualquiera»: dice que exige criterio jurídico-tributario, que es lo que de verdad limita el
proyecto a un solo país. `frontend/tests/CountryPage.test.tsx` fija el titular y **afirma en
negativo** que no reaparece la fórmula «lo puede abrir cualquiera», para que el copy no se degrade
con el tiempo.

Lo que sí se afirma del corpus español es que **su jurisprudencia se delimitó con criterio
jurídico-tributario** (selección de resoluciones, criterios del art. 9 LIRPF, doce categorías de
prueba). Lo que **no** se afirma es que su análisis esté ya revisado por especialistas: las
anotaciones de `knowledge/annotations/` están en `status: proposed`, pendientes de aprobación
humana, y el sitio advierte de que el análisis lo genera un modelo y puede contener errores.
Escribir «revisado por expertos» sería falso y contradiría ese aviso. La validación se enuncia como
**requisito para publicar**, no como hecho consumado.

`/colaborar` (`frontend/src/pages/ColaborarPage.tsx`) centraliza la invitación y es su **única
ruta indexable**. Esto es deliberado: actualmente **todas** las páginas de país sin corpus son
`noindex, follow` para no publicar una veintena de placeholders casi idénticos —`/espana`, que sí
tiene corpus, es indexable y está en el sitemap—, pero la implementación mantiene ambas
decisiones separadas para no convertir esa política actual en un invariante falso. Los
placeholders también son invisibles en búsquedas, así que sin una URL indexable nadie llegaría a
la invitación desde Google.
`/colaborar` tiene contenido propio (perfiles, invariantes, criterio de arranque), está en el
sitemap y `test/test_frontend_seo_assets.py` fija ambas cosas.

El recuento exacto no se escribe en prosa a propósito: la lista de rutas reservadas crece, y un
número a mano en varios documentos se queda desfasado en la primera ampliación. La fuente es
`countryRoutes.json`; el estado funcional se consulta en `corpusStatus` y la publicación SEO en
`indexable`.

Los dos canales son equivalentes: la issue de GitHub y `info@residenciafiscal.org`. Buena parte
del público objetivo —juristas— no tiene cuenta de GitHub, y crearla para escribir es fricción
suficiente para perderlos. `frontend/src/lib/contribution.ts` es la fuente única de ambos, de
`COLLABORATE_PATH` y de `EXPERT_PROFILES`, que comparten `/colaborar` y las páginas de país.

- El enlace lleva al formulario `aportar_pais.yml` con el título y el campo `pais` ya rellenados
  vía query params, así que quien llega desde `/chile` no tiene que explicar de qué país habla.
- La invitación es **abierta a cualquier jurisdicción**, no solo a los países con ruta. El
  texto no promete fecha ni da por hecho que el país vaya a publicarse.
- El segundo CTA apunta a `CONTRIBUTING.md`, donde está el detalle operativo y los invariantes
  (no reescribir el texto de una resolución, no subir documentos antes de resolver su
  reutilización, aislamiento entre corpus).
- La `description` de cada ruta pendiente dice lo mismo que la página. Son `indexable: false`, así
  que no entran en el sitemap ni permiten indexación (`noindex, follow`), pero sí se prerenderizan:
  la tarjeta social de `/peru` compartida en redes tiene que invitar a contribuir, no anunciar
  contenido que no existe.

Al publicar un país, esta sección de su página desaparece junto con la plantilla.
