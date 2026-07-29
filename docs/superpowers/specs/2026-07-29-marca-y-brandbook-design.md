# Marca y brandbook — Residencia Fiscal

> **Estado:** aprobado 2026-07-29 · spec de diseño previo a implementación.
> Referencias tomadas de `comunicador/docs/brand/brand-guidelines.md` (estructura,
> tabla de contraste verificada, comprobación determinista) y de
> `presupuestor/docs/marketing/BRAND.md` (mapa de assets y especificaciones por
> superficie).

## Problema

El proyecto tiene tokens de color desplegados en `frontend/src/index.css` y un
`favicon.svg` provisional con una «R», pero **no tiene marca documentada**: nadie —
persona o agente — puede producir una pieza on-brand sin abrir el CSS y adivinar el
criterio. No hay isotipo definido, ni lockup, ni imagen Open Graph, ni reglas de voz,
ni ningún gate que impida que la paleta derive.

## Objetivo

Un documento canónico (`docs/brand/brand-guidelines.md`) desde el cual cualquiera
pueda producir una pieza correcta, más los archivos de identidad y un gate automático
que evite que el documento y el código se separen.

**Fuera de alcance:** rediseñar la paleta (los tokens vigentes se documentan, no se
sustituyen), rediseñar componentes de la SPA, y auto-hospedar las fuentes.

---

## 1. Concepto de marca — «El expediente, legible»

Azul pizarra institucional sobre lienzo casi blanco. El ámbar aparece **solo donde hay
algo que verificar**: la cita, la fuente, el aviso. Consecuencia de diseño: *el color se
gana*. Una pantalla en reposo es casi monocroma.

El activo distintivo es **la cita**. Toda respuesta muestra el ROJ/ECLI de la
resolución en la que se apoya, en la misma unidad visual que el contenido generado —
no como pie opcional. Si no cabe, sobra otra cosa. Es el equivalente funcional del
semáforo editorial de Comunicador: el elemento que la marca no negocia.

---

## 2. Identidad gráfica

### Isotipo

Monograma «RF» sobre cuadrado `primary` (`#1e3a5f`), radio 14/64. La **R en blanco**,
la **F en ámbar**: el color separa las dos palabras del nombre en lugar de añadir un
elemento decorativo más. Sin sombras, sin degradados, sin recolorear.

Elegido entre seis propuestas (monograma con filete, monograma bicolor, anillo de los
183 días, anillo con monograma dentro, la frontera, la balanza). Se descartaron el
anillo y la frontera porque a 16 px pierden el elemento que las hace legibles, y la
balanza por ser el recurso más visto del sector.

**Las letras van convertidas a trazado.** Un SVG estático no puede depender de que
Space Grotesk esté instalada en el dispositivo que lo abre; con `<text>` el isotipo
caería a una fuente cualquiera del sistema. Si no se puede extraer el contorno real de
la fuente, se dibujan a mano con la misma métrica geométrica y se documenta.

### Ámbar del isotipo — token nuevo

El ámbar vigente `accent-500` (`#d97706`) sobre `primary` da **3.61:1**: a 16 px la F
se apelmaza contra el azul. Se añade un token:

```css
--color-accent-400: #f59e0b;   /* 5.36:1 sobre primary — ámbar sobre azul */
```

Reservado a **ámbar sobre superficie azul** (isotipo, y cualquier futura superficie
`primary`). No sustituye a `accent-500` ni a `accent-600` en superficies claras. Es un
token, no un HEX suelto: entra en la fuente única y en el gate.

### Wordmark y lockup

- **Wordmark:** `Residencia Fiscal`, Space Grotesk 600, en `foreground`. «Fiscal» en
  peso 500 y `muted-foreground` — la jerarquía del nombre la marca el peso, no el color
  de marca.
- **Lockup:** isotipo + wordmark a su derecha, alineados al centro vertical, separación
  igual a 0.36× el lado del isotipo.
