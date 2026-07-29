# Brandbook — Residencia Fiscal

> **Documento canónico de marca.** Desde aquí cualquiera —persona o agente— debe poder
> producir una pieza on-brand sin abrir el CSS a adivinar el criterio.
> Spec de origen: [`docs/superpowers/specs/2026-07-29-marca-y-brandbook-design.md`](../superpowers/specs/2026-07-29-marca-y-brandbook-design.md).
> Narrativa completa: [`docs/brand/manifiesto.md`](manifiesto.md).
> Gate automático: `frontend/tests/brand-tokens.test.ts` (dentro de `npm run fast-check`).

## 1. La marca en dos frases

**Narrativa** («Vive donde elijas»): un movimiento contra la asimetría de información —
democratizar el conocimiento jurisprudencial con el que trabajan los mejores asesores
fiscales, siempre dentro de la ley. **Ejecución visual** («El expediente, legible»):
rigor documental; el color se gana, la cita no se negocia. La tesis que las une:
*la libertad se ejerce mejor documentado*.

## 2. Identidad gráfica

### Isotipo

Monograma «RF» sobre cuadrado `primary` (`#1e3a5f`), radio 14/64. La **R en
`primary-foreground`** (`#f8fafc`), la **F en `accent-400`** (`#f59e0b`): el color separa
las dos palabras del nombre. Sin sombras, sin degradados, sin recolorear.

- **Fuente única:** `frontend/public/favicon.svg`. Letras de Space Grotesk 600
  **convertidas a trazado** (extraídas de la TTF con fontTools) — un SVG estático no
  puede depender de la fuente instalada.
- Los HEX literales del SVG son deliberados (un SVG estático no lee `var()`); el gate
  comprueba que coincidan con tokens de `index.css`.
- Tamaño mínimo: 16 px. El `favicon.ico` de 16 px se genera desde una variante con el
  trazo engrosado (lo hace `npm run favicon`; no existe como archivo aparte).

### Wordmark y lockup

- **Wordmark:** `Residencia Fiscal`, Space Grotesk 600 en `foreground`; «Fiscal» en
  peso 500 y `muted-foreground`. La jerarquía la marca el peso, no el color de marca.
- **Lockup** (`frontend/src/assets/logo.svg`): isotipo + wordmark a su derecha,
  separación 0.36× el lado del isotipo, alineados al centro vertical.
- Isotipo y wordmark funcionan cada uno solo: isotipo en favicon/avatar, wordmark en
  correo/documentos. Tamaño mínimo del lockup: 120 px de ancho.
- **Espacio de respeto:** un margen igual a la altura de la «R» por los cuatro lados.

### Vetos gráficos

Nada de balanzas, martillos de juez, banderas, columnas clásicas, mascotas,
ilustraciones 3D ni iconografía de «robot». Tampoco degradados ni sombras de color.
El producto vende trazabilidad documental, no automatización simpática.

## 3. Color

La fuente única es `frontend/src/index.css`. Este documento explica y restringe esos
tokens; si cambia el CSS, se actualiza esta página en el mismo commit (el gate recalcula
los ratios y avisa si la tabla caduca).

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

Dos reglas que salen de la tabla:

1. **`muted-foreground` no va sobre superficie teñida.** Los metadatos dentro de una
   tarjeta `muted`/`secondary` van en `secondary-foreground` (13.35:1).
2. **`accent-500` no lleva texto encima ni es texto.** Para texto ámbar sobre blanco,
   `accent-600`; para bloques de aviso, fondo `accent` + texto `accent-foreground`.

`accent-400` está **reservado a ámbar sobre superficie `primary`** (isotipo). Paleta
cerrada: un matiz nuevo sale de la escala `primary` o de opacidades, nunca de un color
nuevo.

## 4. Tipografía

| Rol | Familia | Uso |
| --- | --- | --- |
| Titulares | `Space Grotesk` (500/600/700) | `h1`–`h4`, wordmark, cifras destacadas |
| Interfaz y texto | `Inter` (400/500/600/700) | Todo lo demás |
| **Evidencia** | `ui-monospace, monospace` | ROJ, ECLI, fechas de resolución, artículos citados, identificadores |

El monoespaciado marca **lo que el usuario puede ir a comprobar** contra el texto
original. Es un recurso de verificación, no de decoración. Jerarquía por peso y tamaño,
nunca por color.

## 5. Composición

- **Radio:** `0.5rem` base; tarjetas y diálogos en `lg`, badges en píldora, isotipo 14/64.
- **Bordes antes que sombras:** `1px` de `border` para separar; `shadow-lg` solo en
  flotantes. Ninguna sombra de color.
- **Foco visible único:** todos los controles comparten `control-focus` (definido una
  sola vez en `index.css`).
- **Movimiento sobrio:** hover cambia tono, nunca escala; la pulsación hunde
  (`control-press`).
- **Una acción principal por vista.** En el chat: enviar la consulta.
- **La cita es parte del componente:** todo bloque con contenido generado muestra la
  resolución en que se apoya dentro de la misma unidad visual.

## 6. Voz y mensaje

- **Claim canónico:** «Reside donde mejor te traten. Decide con las sentencias en la
  mano.» La primera frase nunca aparece sin la segunda.
- **Claim funcional** (README, docs, metadescripciones): «106 sentencias sobre
  residencia fiscal, con la cita siempre a la vista.»
- **Manifiesto:** tres versiones canónicas y reglas de uso en
  [`manifiesto.md`](manifiesto.md). Se usa una versión entera o no se usa.
- **Distinción obligatoria:** toda respuesta separa criterio del tribunal, hechos
  probados e inferencia.
- **Vetos:** «asesoramiento», «abogado virtual», «garantizamos», «IA jurídica»,
  promesas de resultado; y todo lo que suene a ocultación: «paga cero», «Hacienda no
  se enterará», «escapa», «paraíso fiscal» como reclamo. La marca democratiza la
  *información* de los mejores asesores; nunca promete el *servicio*. Habla de
  *elegir*, no de *huir*. El veto más grave: citar una sentencia que no esté en el
  corpus.
- Mientras el motor sea stub, el aviso de contenido simulado **es parte del contrato
  de marca**, no un parche.

## 7. Superficies y artefactos

| Superficie | Fuente única | Artefacto (`no editar a mano`) |
| --- | --- | --- |
| Favicon / avatar | `frontend/public/favicon.svg` | `favicon.ico`, `apple-touch-icon.png` → `npm run favicon` |
| Lockup | `frontend/src/assets/logo.svg` | — |
| Open Graph | `frontend/og/og-image.html` (placeholders `__TOKEN__`) | `public/og-image.png` → `npm run og` |
| Metaetiquetas | `frontend/index.html` | — |

Si cambia un token de `index.css`, se regeneran los artefactos en el mismo commit
(`npm run og && npm run favicon`). Los renders usan Chrome headless + Pillow, sin
dependencias npm nuevas.

## 8. Gate automático

`frontend/tests/brand-tokens.test.ts`, dentro de `npm run fast-check` y del workflow
`frontend.yml`:

1. Recalcula los ratios de la tabla de contraste desde `index.css` (los pares
   prohibidos se afirman al revés: si alguien los arregla, el test obliga a
   actualizar la regla).
2. Ningún HEX literal en `src/` fuera de `index.css`; las excepciones declaradas
   (favicon, logo) deben usar HEX que existan como token.
3. Nada de clases de escala sobre tokens planos (solo `primary` tiene escala 50…950).
4. Toda clase `control-*` referenciada existe en `index.css`.

La comprobación de clases es textual, no de árbol renderizado: cubre el error
frecuente, no todos.
