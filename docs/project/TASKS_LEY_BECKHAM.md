# TASKS — Proyecto análogo: régimen de impatriados («Ley Beckham»)

Plan para duplicar este proyecto y adaptarlo al **régimen especial de
trabajadores desplazados a territorio español** (art. 93 LIRPF), conocido
popularmente como *Ley Beckham*: dominio propio, repositorio propio, corpus
propio y el mismo contrato de verificabilidad que rige aquí.

> **Estado:** propuesta. Ninguna tarea está ejecutada. El orden importa: las
> fases 0 y 2 condicionan todo lo demás, y la fase 3 no arranca sin fuente
> reutilizable confirmada.
>
> **Aviso (3 de agosto de 2026):** una valoración posterior
> ([`LEY_BECKHAM_VALORACION.md`](../product/LEY_BECKHAM_VALORACION.md))
> recomienda la
> opción contraria — integrar el régimen como sección de residenciafiscal.org
> bajo `/espana`, sin dominio ni repositorio nuevos. La decisión está pendiente
> del propietario; el issue con la recomendación y sus pasos está en
> [`TASKS.md`](TASKS.md), sección «Producto y arquitectura». **No ejecutar las
> fases 0 y 1 de este plan sin esa decisión.** Las fases de contenido (2–4)
> siguen siendo válidas en ambos escenarios.

## 1. Objetivo y no-objetivos

**Objetivo.** Un corpus verificable y un chat de investigación sobre el régimen
de impatriados: qué requisitos exige, cómo los ha interpretado la
Administración y los tribunales, qué pruebas se aceptan y qué consecuencias
tiene perder o renunciar al régimen. Cada afirmación, respaldada por fuente,
página y extracto literal.

**No-objetivos** (idénticos a los de este repositorio, y por las mismas razones):

- No es un asesor fiscal ni predice el resultado del caso de quien pregunta.
- No reescribe, corrige ni parafrasea el texto de una fuente oficial. Las citas
  salen de subcadenas exactas del documento original.
- No se publica análisis como «revisado por expertos» mientras no lo esté.

## 2. Lo que hereda y lo que no

Hereda tal cual (es infraestructura, no contenido jurídico):

- [ ] Pipeline verbatim con `pypdf`, hashes y páginas físicas.
- [ ] Verificación de citas determinista, sin LLM, con umbral y manifiesto.
- [ ] Gateway de modelos (`neutral-llm-gateway`) y política de coste visible.
- [ ] SPA React + Netlify Function del chat, protocolo SSE y persistencia local.
- [ ] **Caché y detección de versión desplegada**, ya resuelto aquí:
      [`docs/operations/CACHE_AND_RELEASES.md`](../operations/CACHE_AND_RELEASES.md).
      Se copia entero, incluidas las reglas de 404 previas al fallback.
- [ ] Gates de CI (ruff/mypy/pytest, biome/tsc/vitest/build) y marca con gate
      automático de contraste.

**No hereda** (es contenido, y copiarlo sería falsear el corpus):

- El catálogo `VALID_RESULTADO_FINAL` y los criterios del art. 9 LIRPF: aquí la
  materia es otra.
- El corpus de sentencias y el normativo de residencia.
- El copy, la marca y el manifiesto.

## 3. Fase 0 — Dominio, nombre y marca

**Riesgo a resolver antes de comprar nada:** *Beckham* es el apellido de una
persona real y una marca registrada en varias clases. «Ley Beckham» es un apodo
periodístico del régimen, no su nombre legal. Usarlo como **nombre de dominio o
marca del producto** es un riesgo distinto —y mayor— que usarlo como término
descriptivo dentro del contenido.

- [ ] Consultar con un abogado de marcas si el dominio puede contener
      «beckham». Hasta que haya respuesta, trabajar con la hipótesis de que
      **no**.
- [ ] Elegir dominio descriptivo (línea recomendada): sobre *impatriados* o
      *régimen de impatriados*, con `.org` coherente con el proyecto hermano.
      Reservar la variante `.es` si está libre.
- [ ] Comprobar disponibilidad y precio de renovación (no solo el primer año).
- [ ] Comprobar que el nombre no colisiona con despachos o productos ya
      existentes en el sector.
- [ ] **Comprar el dominio** con el mismo registrador que el actual, con
      renovación automática y privacidad de WHOIS activada.
- [ ] Delegar DNS a Cloudflare, replicando la configuración documentada en
      [`docs/operations/CLOUDFLARE.md`](../operations/CLOUDFLARE.md).