- Isotipo y wordmark funcionan **cada uno solo**: el isotipo en favicon y avatar, el
  wordmark en correo y documentos. Las letras del isotipo nunca se dibujan dentro del
  texto del wordmark.
- **Espacio de respeto:** un margen igual a la altura de la «R» del wordmark por los
  cuatro lados.
- **Tamaño mínimo:** isotipo 16 px, lockup 120 px de ancho.

### Vetos gráficos

Nada de balanzas, martillos de juez, banderas, columnas clásicas, mascotas,
ilustraciones 3D ni iconografía de «robot». El producto vende trazabilidad documental,
no automatización simpática. Tampoco degradados ni sombras de color.

---

## 3. Color

La fuente única es `frontend/src/index.css`. El brandbook **explica y restringe** esos
tokens; no los duplica como sistema paralelo. Si cambia el CSS, se actualiza la página
en el mismo commit.

### Contraste verificado (2026-07-29)

Ratios WCAG calculados, no estimados. AA exige 4.5:1 en texto normal y 3:1 en texto
grande (≥18.66px bold o ≥24px) y componentes de interfaz.

| Par | Ratio | Uso permitido |
| --- | --- | --- |
| `foreground` sobre `background` | 17.85:1 | Libre |
| `foreground` sobre `secondary`/`muted` | 16.30:1 | Libre |
| `secondary-foreground` sobre `secondary` | 13.35:1 | Libre |
| `primary` sobre `background` | 11.50:1 | Libre |
| `primary-foreground` sobre `primary` | 10.99:1 | Libre |
| `primary` sobre `accent` | 11.09:1 | Libre |
| `accent-foreground` sobre `accent` | 8.75:1 | Patrón de bloque de aviso |
| `destructive` sobre blanco / blanco sobre `destructive` | 6.47:1 | Libre |
| `accent-400` sobre `primary` | 5.36:1 | Solo isotipo y superficies azules |
| `success` / `warning` / `accent-600` sobre blanco (y viceversa) | 5.02:1 | Libre, incluido texto de badge |
| `muted-foreground` sobre `background` | 4.76:1 | Texto secundario **solo sobre blanco**, sin bajar de 12 px |
| **`muted-foreground` sobre `muted`/`secondary`** | **4.34:1** | ❌ Falla AA |
| **`accent-500` (`#d97706`) sobre blanco** | **3.19:1** | ❌ Nunca lleva texto |

### Dos reglas que salen de la tabla

1. **`muted-foreground` no va sobre superficie teñida.** Los metadatos dentro de una
   tarjeta `muted` o `secondary` van en `secondary-foreground` (13.35:1). Esto se
   arregla con una regla, no cambiando el token: `muted-foreground` sobre blanco está
   bien y es el caso mayoritario.
2. **`accent-500` no lleva texto encima ni es texto.** Es un tono de superficie y de
   filete. Para texto ámbar sobre blanco, `accent-600` (5.02:1); para bloques de aviso,
   fondo `accent` con texto `accent-foreground` (8.75:1).

Paleta cerrada: no se introducen colores nuevos. Un matiz que haga falta sale de la
escala `primary` o de opacidades de los tokens existentes.

---

## 4. Tipografía

| Rol | Familia | Uso |
| --- | --- | --- |
| Titulares | `Space Grotesk` (500/600/700) | `h1`–`h4`, wordmark, cifras destacadas |
| Interfaz y texto | `Inter` (400/500/600/700) | Todo lo demás |
| **Evidencia** | `ui-monospace, monospace` | ROJ, ECLI, fechas de resolución, artículos citados, identificadores |

El rol de **evidencia** es nuevo y es deliberado: el monoespaciado marca lo que el
usuario puede ir a comprobar contra el texto original. Es un recurso de verificación,
no de decoración. Jerarquía por peso y tamaño, nunca por color.

**Deuda anotada:** las fuentes se cargan desde Google Fonts CDN (`index.html`), lo que
añade una petición bloqueante y un tercero en la ruta crítica. La CSP de `netlify.toml`
ya lo contempla (`fonts.googleapis.com`, `fonts.gstatic.com`). Auto-hospedarlas queda
como pendiente declarado, no se resuelve en este trabajo.

