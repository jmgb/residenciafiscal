# Páginas por país

## Estado actual

El frontend ya tiene una entrada por país para que la navegación y la arquitectura puedan
crecer sin rehacer el menú:

- `/` redirige a `/espana`.
- `/espana` conserva literalmente la experiencia que antes vivía en la home: el chat y las
  sugerencias de preguntas. El aviso depende del selector: contenido simulado en `stub` e
  investigación experimental en `live`.
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

Y su propia metadata de buscador, que ya no se compone en el código:

- `title`: el título completo, tal cual sale en la pestaña y en el resultado de búsqueda. Lo leen
  `CountryPage` (con `exactTitle`) y `scripts/prerender.mjs`, para que el bot y la SPA no puedan
  discrepar.
- `description`: la meta description, distinta en cada país.
- `sitemap`: `changefreq` y `priority` propios. `/espana` cambia con el corpus; una jurisdicción
  sin corpus publica un convenio que se mueve muy de tarde en tarde.
- `treatyBoeId`: identificador del BOE del convenio de doble imposición entre España y ese país,
  o `null` si no hay convenio en vigor. Ver la sección siguiente.

## El convenio de doble imposición con España

Una página de país sin corpus tenía hasta ahora un solo contenido: la invitación a contribuir.
Eso la hacía inútil para quien llega buscando su situación entre dos países, y por eso estaban
en `noindex`. Lo que sí puede publicar hoy, verificado y sin criterio jurídico propio, es el
**convenio de doble imposición entre España y esa jurisdicción**: es norma española del BOE, ya
versionada en `normativa/es/` y publicada artículo a artículo en
`knowledge/normativa/es/preceptos/`.

`treatyBoeId` es esa declaración, y solo eso: un identificador del BOE. Todo lo demás —título
oficial de la norma, artículo de residencia, redacción vigente, sentencias del corpus que lo
aplican, texto literal y enlace oficial— lo resuelve `TaxTreaty.tsx` contra el corpus normativo,
así que no hay una segunda copia del dato que pueda desincronizarse.

Tres límites, todos en el copy de la página:

- El convenio resuelve **de qué Estado es residente** quien podría serlo de los dos. No describe
  la ley interna del otro país, y la página no debe insinuar que sí.
- No sustituye al corpus: la página sigue diciendo que no hay jurisprudencia de ese país.
- `null` significa **no hay convenio en vigor**, comprobado contra la
  [relación oficial de la AEAT](https://sede.agenciatributaria.gob.es/Sede/normativa-criterios-interpretativos/fiscalidad-internacional/convenios-doble-imposicion-firmados-espana.html),
  y la página lo dice explícitamente. Hoy son Guatemala, Haití, Honduras, Nicaragua y Perú.

`tests/test_country_tax_treaties.py` ata cada `treatyBoeId` al corpus: comprueba que existe, que
el título oficial de la norma nombra a ese país —un identificador equivocado publicaría el
convenio de otra jurisdicción con el nombre correcto encima—, que no está derogado y que el
artículo publicado es el que resuelve la doble residencia.

`legalReferences` es distinto y no se mezcla con esto: describe el **derecho del propio país** y
exige validación de un especialista de allí. Es una lista porque no todas las jurisdicciones
concentran la residencia en un único artículo. Cada referencia conserva:

- `kind`: `domestic-residence` o `tax-treaty`;
- `shortCitation`: texto compacto y verificable para la interfaz;
- `title`: título oficial de la norma;
- `officialUrl`: enlace a la fuente pública oficial;
- `reviewedAt`: fecha ISO (`YYYY-MM-DD`) en la que se comprobaron editorialmente la cita, el
  título y el enlace contra esa fuente.

La primera referencia es la principal y alimenta el subtítulo compacto de una jurisdicción
publicada. No se incorporan equivalencias obtenidas de blogs, memoria o búsquedas automáticas:
las valida un especialista de la jurisdicción. Un país `pending` muestra siempre `Sin corpus`,
aunque ya tenga referencias documentadas, para no confundir normativa localizada con
jurisprudencia publicada.

Las referencias de la jurisdicción del chat se muestran también en su bienvenida bajo
`Marco jurídico`, enlazadas a la fuente oficial. `reviewedAt` no significa que la norma sea
aplicable a cualquier ejercicio ni sustituye el control de versiones del corpus normativo:
registra la última comprobación editorial de esos metadatos. No se actualiza automáticamente en
cada build; cambia solo después de repetir esa comprobación.

## Cómo activar un país

Cuando exista la documentación nacional revisada y trazable:

1. Añadir el corpus y su pipeline de recuperación aislados del corpus español.
2. Registrar el corpus en el motor y mantener el contrato `ChatRequestContext` para que no pueda
   consultar por accidente documentos de otro país.
3. Añadir tests de aislamiento: una consulta de México no puede devolver una cita de España.
4. Registrar al menos una referencia jurídica oficial validada en `legalReferences`, dejando
   primero la que deba identificar el marco nacional en superficies compactas y fechando su
   comprobación en `reviewedAt`.
5. Cambiar `corpusStatus` a `published`.
6. Sustituir la plantilla de preparación por contenido y CTA propios del país, manteniendo la
   ruta de `CountryRoute`.
7. Revisar `title` y `description`: dejan de hablar del convenio y pasan a hablar del corpus.
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

`/colaborar` (`frontend/src/pages/ColaborarPage.tsx`) centraliza la invitación, tiene contenido
propio (perfiles, invariantes, criterio de arranque) y está en el sitemap.

**Las páginas de país ya no son `noindex`.** Lo fueron mientras su único contenido era la
invitación: veintiocho placeholders casi idénticos no le sirven a nadie en un buscador. Dejaron
de serlo cuando cada una pasó a publicar el convenio de doble imposición con España, con su
artículo de residencia, su texto literal y su enlace al BOE: contenido distinto en cada ruta,
verificable y útil para quien busca su situación entre dos países. `corpusStatus` e `indexable`
siguen siendo decisiones separadas, y hoy las 29 rutas están en el sitemap.

Lo que **no** cambia con la indexación: la página sigue diciendo que no hay jurisprudencia de ese
país, y el convenio se presenta como norma española que resuelve la doble residencia, no como el
derecho interno de esa jurisdicción.

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
- La `description` de cada ruta pendiente dice lo mismo que la página: el convenio con España y
  que su jurisprudencia todavía no existe. Todas se prerenderizan, así que la tarjeta social de
  `/peru` compartida en redes anuncia eso y no contenido que no tenemos.

Al publicar un país, esta sección de su página desaparece junto con la plantilla.