- [ ] Reservar los perfiles sociales mínimos y el correo de contacto del
      proyecto (nunca el personal, como aquí).
- [ ] Decidir la relación entre los dos sitios: enlace mutuo, marca compartida
      o independientes. Afecta a SEO y a la arquitectura de contenidos.

> «Ley Beckham» **sí** se usa en títulos, `description` y cuerpo del contenido:
> es como busca la gente. La distinción es dominio/marca frente a término
> descriptivo, y conviene dejarla escrita en el brandbook del nuevo proyecto.

## 4. Fase 1 — Duplicación técnica

- [ ] Crear repositorio nuevo. **No es un fork de GitHub**: se copia el árbol y
      se inicia historia limpia, para que el corpus español de residencia no
      viaje en el historial.
- [ ] Purgar `sentencias/`, `normativa/`, `knowledge/`, `output/` y los
      documentos de fases E0/F0.x, que son bitácora de este corpus.
- [ ] Renombrar paquete, dominio, títulos, `llms.txt`, `robots.txt`, `sitemap`,
      OG y favicon.
- [ ] Vaciar `countryRoutes.json`: el eje del proyecto nuevo **no es el país**,
      es el régimen. Decidir si se conserva la arquitectura multi-jurisdicción
      (hay regímenes de impatriados en Portugal, Italia, Países Bajos…) o se
      simplifica. Recomendado: conservarla, es donde crece el proyecto.
- [ ] Rehacer `src/config.py` con los catálogos de la nueva materia (ver fase 4).
- [ ] Dejar la suite en verde con el corpus vacío antes de cargar nada.

**Gate 1:** `make fast-check` y `npm run fast-check` verdes en un repositorio
sin un solo documento jurídico.

## 5. Fase 2 — Corpus normativo

Mismo pipeline que aquí: XML del BOE, un Markdown **por precepto**, sin LLM y
con test de identidad literal. Sin normalización NFKC.

Preceptos candidatos (**verificar uno a uno contra el BOE antes de publicarlos;
no dar por buena esta lista de memoria**):

- [ ] Art. 93 LIRPF — régimen especial de trabajadores desplazados.
- [ ] Desarrollo reglamentario del régimen en el RIRPF (opción, renuncia,
      exclusión y contenido de la declaración).
- [ ] Ley 28/2022 (de startups), que modificó el régimen: ampliación de
      supuestos y reducción de los periodos de no residencia previa exigidos.
- [ ] Órdenes de los modelos de opción/renuncia/exclusión y de declaración.
- [ ] Preceptos conexos: art. 9 LIRPF (residencia, que sigue siendo la puerta),
      IRNR en lo aplicable, y art. 4 de los CDI para el conflicto de residencia.
- [ ] Redacciones anteriores vigentes para los ejercicios que el corpus
      enjuicie, rotuladas como tales igual que aquí se hace con las derogadas.

**Gate 2:** cada párrafo publicado es idéntico al del XML de origen, verificado
por mutación, y cada precepto declara su vigencia por ejercicio.

## 6. Fase 3 — Fuentes: jurisprudencia **y doctrina administrativa**

Aquí está la diferencia estructural más importante con este proyecto. En
residencia fiscal manda la jurisprudencia. En el régimen de impatriados, buena
parte de la interpretación viva está en **consultas vinculantes de la DGT** y en
**resoluciones del TEAC**, con menos volumen de sentencias.

- [ ] Confirmar fuentes y **condiciones de reutilización de cada una**: CENDOJ
      para sentencias, la base de consultas de la DGT y DYCTEA para el TEAC. Sin
      condiciones claras, esa fuente no entra.
- [ ] Escribir el `AVISO_LEGAL.md` e inventario `readme.txt` de cada corpus de
      origen, como en `sentencias/` y `normativa/`.
- [ ] Definir la **jerarquía de autoridad** y hacerla explícita en la UI: TS >
      AN/TSJ > TEAC > DGT. Una consulta vinculante vincula a la Administración,
      no al juez, y el producto no puede presentarlas como equivalentes.
- [ ] Delimitar el corpus con criterio tributario, no por búsqueda de texto:
      qué cuestiones decide realmente cada documento.
- [ ] Congelar un holdout independiente **antes** de ajustar recuperación.

**Gate 3:** una fuente procesada extremo a extremo con citas verificadas, luego
cinco, y solo entonces el resto. Idéntico escalonado 1 → 5 → N que aquí.