---

## 5. Composición

- **Radio:** `0.5rem` base; tarjetas y diálogos en `lg`, badges en píldora, isotipo
  14/64.
- **Bordes antes que sombras.** `1px` de `border` para separar; tarjetas hasta
  `shadow-xs`; `shadow-lg` reservado a flotantes (popover, diálogo, drawer, toast).
  Ninguna sombra de color.
- **Foco visible único:** todos los controles comparten `control-focus`. Las utilidades
  `control-*` se definen una sola vez en `index.css`; ningún primitivo redeclara su
  foco.
- **Movimiento sobrio:** el hover cambia tono (`primary` → `primary-800`), nunca escala
  ni engorda la sombra; la pulsación hunde el control (`control-press`).
- **Una acción principal por vista.** En el chat, la acción principal es enviar la
  consulta.
- **La cita es parte del componente.** Cualquier bloque que muestre contenido generado
  muestra la resolución en que se apoya dentro de la misma unidad visual.

---

## 6. Voz y mensaje

### Claim canónico

> **106 sentencias sobre residencia fiscal, con la cita siempre a la vista.**

### Tres promesas

1. **Corpus acotado y declarado.** 106 sentencias, Tribunal Supremo y Audiencia
   Nacional, 2015–2025. El tamaño y los límites del corpus se dicen, no se insinúan.
2. **Toda respuesta cita la resolución en que se apoya.** Sin cita no hay respuesta.
3. **Orientación documental verificable, no asesoramiento.** El destino de una consulta
   es el texto original de la sentencia.

### Distinción obligatoria

Elevada a regla de marca desde `frontend/public/llms.txt`: una respuesta distingue
siempre entre **criterio del tribunal**, **hechos probados** e **inferencia**. Tres
cosas distintas que suenan igual si se escriben mal.

### Vetos de lenguaje

«asesoramiento», «te asesoramos», «abogado virtual», «garantizamos», «revoluciona»,
«IA jurídica», cualquier promesa de resultado en un litigio, y —el más grave— citar
una sentencia que no esté en el corpus.

### Estado del motor

Mientras `chatEngineMode === 'stub'` en `frontend/src/lib/chat-engine.ts`, la interfaz
avisa de que el contenido es simulado. **Ese aviso es parte del contrato de marca, no
un parche**: la marca no promete lo que el motor todavía no hace. Cuando el modo pase a
`'live'`, el aviso se apaga solo.

---

## 7. Superficies

| Superficie | Reglas clave |
| --- | --- |
| Chat (`/`) | Lienzo claro, tarjetas con borde, una acción principal (enviar), citas visibles en cada respuesta, aviso de simulación mientras el motor sea stub |
| Favicon e icono de app | Isotipo tal cual, sin wordmark. Fuente: `frontend/public/favicon.svg` → `npm run favicon` |
| Open Graph | 1200×630. Fondo blanco, wordmark en `foreground`, claim en `muted-foreground`, filete `primary` arriba y la cifra del corpus como firma. Fuente: `frontend/og/og-image.html` → `npm run og` |
| Documentación y README | Mismo vocabulario canónico que la interfaz; los nombres técnicos van en código |
| Correo (futuro) | Texto primero, wordmark tipográfico en cabecera, sin plantillas decorativas |

**Dominio canónico:** `https://www.residenciafiscal.org` — el ápex redirige con 301
(`netlify.toml`). Las URL absolutas de las metaetiquetas usan la forma `www`.

---

## 8. Artefactos y reproducibilidad

Mismo enfoque que Comunicador, verificado disponible en esta máquina: **Chrome headless
+ Pillow**, sin añadir dependencias npm.

| Archivo | Rol |
| --- | --- |
| `frontend/public/favicon.svg` | **Fuente única** del isotipo. Lleva los HEX literales porque un SVG estático no lee `var()`; si cambia un token, cambia aquí en el mismo commit |
| `frontend/src/assets/logo.svg` | Lockup horizontal |
| `frontend/og/og-image.html` | **Fuente única** de la imagen OG; el render le inyecta los tokens leídos de `index.css` |
| `frontend/og/render-favicon.sh` | `npm run favicon` → `favicon.ico` (48/32/16) + `apple-touch-icon.png` (180 full-bleed) |
| `frontend/og/render.sh` | `npm run og` → `public/og-image.png` |

Los `.ico`, `.png` de apple-touch y la OG son **artefactos**: no se editan a mano ni se
sustituyen por versiones hechas aparte.

El `favicon.ico` de 16 px se genera desde una variante con el trazo de las letras
engrosado, igual que hace Comunicador con su «C»: a ese tamaño el monograma sin
engrosar pierde el contraforma.

---

## 9. Comprobación determinista

`frontend/tests/brand-tokens.test.ts`, dentro de `npm run fast-check` y del workflow
`.github/workflows/frontend.yml`. Cuatro reglas, las cuatro aprendidas en Comunicador:

1. **Contraste.** Los pares permitidos de la tabla se recalculan leyendo `index.css` y
   fallan si bajan de AA. Los dos pares que hoy no cumplen se comprueban al revés: el
   test afirma que **siguen por debajo de AA**, de modo que si alguien retoca el token y
   los arregla, el test se cae y obliga a actualizar la regla en lugar de dejarla
   caducada en el documento.

   Además, un chequeo textual sobre `src/`: ningún `className` combina en el **mismo
   atributo** `bg-muted`/`bg-secondary` con `text-muted-foreground`, ni usa
   `text-accent-500`. Es una comprobación literal, no de árbol renderizado: no detecta
   el caso en que el fondo teñido lo pone un componente padre. Esa limitación se asume;
   cubre el error frecuente, no todos.
2. **Ningún HEX literal fuera de la fuente única.** Excepciones declaradas y
   comprobadas: `public/favicon.svg`, `src/assets/logo.svg` y `og/og-image.html`.
3. **Nada de clases de escala sobre tokens planos.** Solo `primary` tiene escala
   `50…950`; `bg-warning-50` o `text-success-900` se renderizan transparentes sin
   avisar.
4. **Toda clase `control-*` referenciada existe en `index.css`.** Una clase sin
   definición deja el control sin foco o sin borde y nada avisa.

---

## 10. Entregables

| Archivo | Acción |
| --- | --- |
| `docs/brand/brand-guidelines.md` | Nuevo — el brandbook canónico |
| `frontend/public/favicon.svg` | Reemplaza el provisional de la «R» |
| `frontend/src/assets/logo.svg` | Nuevo — lockup |
| `frontend/og/og-image.html` | Nuevo — fuente de la OG |
| `frontend/og/render.sh`, `frontend/og/render-favicon.sh` | Nuevos — render determinista |
| `frontend/package.json` | Scripts `og` y `favicon` |
| `frontend/public/favicon.ico`, `apple-touch-icon.png`, `og-image.png` | Artefactos generados |
| `frontend/index.html` | Metaetiquetas OG/Twitter (hoy no hay ninguna) + enlaces a los iconos |
| `frontend/src/index.css` | Token `--color-accent-400` |
| `frontend/tests/brand-tokens.test.ts` | Nuevo — el gate |
| `CLAUDE.md` | Sección de marca apuntando al brandbook |

## 11. Riesgos y decisiones abiertas

- **Contorno de las letras.** Si no hay acceso a la TTF de Space Grotesk para extraer
  los glifos, se dibujan las formas a mano. En ese caso el isotipo no es tipográficamente
  idéntico al wordmark; se acepta y se documenta.
- **Modo oscuro:** no existe hoy. Si se añade, la tabla de contraste se recalcula sobre
  el nuevo fondo.
- **Fuentes en CDN:** pendiente declarado, ver §4.
- **Test de contraste y `frontend.yml`:** el workflow pasa hoy `--passWithNoTests` a
  vitest; ya hay suites, así que el gate es real. Sin cambios necesarios.