## 7. Fase 4 — Modelo de datos

- [ ] Sustituir el catálogo de resultados por el que pide esta materia:
      concesión, denegación, pérdida sobrevenida, exclusión, renuncia,
      regularización, inadmisión.
- [ ] Modelar los **requisitos** como cuestiones jurídicas de primera clase: no
      residencia previa, causa del desplazamiento, existencia de relación
      laboral o de administrador, plazo de la opción, no obtención de rentas por
      establecimiento permanente, extensión a familiares.
- [ ] Añadir al esquema el **tipo de fuente** (sentencia | resolución TEAC |
      consulta vinculante) y su fuerza vinculante. Es un campo nuevo respecto a
      `residenciafiscal-case/3`.
- [ ] Modelar el **ejercicio aplicable**: el régimen cambió con la Ley 28/2022 y
      mezclar redacciones es el error más caro que puede cometer este producto.
- [ ] Anclajes literales por proposición, como en la fase C/D de aquí.

**Gate 4:** evaluación ejecutable de preguntas reales sobre la muestra fija,
con `preguntar` y `abstenerse` entre las conductas válidas.

## 8. Fase 5 — Chat

- [ ] Reutilizar la Function y el protocolo SSE sin cambios estructurales.
- [ ] Reescribir el prompt y la rúbrica: la materia y el caso de uso son otros.
      La rúbrica se congela **antes** de medir, como se aprendió en F0.3.
- [ ] Mantener coste, tokens, modelo efectivo y medición visibles por respuesta.
- [ ] Aviso explícito y no negociable: el régimen se solicita en plazo y una
      respuesta del chat no sustituye asesoramiento. El coste de equivocarse
      aquí lo paga el usuario en cuota.
- [ ] Revisión jurídica ciega por un especialista en impatriados antes de abrir
      el chat al público, con el mismo protocolo X/Y.

## 9. Fase 6 — Frontend, marca y SEO

- [ ] Brandbook propio con gate de contraste (se hereda el mecanismo, no los
      tokens).
- [ ] Páginas estáticas prerenderizadas: manifiesto, metodología, fuentes,
      colaborar, privacidad.
- [ ] SEO sobre las búsquedas reales («ley beckham requisitos», «régimen de
      impatriados 2026», «modelo 149»), respetando la separación entre término
      descriptivo y marca de la fase 0.
- [ ] `llms.txt` describiendo el corpus y sus límites.

## 10. Fase 7 — Despliegue y operación

- [ ] Netlify con `base`, `publish` y el `ignore` de build por rutas.
- [ ] **Copiar íntegra la política de caché y versionado** de
      [`CACHE_AND_RELEASES.md`](../operations/CACHE_AND_RELEASES.md): reglas de
      404 antes del fallback, cabeceras por ruta real, `/version.json` con
      `no-store` y guardián de versión en el shell. Es trabajo ya pagado.
- [ ] Sentry, GA4/PostHog y UptimeRobot con dos monitores de palabra clave (uno
      sobre la home y otro sobre el corpus JSON, por el fallback SPA).
- [ ] Backups y presupuesto del chat con tope duro antes de abrir el gasto.

## 11. Fase 8 — Legal

- [ ] Aviso legal, privacidad y cookies del dominio nuevo.
- [ ] Licencia MIT para código y documentación, con los corpus de fuente
      excluidos y sus condiciones propias declaradas.
- [ ] Declarar que el análisis lo genera un modelo y su estado de revisión.
- [ ] Contacto por canales del proyecto, nunca personales.

## 12. Riesgos y decisiones abiertas

| Riesgo | Mitigación |
|---|---|
| Uso de «Beckham» en dominio o marca | Fase 0 con abogado; por defecto, dominio descriptivo |
| Condiciones de reutilización de DGT/TEAC | Verificar antes de descargar nada; sin condiciones claras, fuera |
| Mezclar redacciones pre y post Ley 28/2022 | Ejercicio aplicable en el esquema y en la UI, desde el primer caso |
| Que el producto se lea como asesoramiento | Aviso, conducta `abstenerse` y revisión jurídica previa a abrir |
| Duplicar dos bases de código que divergen | Extraer lo genérico solo cuando **dos** proyectos lo necesiten, como con el gateway |

**Decisiones abiertas:** un repositorio o dos; marca independiente o familia;
si el eje multi-jurisdicción se conserva desde el día uno; y si el chat arranca
con corpus mínimo o espera a la muestra de cinco verificada.
