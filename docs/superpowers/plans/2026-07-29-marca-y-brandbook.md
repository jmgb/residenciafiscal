# Marca y brandbook — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dejar la marca de Residencia Fiscal documentada, dibujada y protegida por un gate automático: brandbook canónico, isotipo y lockup generados de forma reproducible, artefactos (favicon, apple-touch, Open Graph) y un test que impide que el documento y el código se separen.

**Architecture:** Los SVG de identidad **se generan** desde Space Grotesk con un script Python (`frontend/brand/build-identity.py`) y **se commitean**: el trazado de las letras no puede depender de que la fuente esté instalada en el dispositivo que abre el SVG. Los binarios (`.ico`, `apple-touch-icon.png`, `og-image.png`) son artefactos de dos scripts de Chrome headless + Pillow, copiando el enfoque ya probado en `comunicador/frontend/og/`. Ninguna dependencia npm nueva. El brandbook vive en `docs/brand/brand-guidelines.md` y **explica y restringe** los tokens de `frontend/src/index.css`, que sigue siendo la fuente única de color; `frontend/tests/brand-tokens.test.ts` es lo que impide que esa relación se pudra.

**Tech Stack:** Python 3 + fontTools + Pillow (todos ya disponibles en la máquina), Chrome headless (`/usr/bin/google-chrome`), Vitest 3, Tailwind CSS 4, Biome 2.

**Spec:** [`docs/superpowers/specs/2026-07-29-marca-y-brandbook-design.md`](../specs/2026-07-29-marca-y-brandbook-design.md)

---

## Revisión 2026-07-29 — trabajo concurrente

Mientras se escribía este plan, otra sesión ejecutó parte de él a mano sobre `main`.
Comprobado en el árbol de trabajo:

- **Task 1 (manifiesto): hecha y commiteada** en `47304d9`.
- **Task 2, mitad del token: hecha.** `--color-accent-400: #f59e0b` ya está en
  `src/index.css` con su comentario y su ratio. Falta el test.
- **Task 4, los dos SVG principales: hechos a mano.** `public/favicon.svg` y
  `src/assets/logo.svg` existen, con las letras trazadas desde **Space Grotesk 600**
  (verificado: el `d` de la «R» es byte a byte idéntico a la salida de fontTools con el
  peso 600) y la R en `primary-foreground` `#f8fafc` en vez de blanco puro — mejor
  tokenizado que lo que proponía este plan.

**Decisión: no se rehacen.** Su isotipo y su lockup son correctos y regenerarlos solo
produciría un conflicto con trabajo en vuelo. Las tareas se renumeran como **R1…R8** y
se ajustan así:

| Original | Nuevo | Cambio |
| --- | --- | --- |
| Task 1 | — | Ya hecha, se elimina |
| Task 2 | **R1** | Solo el test; el token ya está |
| Task 3 | **R1** | Se fusiona: un solo gate con las cuatro reglas |
| Task 4 | **R2** | El generador pasa a **peso 600** y produce **solo las tres variantes que faltan** (`iso-16`, `iso-fullbleed`, `logo-inverse`). No sobrescribe `favicon.svg` ni `logo.svg` |
| Task 5–9 | **R3–R7** | Sin cambios de fondo |
| Task 10 | **R8** | Sin cambios |

**Deuda que esto deja abierta, declarada:** `favicon.svg` y `logo.svg` quedan mantenidos
a mano mientras el generador cubre solo las variantes derivadas. Unificar los cinco bajo
`build-identity.py` es un follow-up para cuando el trabajo concurrente haya aterrizado;
hasta entonces, tocar el isotipo obliga a editar dos sitios. Está anotado en los
Pendientes del brandbook (R6).

**Regla de convivencia para todas las tareas:** cada commit lista sus rutas una a una.
Nunca `git add -A` ni `git add frontend/src`. Si el gate de R1 señala código de la otra
sesión, se reporta — no se edita.

---

## Desviaciones del spec (decididas al verificar, no al escribir)

Tres cosas del spec no sobreviven al contacto con la realidad. Se corrigen aquí y el brandbook (Task 9) documenta la versión corregida:

1. ~~**§8 dice que el `.ico` de 16 px sale «de una variante con el trazo de las letras engrosado, igual que Comunicador».** No aplica: la «C» de Comunicador es un `stroke` y se engorda con un `sed` sobre `stroke-width`; nuestro monograma son **contornos rellenos**, que no tienen `stroke-width` que tocar.~~

   **Corregido 2026-07-29 — esta desviación era falsa.** Un contorno relleno sí se puede
   engrosar: basta **añadirle** un `stroke` del mismo color que el `fill`, que expande la
   silueta hacia fuera. Es lo que hace `og/render-favicon.sh` de la otra sesión
   (`stroke="#f8fafc" stroke-width="28"`), y funciona. Lo que no aplicaba era el `sed`
   *literal* de Comunicador, que edita un `stroke-width` ya existente. Generalicé de un
   caso a una imposibilidad, y no lo era. La solución en vigor es la del stroke añadido;
   la variante de cap 38 que proponía este plan queda descartada por innecesaria.
2. **§8 y §10 sitúan las herramientas en `frontend/og/`.** El directorio contiene favicon, lockup y OG, así que se llama **`frontend/brand/`**. `og/` describiría un tercio de su contenido.
3. **§7 pide el claim canónico en `muted-foreground` en la imagen OG.** El claim es el texto principal de la pieza y en gris al 4.76:1 a 44 px queda lavado. Va en **`foreground`**; `muted-foreground` se reserva a la firma (`106 sentencias · …`), que es donde el spec quería la sobriedad.

Una adición sobre el spec: **`logo-inverse.svg`**, el lockup para fondo `primary`. Sin él, la marca no puede ponerse sobre su propio azul (cabecera, OG, correo) — y el isotipo con caja azul sobre fondo azul desaparece. Cuesta cero: mismo generador, mismos trazados.

---

## Estructura de archivos

| Archivo | Responsabilidad |
| --- | --- |
| `docs/brand/manifiesto.md` | **Ya escrito**, sin commitear. Narrativa canónica |
| `docs/brand/brand-guidelines.md` | Brandbook: color, tipografía, logo, composición, voz, superficies, QA |
| `frontend/brand/build-identity.py` | Genera los cinco SVG desde Space Grotesk. Único sitio donde se decide la geometría del monograma |
| `frontend/brand/render-favicon.sh` | SVG → `favicon.ico` (48/32/16) + `apple-touch-icon.png` (180) |
| `frontend/brand/og-image.html` | Fuente de la imagen Open Graph. Recibe los tokens inyectados desde `index.css` |
| `frontend/brand/render.sh` | `og-image.html` → `public/og-image.png` (1200×630) |
| `frontend/public/favicon.svg` | Isotipo. Generado y commiteado; lo consumen `index.html` y los renders |
| `frontend/src/assets/logo.svg` · `logo-inverse.svg` | Lockup sobre claro / sobre `primary` |
| `frontend/src/index.css` | Fuente única de color. Se le añade un token |
| `frontend/tests/brand-tokens.test.ts` | El gate. Cuatro reglas |
| `frontend/index.html` | Metaetiquetas OG/Twitter y enlaces a los iconos |

**Qué es fuente y qué es artefacto.** Fuente: `build-identity.py`, `og-image.html`, `index.css`, el brandbook. Artefacto generado pero commiteado: los cinco SVG (porque los consume el resto del proyecto y el build de Netlify no ejecuta Python). Artefacto binario: `.ico`, `apple-touch-icon.png`, `og-image.png` — no se editan a mano nunca.

---

### Task 1: Commitear el manifiesto

`docs/brand/manifiesto.md` ya existe en el árbol de trabajo sin versionar. Es la entrada de la narrativa que el resto del trabajo cita, así que va primero y solo.

**Files:**
- Commit: `docs/brand/manifiesto.md`

- [ ] **Step 1: Comprobar que el archivo está y no está versionado**

```bash
git status --short docs/brand/manifiesto.md
```

Expected: `?? docs/brand/manifiesto.md`

- [ ] **Step 2: Comprobar que el spec revisado también está pendiente**

```bash
git status --short docs/superpowers/specs/
```

Expected: ` M docs/superpowers/specs/2026-07-29-marca-y-brandbook-design.md`

- [ ] **Step 3: Commit**

```bash
git add docs/brand/manifiesto.md docs/superpowers/specs/2026-07-29-marca-y-brandbook-design.md
git commit -m "docs(brand): manifiesto canónico y narrativa de marca

El spec incorpora la narrativa de movimiento (§1 y §6) y el manifiesto
desarrolla sus tres versiones de uso —íntegra, corta y de una línea— con
las reglas que impiden despiezarlo."
```

---

### Task 2: Token `accent-400` y test de contraste

El ámbar vigente (`accent-500`, `#d97706`) sobre `primary` da 3.61:1 y a 16 px la F se apelmaza. Entra un token nuevo. **El test va antes que el token**, para verlo fallar por la razón correcta.

**Files:**
- Create: `frontend/tests/brand-tokens.test.ts`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Escribir el test que falla**

Create `frontend/tests/brand-tokens.test.ts`:

```ts
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const RAIZ = fileURLToPath(new URL('..', import.meta.url));
const CSS = readFileSync(`${RAIZ}src/index.css`, 'utf8');

/** Tokens de color declarados en la fuente única, por nombre sin el prefijo. */
export const TOKENS: Record<string, string> = Object.fromEntries(
  [...CSS.matchAll(/--color-([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})\s*;/g)].map((m) => [m[1], m[2]])
);

const luminancia = (hex: string): number => {
  const canales = [1, 3, 5]
    .map((i) => Number.parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * canales[0] + 0.7152 * canales[1] + 0.0722 * canales[2];
};

/** Ratio de contraste WCAG 2.1 entre dos tokens. */
export const contraste = (a: string, b: string): number => {
  const claro = Math.max(luminancia(TOKENS[a]), luminancia(TOKENS[b]));
  const oscuro = Math.min(luminancia(TOKENS[a]), luminancia(TOKENS[b]));
  return (claro + 0.05) / (oscuro + 0.05);
};

const AA_NORMAL = 4.5;

describe('paleta', () => {
  it('declara los tokens que el brandbook documenta', () => {
    for (const token of ['background', 'foreground', 'primary', 'accent-400', 'accent-500']) {
      expect(TOKENS, `falta --color-${token} en src/index.css`).toHaveProperty(token);
    }
  });

  // Cada par de la tabla del brandbook §3. Si uno baja de AA, el documento
  // miente y el test lo dice antes que un usuario.
  it.each([
    ['foreground', 'background', 17.85],
    ['foreground', 'secondary', 16.3],
    ['secondary-foreground', 'secondary', 13.35],
    ['primary', 'background', 11.5],
    ['primary-foreground', 'primary', 10.99],
    ['primary', 'accent', 11.09],
    ['accent-foreground', 'accent', 8.75],
    ['destructive', 'background', 6.47],
    ['accent-400', 'primary', 5.36],
    ['success', 'background', 5.02],
    ['warning', 'background', 5.02],
    ['accent-600', 'background', 5.02],
    ['muted-foreground', 'background', 4.76],
  ])('%s sobre %s cumple AA y sigue en %f:1', (frente, fondo, esperado) => {
    const ratio = contraste(frente, fondo);
    expect(ratio).toBeGreaterThanOrEqual(AA_NORMAL);
    expect(ratio).toBeCloseTo(esperado, 1);
  });

  // Al revés a propósito: estos dos pares NO cumplen AA y el brandbook los
  // prohíbe. Si alguien retoca el token y los arregla, este test se cae y
  // obliga a actualizar la regla en vez de dejarla caducada en el documento.
  it.each([
    ['muted-foreground', 'muted'],
    ['accent-500', 'background'],
  ])('%s sobre %s sigue por debajo de AA (par prohibido)', (frente, fondo) => {
    expect(contraste(frente, fondo)).toBeLessThan(AA_NORMAL);
  });
});
```

- [ ] **Step 2: Ejecutar el test y verlo fallar**

```bash
cd frontend && npx vitest run tests/brand-tokens.test.ts
```

Expected: FAIL, dos casos. El primero por aserción: `falta --color-accent-400 en src/index.css`. El segundo, `accent-400 sobre primary`, por excepción — `TypeError: Cannot read properties of undefined (reading 'slice')`, porque `TOKENS['accent-400']` no existe todavía. Verificado: es un `TypeError`, no un `NaN`.

- [ ] **Step 3: Añadir el token**

Modify `frontend/src/index.css` — dentro del bloque `@theme`, en el grupo del acento, justo antes de `--color-accent-500`:

```css
  /* Acento — ámbar sobrio para citas y destacados */
  --color-accent: #fffbeb;
  --color-accent-foreground: #78350f;
  --color-accent-400: #f59e0b;
  --color-accent-500: #d97706;
  --color-accent-600: #b45309;
```

`accent-400` es **ámbar sobre superficie azul** (5.36:1 sobre `primary`): isotipo y cualquier futura superficie `primary`. No sustituye a `accent-500` ni a `accent-600` sobre fondos claros.

- [ ] **Step 4: Ejecutar el test y verlo pasar**

```bash
cd frontend && npx vitest run tests/brand-tokens.test.ts
```

Expected: PASS, 16 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/index.css frontend/tests/brand-tokens.test.ts
git commit -m "feat(brand): token accent-400 y gate de contraste

El ámbar accent-500 sobre primary se queda en 3.61:1 y a 16 px la F del
monograma se apelmaza contra el azul. accent-400 (#f59e0b) da 5.36:1 y queda
reservado a ámbar sobre superficie azul.

El test recalcula la tabla de contraste del brandbook desde index.css, y
comprueba al revés los dos pares que hoy fallan AA: si alguien los arregla,
falla y obliga a actualizar la regla."
```

---

### Task 3: Las otras tres reglas del gate

Contraste no basta. Las tres reglas que siguen son errores que ya han pasado en Comunicador y que **no avisan**: la clase se renderiza transparente, o el control se queda sin foco, y nadie se entera.

**Files:**
- Modify: `frontend/tests/brand-tokens.test.ts`

- [ ] **Step 1: Escribir los tests que fallan**

Primero, ampliar el `import` que ya está **en la cabecera** del archivo — no añadir un segundo `import` al final, porque `organizeImports` de Biome lo movería arriba y el diff del siguiente commit saldría sucio:

```ts
import { readdirSync, readFileSync } from 'node:fs';
```

Y añadir al final de `frontend/tests/brand-tokens.test.ts`:

```ts
const recorrer = (dir: string): string[] =>
  readdirSync(dir, { withFileTypes: true }).flatMap((entrada) => {
    const ruta = `${dir}/${entrada.name}`;
    return entrada.isDirectory() ? recorrer(ruta) : [ruta];
  });

const ARCHIVOS_SRC = recorrer(`${RAIZ}src`).map((ruta) => ({
  ruta: ruta.slice(RAIZ.length),
  contenido: readFileSync(ruta, 'utf8'),
}));

const CODIGO = ARCHIVOS_SRC.filter((a) => /\.(ts|tsx)$/.test(a.ruta));

describe('fuente única de color', () => {
  // Los SVG de identidad llevan HEX literales a la fuerza: un SVG estático no
  // lee var() del CSS. Son la única excepción, y está declarada aquí para que
  // añadir una segunda sea una decisión visible en el diff.
  const EXCEPCIONES = ['src/index.css', 'src/assets/logo.svg', 'src/assets/logo-inverse.svg'];

  it('ningún archivo de src/ declara colores literales', () => {
    const infractores = ARCHIVOS_SRC.filter(
      (a) => !EXCEPCIONES.includes(a.ruta) && /#[0-9a-fA-F]{3,8}\b/.test(a.contenido)
    ).map((a) => a.ruta);
    expect(infractores).toEqual([]);
  });
});

describe('clases de color', () => {
  const FAMILIAS = [...new Set(Object.keys(TOKENS).map((t) => t.split('-')[0]))];
  const UTILIDAD = new RegExp(
    `\\b(?:bg|text|border|ring|fill|stroke|outline|divide|from|via|to)-` +
      `((?:${FAMILIAS.join('|')})(?:-[a-z0-9]+)*)`,
    'g'
  );

  // Solo `primary` tiene escala 50…950 y `accent` tiene 400/500/600. Una clase
  // como `bg-warning-50` se renderiza transparente sin que nada avise. Ya pasó
  // tres veces en Comunicador.
  it('toda clase de color usada corresponde a un token declarado', () => {
    const inexistentes = new Set<string>();
    for (const { contenido } of CODIGO) {
      for (const [, nombre] of contenido.matchAll(UTILIDAD)) {
        if (!(nombre in TOKENS)) inexistentes.add(nombre);
      }
    }
    expect([...inexistentes]).toEqual([]);
  });

  // Comprobación literal sobre el mismo atributo className. No ve el árbol
  // renderizado: no detecta el caso en que el fondo teñido lo pone un
  // componente padre. Cubre el error frecuente, no todos.
  it('no combina texto muted-foreground sobre superficie teñida', () => {
    const infractores: string[] = [];
    for (const { ruta, contenido } of CODIGO) {
      for (const [, clases] of contenido.matchAll(/className=['"]([^'"]+)['"]/g)) {
        const teñido = /\bbg-(muted|secondary)\b/.test(clases);
        if (teñido && /\btext-muted-foreground\b/.test(clases)) infractores.push(`${ruta}: ${clases}`);
      }
    }
    expect(infractores).toEqual([]);
  });

  it('nunca usa accent-500 como color de texto', () => {
    const infractores = CODIGO.filter((a) => /\btext-accent-500\b/.test(a.contenido)).map((a) => a.ruta);
    expect(infractores).toEqual([]);
  });
});

describe('utilidades control-*', () => {
  // Un primitivo que referencia `control-focus` sin que la clase exista se
  // queda sin anillo de foco y nada avisa. Pasó en Comunicador con cinco.
  it('toda clase control-* referenciada existe en index.css', () => {
    const usadas = new Set<string>();
    for (const { contenido } of CODIGO) {
      for (const [clase] of contenido.matchAll(/\bcontrol-[a-z-]+\b/g)) usadas.add(clase);
    }
    const faltan = [...usadas].filter((clase) => !CSS.includes(`.${clase}`));
    expect(faltan).toEqual([]);
  });
});
```

- [ ] **Step 2: Ejecutar y ver qué encuentra**

```bash
cd frontend && npx vitest run tests/brand-tokens.test.ts
```

Expected: los tests corren. **Es esperable que alguno falle señalando código real existente** — es el objetivo del gate, no un fallo del test.

Si `ningún archivo de src/ declara colores literales` falla, mirar el archivo: si es un color de marca, se sustituye por el token; si es un caso legítimo nuevo, se añade a `EXCEPCIONES` **con un comentario que diga por qué**.

Si `toda clase de color usada corresponde a un token declarado` falla, la clase señalada se está renderizando transparente ahora mismo en producción: se corrige al token que existe.

- [ ] **Step 3: Corregir lo que salga**

Arreglar el código señalado, no el test. Un test de marca que se relaja para pasar no sirve de nada.

- [ ] **Step 4: Verificar en verde y comprobar que el gate entra en `fast-check`**

```bash
cd frontend && npm run fast-check
```

Expected: biome, tsc y vitest en verde, con `tests/brand-tokens.test.ts` entre las suites ejecutadas.

- [ ] **Step 5: Commit**

```bash
git add frontend/tests/brand-tokens.test.ts frontend/src
git commit -m "test(brand): tres reglas más en el gate de marca

HEX literales fuera de index.css, clases de color sobre tokens inexistentes
(se renderizan transparentes sin avisar) y utilidades control-* referenciadas
pero no definidas (dejan el control sin foco). Los tres son errores mudos."
```

---

### Task 4: Generador de identidad

Los cinco SVG salen de un solo script. Las letras van **convertidas a trazado**: un SVG estático no puede depender de que Space Grotesk esté instalada en el dispositivo que lo abre.

**Files:**
- Create: `frontend/brand/build-identity.py`
- Modify: `frontend/package.json`
- Modify: `frontend/.gitignore` (crear si no existe)
- Generated: `frontend/public/favicon.svg`, `frontend/src/assets/logo.svg`, `frontend/src/assets/logo-inverse.svg`, `frontend/brand/.render/*.svg`

- [ ] **Step 1: Escribir el generador**

Create `frontend/brand/build-identity.py` — este script está verificado y produce las cinco salidas correctas:

```python
#!/usr/bin/env python3
"""Genera los SVG de identidad de Residencia Fiscal desde Space Grotesk.

    npm run identity        (desde frontend/)

Produce cinco archivos:

    public/favicon.svg            isotipo, monograma «RF» sobre primary
    src/assets/logo.svg           lockup horizontal sobre fondo claro
    src/assets/logo-inverse.svg   lockup para fondo primary
    brand/.render/iso-16.svg      variante para el .ico de 16 px
    brand/.render/iso-fullbleed.svg   variante a sangre para apple-touch

Las letras van convertidas a trazado a propósito: un SVG estático no puede
depender de que Space Grotesk esté instalada en el dispositivo que lo abre.
Las URL de las fuentes están fijadas (v22) para que el resultado sea
reproducible.

Los HEX van literales porque un SVG estático no lee `var()` del CSS. Son los
tokens de src/index.css: si cambia un token, cambia aquí en el mismo commit.
Contrato en docs/brand/brand-guidelines.md.
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

try:
    from fontTools.misc.transform import Identity
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont
except ModuleNotFoundError:
    sys.exit('Falta fontTools: pip install fonttools (o uv pip install fonttools).')

RAIZ = Path(__file__).resolve().parent.parent

# Space Grotesk v22, pesos 700 (isotipo), 600 («Residencia») y 500 («Fiscal»).
FUENTES = {
    700: 'https://fonts.gstatic.com/s/spacegrotesk/v22/V8mQoQDjQSkFtoMM3T6r8E7mF71Q-gOoraIAEj4PVksj.ttf',
    600: 'https://fonts.gstatic.com/s/spacegrotesk/v22/V8mQoQDjQSkFtoMM3T6r8E7mF71Q-gOoraIAEj42Vksj.ttf',
    500: 'https://fonts.gstatic.com/s/spacegrotesk/v22/V8mQoQDjQSkFtoMM3T6r8E7mF71Q-gOoraIAEj7aUUsj.ttf',
}

# Tokens de src/index.css.
AZUL = '#1e3a5f'        # primary
BLANCO = '#ffffff'      # background
AMBAR = '#f59e0b'       # accent-400 — ámbar sobre azul, 5.36:1
TINTA = '#0f172a'       # foreground
GRIS = '#64748b'        # muted-foreground
AZUL_CLARO = '#e2ebf4'  # primary-100

CAJA = 64          # lado del isotipo
ALTURA_CAJA = 700  # cap height de Space Grotesk, en unidades de em


def descargar(peso: int, destino: Path) -> Path:
    if not destino.exists():
        print(f'  descargando Space Grotesk {peso}…')
        destino.parent.mkdir(parents=True, exist_ok=True)
        peticion = urllib.request.Request(FUENTES[peso], headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(peticion, timeout=30) as respuesta:
            destino.write_bytes(respuesta.read())
    return destino


def trazar(ttf: Path, texto: str, tracking: float = 0.0) -> tuple[str, float]:
    """Compone `texto` en una sola ruta SVG. Devuelve (d, ancho_en_unidades)."""
    fuente = TTFont(ttf)
    glifos, cmap, hmtx = fuente.getGlyphSet(), fuente.getBestCmap(), fuente['hmtx']
    pluma = SVGPathPen(glifos)
    avance = 0.0
    for caracter in texto:
        nombre = cmap[ord(caracter)]
        glifos[nombre].draw(TransformPen(pluma, Identity.translate(avance, 0)))
        avance += hmtx[nombre][0] * (1 + tracking)
    return pluma.getCommands(), avance


def monograma(bold: Path, altura: float, tracking: float) -> tuple[str, str, str]:
    """Devuelve (transform, path_R, plantilla_path_F) del monograma «RF»."""
    r_d, r_avance = trazar(bold, 'R')
    f_d, _ = trazar(bold, 'F')
    escala = altura / ALTURA_CAJA
    avance_r = r_avance * (1 + tracking)
    tinta_izq = 66      # sidebearing izquierdo de la R, en unidades
    tinta_der = 506     # borde derecho de la tinta de la F, en unidades
    ancho = (avance_r + tinta_der - tinta_izq) * escala
    x = (CAJA - ancho) / 2 - tinta_izq * escala
    y = (CAJA + altura) / 2
    return (
        f'translate({x:.2f} {y:.2f}) scale({escala:.5f} -{escala:.5f})',
        r_d,
        f'<path d="{f_d}" fill="{{ambar}}" transform="translate({avance_r:.0f} 0)"/>',
    )


def isotipo(bold: Path, altura: float, tracking: float, radio: int) -> str:
    transform, r_d, f_tpl = monograma(bold, altura, tracking)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="Residencia Fiscal">
  <rect width="64" height="64" rx="{radio}" fill="{AZUL}"/>
  <g transform="{transform}">
    <path d="{r_d}" fill="{BLANCO}"/>
    {f_tpl.format(ambar=AMBAR)}
  </g>
</svg>
'''


def lockup(bold: Path, semi: Path, medium: Path, inverso: bool) -> str:
    """Isotipo + wordmark a su derecha. `inverso` compone para fondo primary."""
    res_d, res_avance = trazar(semi, 'Residencia', -0.01)
    fis_d, fis_avance = trazar(medium, 'Fiscal', -0.01)
    espacio = 260  # separación entre palabras, en unidades de em

    altura_texto = 34
    escala = altura_texto / ALTURA_CAJA
    hueco = CAJA * 0.36  # espacio de respeto entre isotipo y wordmark
    x_texto = CAJA + hueco
    base = (CAJA + altura_texto) / 2
    ancho = x_texto + (res_avance + espacio + fis_avance) * escala

    transform, r_d, f_tpl = monograma(bold, 32, -0.03)
    color_res = BLANCO if inverso else TINTA
    color_fis = AZUL_CLARO if inverso else GRIS
    # Sobre primary la caja azul del isotipo desaparecería: se dibuja el
    # monograma directamente, sin fondo.
    caja = '' if inverso else f'  <rect width="64" height="64" rx="14" fill="{AZUL}"/>\n'

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho:.1f} 64" role="img" aria-label="Residencia Fiscal">
{caja}  <g transform="{transform}">
    <path d="{r_d}" fill="{BLANCO}"/>
    {f_tpl.format(ambar=AMBAR)}
  </g>
  <g transform="translate({x_texto:.2f} {base:.2f}) scale({escala:.5f} -{escala:.5f})">
    <path d="{res_d}" fill="{color_res}"/>
    <path d="{fis_d}" fill="{color_fis}" transform="translate({res_avance + espacio:.0f} 0)"/>
  </g>
</svg>
'''


def main() -> None:
    cache = Path(__file__).resolve().parent / '.fuentes'
    bold = descargar(700, cache / 'SpaceGrotesk-700.ttf')
    semi = descargar(600, cache / 'SpaceGrotesk-600.ttf')
    medium = descargar(500, cache / 'SpaceGrotesk-500.ttf')

    salidas = {
        RAIZ / 'public/favicon.svg': isotipo(bold, 32, -0.03, 14),
        RAIZ / 'src/assets/logo.svg': lockup(bold, semi, medium, inverso=False),
        RAIZ / 'src/assets/logo-inverse.svg': lockup(bold, semi, medium, inverso=True),
        # El .ico de 16 px necesita más caja llena y menos radio: a ese tamaño
        # el monograma normal pierde la contraforma de la R. El apple-touch va
        # a sangre porque iOS aplica su propia máscara de esquinas.
        RAIZ / 'brand/.render/iso-16.svg': isotipo(bold, 38, -0.08, 10),
        RAIZ / 'brand/.render/iso-fullbleed.svg': isotipo(bold, 32, -0.03, 0),
    }
    for ruta, contenido in salidas.items():
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(contenido, encoding='utf-8')
        print(f'  {ruta.relative_to(RAIZ)}  ({len(contenido)} bytes)')


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Ignorar la caché de fuentes y los intermedios de render**

Modify `frontend/.gitignore` (ya existe, con 10 líneas) — añadir al final:

```gitignore

# Caché de las TTF que descarga brand/build-identity.py y variantes
# intermedias de render. Los SVG de salida sí se versionan.
brand/.fuentes/
brand/.render/
```

`frontend/src/assets/` **no existe todavía**: lo crea el generador con `mkdir(parents=True)`. No hay que crearlo a mano.

- [ ] **Step 3: Añadir el script npm**

Modify `frontend/package.json` — en `"scripts"`, tras `"preview"`:

```json
    "identity": "python3 brand/build-identity.py",
```

- [ ] **Step 4: Ejecutar el generador**

```bash
cd frontend && npm run identity
```

Expected:

```
  descargando Space Grotesk 700…
  descargando Space Grotesk 600…
  descargando Space Grotesk 500…
  public/favicon.svg  (795 bytes)
  src/assets/logo.svg  (10164 bytes)
  src/assets/logo-inverse.svg  (10108 bytes)
  brand/.render/iso-16.svg  (795 bytes)
  brand/.render/iso-fullbleed.svg  (794 bytes)
```

- [ ] **Step 5: Comprobar visualmente que el monograma es legible a 16 px**

```bash
cd frontend && cat > /tmp/iso-check.html <<'EOF'
<body style="margin:0;background:#fff;padding:20px;display:flex;gap:16px;align-items:flex-end">
<img src="public/favicon.svg" width="64"><img src="public/favicon.svg" width="32">
<img src="brand/.render/iso-16.svg" width="16"><img src="src/assets/logo.svg" height="40">
</body>
EOF
google-chrome --headless --disable-gpu --no-sandbox --hide-scrollbars \
  --window-size=700,200 --screenshot=/tmp/iso-check.png "file://$PWD/../tmp/iso-check.html" 2>/dev/null
explorer.exe "$(wslpath -w /tmp/iso-check.png)"
```

Expected: se abre en el navegador de Windows. La «RF» se distingue a 16 px y el lockup se lee a 40 px de alto. (`explorer.exe` devuelve exit code 1 aunque funcione; no es un error.)

- [ ] **Step 6: Comprobar que el gate sigue verde con los SVG nuevos**

```bash
cd frontend && npx vitest run tests/brand-tokens.test.ts
```

Expected: PASS. `logo.svg` y `logo-inverse.svg` están en la lista de `EXCEPCIONES` de HEX literales; si el test falla ahí, es que el nombre del archivo no coincide con la excepción declarada.

- [ ] **Step 7: Commit**

```bash
git add frontend/brand/build-identity.py frontend/package.json frontend/.gitignore \
        frontend/public/favicon.svg frontend/src/assets/logo.svg frontend/src/assets/logo-inverse.svg
git commit -m "feat(brand): isotipo RF y lockup generados desde Space Grotesk

Monograma «RF» sobre primary, R en blanco y F en accent-400: el color separa
las dos palabras del nombre en lugar de añadir un elemento decorativo.
Sustituye el favicon provisional de la «R».

Las letras van trazadas porque un SVG estático no puede depender de que la
fuente esté instalada donde se abra. El generador fija las URL de Space
Grotesk v22 para que el trazado no cambie solo.

logo-inverse.svg va más allá del spec: sin él la marca no puede ponerse sobre
su propio azul, porque la caja del isotipo desaparecería contra el fondo."
```

---

### Task 5: Favicon, `.ico` y `apple-touch-icon`

**Files:**
- Create: `frontend/brand/render-favicon.sh`
- Modify: `frontend/package.json`
- Generated: `frontend/public/favicon.ico`, `frontend/public/apple-touch-icon.png`

- [ ] **Step 1: Escribir el script de render**

Create `frontend/brand/render-favicon.sh`:

```bash
#!/usr/bin/env bash
# Render determinista del favicon y sus derivados.
#
#   npm run favicon      (desde frontend/)
#
# Las fuentes son los SVG que genera brand/build-identity.py. Produce dos
# artefactos que no se editan a mano:
#   - public/favicon.ico          48/32 desde el isotipo normal; 16 desde la
#                                 variante de caja llena, porque a ese tamaño
#                                 el monograma normal pierde la contraforma
#                                 de la R.
#   - public/apple-touch-icon.png 180x180 a sangre: iOS aplica su propia
#                                 máscara de esquinas, así que sin rx.
# Contrato en docs/brand/brand-guidelines.md.
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f brand/.render/iso-16.svg ]; then
  echo "Faltan las variantes de render. Ejecuta antes: npm run identity" >&2
  exit 1
fi

CHROME="${CHROME_BIN:-}"
if [ -z "$CHROME" ]; then
  for candidato in google-chrome google-chrome-stable chromium chromium-browser; do
    if command -v "$candidato" >/dev/null 2>&1; then
      CHROME="$(command -v "$candidato")"
      break
    fi
  done
fi
if [ -z "$CHROME" ]; then
  echo "No encuentro Chrome ni Chromium. Instala uno o exporta CHROME_BIN=/ruta/al/binario." >&2
  exit 1
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

captura() { # captura <ruta_svg> <lado_px> <salida_png>
  local svg="$1" lado="$2" salida="$3"
  printf '<body style="margin:0;background:transparent"><img src="file://%s" width="%s" height="%s"></body>' \
    "$(realpath "$svg")" "$lado" "$lado" > "$TMP/wrap.html"
  "$CHROME" --headless --disable-gpu --no-sandbox --hide-scrollbars \
    --default-background-color=00000000 --window-size=800,900 \
    --screenshot="$salida" "file://$TMP/wrap.html" >/dev/null 2>&1
}

captura public/favicon.svg 512 "$TMP/base.png"
captura brand/.render/iso-16.svg 128 "$TMP/pequeno.png"
captura brand/.render/iso-fullbleed.svg 512 "$TMP/sangre.png"

python3 - "$TMP" <<'PY'
import sys

try:
    from PIL import Image
except ModuleNotFoundError:
    sys.exit('Falta Pillow: pip install pillow (o uv pip install pillow).')

tmp = sys.argv[1]
L = Image.Resampling.LANCZOS

base = Image.open(f'{tmp}/base.png').crop((0, 0, 512, 512))
pequeno = Image.open(f'{tmp}/pequeno.png').crop((0, 0, 128, 128))
sangre = Image.open(f'{tmp}/sangre.png').crop((0, 0, 512, 512))

base.resize((48, 48), L).save(
    'public/favicon.ico',
    format='ICO',
    append_images=[base.resize((32, 32), L), pequeno.resize((16, 16), L)],
)
sangre.convert('RGB').resize((180, 180), L).save('public/apple-touch-icon.png')
PY

echo "public/favicon.ico (48/32/16) y public/apple-touch-icon.png (180x180) regenerados."
```

- [ ] **Step 2: Hacerlo ejecutable y añadir el script npm**

```bash
chmod +x frontend/brand/render-favicon.sh
```

Modify `frontend/package.json` — tras `"identity"`:

```json
    "favicon": "bash brand/render-favicon.sh",
```

- [ ] **Step 3: Ejecutar**

```bash
cd frontend && npm run favicon
```

Expected: `public/favicon.ico (48/32/16) y public/apple-touch-icon.png (180x180) regenerados.`

- [ ] **Step 4: Verificar los artefactos**

```bash
cd frontend && python3 -c "
from PIL import Image
ico = Image.open('public/favicon.ico')
print('ico tamaños:', sorted(ico.info['sizes']))
print('apple-touch:', Image.open('public/apple-touch-icon.png').size)
"
```

Expected:

```
ico tamaños: [(16, 16), (32, 32), (48, 48)]
apple-touch: (180, 180)
```

- [ ] **Step 5: Commit**

```bash
git add frontend/brand/render-favicon.sh frontend/package.json \
        frontend/public/favicon.ico frontend/public/apple-touch-icon.png
git commit -m "feat(brand): favicon.ico y apple-touch-icon

El 16 px sale de la variante de caja llena, no de engrosar el trazo como hace
Comunicador: nuestro monograma son contornos rellenos, no un stroke, y no hay
stroke-width que tocar.

Los dos binarios son artefactos: se regeneran con npm run favicon."
```

---

### Task 6: Imagen Open Graph

**Files:**
- Create: `frontend/brand/og-image.html`
- Create: `frontend/brand/render.sh`
- Modify: `frontend/package.json`
- Generated: `frontend/public/og-image.png`

- [ ] **Step 1: Escribir la fuente de la imagen**

Create `frontend/brand/og-image.html`. El render inyecta los tokens de `index.css` donde está el marcador `/* TOKENS */`, así que aquí **no se escribe ningún HEX**:

```html
<!doctype html>
<meta charset="utf-8" />
<style>
  /* TOKENS */
  @font-face {
    font-family: 'Space Grotesk';
    src: url('.fuentes/SpaceGrotesk-600.ttf') format('truetype');
    font-weight: 600;
  }
  @font-face {
    font-family: 'Space Grotesk';
    src: url('.fuentes/SpaceGrotesk-500.ttf') format('truetype');
    font-weight: 500;
  }
  * { margin: 0; box-sizing: border-box; }
  body {
    width: 1200px; height: 630px;
    background: var(--color-background);
    border-top: 10px solid var(--color-primary);
    padding: 72px 80px;
    display: flex; flex-direction: column; justify-content: space-between;
    font-family: 'Space Grotesk', system-ui, sans-serif;
  }
  .lockup { height: 56px; }
  .claim {
    font-size: 62px; font-weight: 600; line-height: 1.14;
    letter-spacing: -0.02em; color: var(--color-foreground);
    max-width: 15ch;
  }
  .claim span { color: var(--color-primary); }
  .firma {
    font-size: 25px; font-weight: 500; color: var(--color-muted-foreground);
    display: flex; align-items: center; gap: 14px;
  }
  .filete { width: 40px; height: 5px; background: var(--color-accent-500); }
</style>
<body>
  <img class="lockup" src="../src/assets/logo.svg" alt="Residencia Fiscal" />
  <p class="claim">Reside donde mejor te traten.<br /><span>Decide con las sentencias en la mano.</span></p>
  <p class="firma"><i class="filete"></i>106 sentencias del Tribunal Supremo y la Audiencia Nacional · 2015–2025</p>
</body>
```

El claim va en `foreground` y no en `muted-foreground` como decía el spec §7: es el texto principal de la pieza y en gris a 62 px queda lavado. La firma sí es `muted-foreground`, que es donde el spec buscaba la sobriedad. La firma además cumple la regla del manifiesto: **la promesa de libertad nunca viaja sola** — aquí el ancla es la cifra del corpus.

- [ ] **Step 2: Escribir el script de render**

Create `frontend/brand/render.sh`:

```bash
#!/usr/bin/env bash
# Render determinista de la imagen Open Graph.
#
#   npm run og      (desde frontend/)
#
# Toma brand/og-image.html, le inyecta los tokens de color de src/index.css y
# lo fotografía con Chrome headless a 1200x630 exactos. El PNG resultante es un
# artefacto: no se edita a mano.
# Contrato en docs/brand/brand-guidelines.md.
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f brand/.fuentes/SpaceGrotesk-600.ttf ]; then
  echo "Faltan las fuentes. Ejecuta antes: npm run identity" >&2
  exit 1
fi

CHROME="${CHROME_BIN:-}"
if [ -z "$CHROME" ]; then
  for candidato in google-chrome google-chrome-stable chromium chromium-browser; do
    if command -v "$candidato" >/dev/null 2>&1; then
      CHROME="$(command -v "$candidato")"
      break
    fi
  done
fi
if [ -z "$CHROME" ]; then
  echo "No encuentro Chrome ni Chromium. Instala uno o exporta CHROME_BIN=/ruta/al/binario." >&2
  exit 1
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Los tokens salen de index.css, que es la fuente única de color.
{
  echo ':root {'
  grep -oE -- '--color-[a-z0-9-]+:[[:space:]]*#[0-9a-fA-F]{3,8};' src/index.css
  echo '}'
} > "$TMP/tokens.css"

# El HTML se renderiza en su directorio para que las rutas relativas a las
# fuentes y al lockup sigan resolviendo.
sed -e "/\/\* TOKENS \*\//r $TMP/tokens.css" brand/og-image.html > brand/.render/og.html
trap 'rm -rf "$TMP" brand/.render/og.html' EXIT

ANCHO=1200
ALTO=630

# `--window-size` es la ventana, no el viewport: Chrome descuenta su propio
# cromo y la imagen saldría recortada. En vez de compensar con un número
# mágico, se mide el desfase aquí.
printf '<html><body><script>document.body.textContent="VP:"+innerWidth+"x"+innerHeight</script></body></html>' > "$TMP/sonda.html"
MEDIDA="$("$CHROME" --headless --disable-gpu --no-sandbox --window-size="$ANCHO,$ALTO" \
  --virtual-time-budget=500 --dump-dom "file://$TMP/sonda.html" 2>/dev/null |
  grep -oE 'VP:[0-9]+x[0-9]+' | head -1)"
if [ -z "$MEDIDA" ]; then
  echo "No pude medir el viewport de Chrome." >&2
  exit 1
fi
VP_ANCHO="${MEDIDA#VP:}"; VP_ANCHO="${VP_ANCHO%%x*}"
VP_ALTO="${MEDIDA##*x}"
VENTANA_ANCHO=$(( ANCHO + ANCHO - VP_ANCHO ))
VENTANA_ALTO=$(( ALTO + ALTO - VP_ALTO ))

"$CHROME" --headless --disable-gpu --no-sandbox --hide-scrollbars \
  --allow-file-access-from-files --virtual-time-budget=2000 \
  --window-size="$VENTANA_ANCHO,$VENTANA_ALTO" \
  --screenshot="$TMP/og.png" "file://$PWD/brand/.render/og.html" >/dev/null 2>&1

python3 - "$TMP/og.png" "$ANCHO" "$ALTO" <<'PY'
import sys

try:
    from PIL import Image
except ModuleNotFoundError:
    sys.exit('Falta Pillow: pip install pillow (o uv pip install pillow).')

ruta, ancho, alto = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
imagen = Image.open(ruta)
if imagen.size != (ancho, alto):
    imagen = imagen.crop((0, 0, ancho, alto))
imagen.save(ruta)
PY

mv "$TMP/og.png" public/og-image.png
echo "public/og-image.png regenerado (${ANCHO}x${ALTO})."
```

- [ ] **Step 3: Hacerlo ejecutable y añadir el script npm**

```bash
chmod +x frontend/brand/render.sh
```

Modify `frontend/package.json` — tras `"favicon"`:

```json
    "og": "bash brand/render.sh",
```

- [ ] **Step 4: Ejecutar y verificar dimensiones**

```bash
cd frontend && npm run og && python3 -c "
from PIL import Image
print(Image.open('public/og-image.png').size)
"
```

Expected:

```
public/og-image.png regenerado (1200x630).
(1200, 630)
```

- [ ] **Step 5: Mirarla**

```bash
explorer.exe "$(wslpath -w "$PWD/frontend/public/og-image.png")"
```

Expected: el lockup arriba, el claim de dos líneas (la segunda en `primary`) y la firma con el filete ámbar abajo. Si las letras salen con una fuente del sistema en vez de Space Grotesk, es que las rutas `@font-face` no resolvieron: comprobar que `brand/.fuentes/` tiene los `.ttf` y que el render se hizo desde `brand/.render/og.html`.

- [ ] **Step 6: Commit**

```bash
git add frontend/brand/og-image.html frontend/brand/render.sh frontend/package.json \
        frontend/public/og-image.png
git commit -m "feat(brand): imagen Open Graph

Claim canónico sobre lienzo blanco, filete primary arriba y la cifra del
corpus como firma: la promesa de libertad no viaja sola, que es la regla 2
del manifiesto.

El claim va en foreground y no en muted-foreground como pedía el spec: a
62 px el gris al 4.76:1 queda lavado. El gris se queda en la firma."
```

---

### Task 7: Metaetiquetas en `index.html`

Hoy `frontend/index.html` no tiene **ninguna** metaetiqueta social: un enlace compartido sale sin tarjeta.

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1: Añadir enlaces de icono y metaetiquetas**

Modify `frontend/index.html` — sustituir la línea `<link rel="icon" … />` por este bloque, dejando intactos los `preconnect` y la hoja de Google Fonts que van después:

```html
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <link rel="icon" type="image/x-icon" href="/favicon.ico" sizes="48x48 32x32 16x16" />
    <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
    <link rel="canonical" href="https://www.residenciafiscal.org/" />

    <meta property="og:type" content="website" />
    <meta property="og:site_name" content="Residencia Fiscal" />
    <meta property="og:locale" content="es_ES" />
    <meta property="og:url" content="https://www.residenciafiscal.org/" />
    <meta
      property="og:title"
      content="Residencia Fiscal — Reside donde mejor te traten"
    />
    <meta
      property="og:description"
      content="Consulta en lenguaje natural 106 sentencias del Tribunal Supremo y la Audiencia Nacional sobre residencia fiscal de personas físicas en España. Cada respuesta cita la resolución en que se apoya."
    />
    <meta property="og:image" content="https://www.residenciafiscal.org/og-image.png" />
    <meta property="og:image:width" content="1200" />
    <meta property="og:image:height" content="630" />
    <meta
      property="og:image:alt"
      content="Residencia Fiscal — 106 sentencias del Tribunal Supremo y la Audiencia Nacional, 2015-2025"
    />
    <meta name="twitter:card" content="summary_large_image" />
```

El dominio va en forma `www` porque el ápex redirige con 301 (`netlify.toml`). Una URL absoluta al ápex haría que cada scraper social se comiera un salto de más.

- [ ] **Step 2: Comprobar que el build no se rompe**

```bash
cd frontend && npm run typecheck && npx vite build --mode development 2>&1 | tail -5
```

Expected: `tsc` sin errores. `vite build` **puede fallar** si `src/main.tsx` o `src/App.tsx` aún no existen en el árbol — eso es una pendiente conocida del proyecto, ajena a esta tarea. Si falla por eso, seguir; si falla por `index.html`, corregir el HTML.

- [ ] **Step 3: Verificar que los artefactos referenciados existen**

```bash
cd frontend && ls -la public/favicon.svg public/favicon.ico public/apple-touch-icon.png public/og-image.png
```

Expected: los cuatro presentes.

- [ ] **Step 4: Commit**

```bash
git add frontend/index.html
git commit -m "feat(brand): metaetiquetas Open Graph y enlaces de icono

Hasta ahora un enlace compartido salía sin tarjeta: no había ninguna
metaetiqueta social. Las URL absolutas usan la forma www porque el ápex
redirige con 301 y si no cada scraper se comería un salto de más."
```

---

### Task 8: El brandbook

El documento canónico. Debe poder leerse solo y bastar para producir una pieza correcta.

**Files:**
- Create: `docs/brand/brand-guidelines.md`

- [ ] **Step 1: Escribir el brandbook**

Create `docs/brand/brand-guidelines.md` con esta estructura y este contenido. Es un documento largo; el criterio es que **cada regla diga por qué**, porque una regla sin motivo se salta en cuanto estorba.

Secciones, en este orden:

1. **Cabecera de estado** — activo, creado 2026-07-29, con la frase que fija la relación con el código: *fuente única de los tokens es `frontend/src/index.css`; este documento explica y restringe esos tokens, no los duplica como sistema paralelo. Si cambia el CSS, se actualiza esta página en el mismo commit.*
2. **Narrativa** — resumen de dos párrafos y enlace a [`manifiesto.md`](./manifiesto.md) como canónico. No se copia el manifiesto aquí: se enlaza.
3. **Concepto visual «El expediente, legible»** — la narrativa es de libertad, la ejecución de rigor; *el color se gana*; la cita como activo que no se negocia.
4. **Color** — la tabla de contraste del spec §3 **íntegra**, con las dos reglas que salen de ella (`muted-foreground` no va sobre superficie teñida; `accent-500` no lleva texto ni es texto) y la nota de paleta cerrada. Añadir `accent-400` con su motivo: ámbar sobre azul, 5.36:1.
5. **Tipografía** — los tres roles (Space Grotesk titulares, Inter texto, monoespaciado evidencia) y el motivo del tercero. La deuda de Google Fonts CDN, declarada.
6. **Composición** — los seis puntos del spec §5.
7. **Identidad gráfica** — isotipo, wordmark, lockup, variante inversa, espacio de respeto, tamaños mínimos, vetos gráficos. **Fuente única: `frontend/brand/build-identity.py`**; los SVG se commitean porque los consume el resto del proyecto y el build de Netlify no ejecuta Python. Los HEX van literales en los SVG porque un SVG estático no lee `var()`: si cambia un token, cambia ahí en el mismo commit.
8. **Voz y mensaje** — claim canónico y funcional, cuándo se usa cada uno, mensajes de apoyo, las cuatro promesas, la distinción obligatoria (criterio / hechos probados / inferencia) y **las dos familias de vetos** con su motivo: contra el humo y contra la sombra de evasión.
9. **Superficies** — la tabla del spec §7 más el dominio canónico.
10. **Artefactos** — qué es fuente y qué es artefacto, con los tres comandos (`npm run identity`, `npm run favicon`, `npm run og`).
11. **Checklist QA** — antes de publicar cualquier pieza.
12. **Comprobación determinista** — las cuatro reglas de `frontend/tests/brand-tokens.test.ts` y qué cubre y qué no cubre cada una.
13. **Pendientes** — modo oscuro, fuentes en CDN, doble audiencia.
14. **Change log** — entrada del 2026-07-29.

El checklist QA (§11) debe incluir, como mínimo:

```markdown
- [ ] El mensaje se entiende en menos de 10 segundos y no promete nada fuera de
      las cuatro promesas.
- [ ] Solo tokens de la paleta; ningún HEX nuevo escrito a mano.
- [ ] `accent-500` no lleva texto encima ni se usa como color de texto.
- [ ] Ningún metadato en `muted-foreground` sobre fondo `muted` o `secondary`.
- [ ] Todo contenido generado que se muestre lleva su cita visible (ROJ/ECLI).
- [ ] Ninguna palabra de las dos listas de vetos.
- [ ] Si la pieza usa el manifiesto, lleva el ancla del producto: cifra del
      corpus, una cita, o la segunda frase del claim.
- [ ] Contraste comprobado en cualquier par nuevo (calculado, no estimado a ojo).
- [ ] Si el motor sigue en `stub`, la pieza no promete respuestas reales.
```

- [ ] **Step 2: Comprobar que los enlaces internos resuelven**

```bash
cd /home/ubuntu/ai_projects/residenciafiscal && \
grep -oE '\]\(\.{0,2}/?[^)]+\.(md|css|ts|py|sh|html|svg)\)' docs/brand/brand-guidelines.md |
  tr -d '](' | tr -d ')' | while read -r destino; do
    ruta="docs/brand/$destino"
    [ -e "$(realpath -m "$ruta")" ] || echo "ROTO: $destino"
  done
```

Expected: sin salida.

- [ ] **Step 3: Comprobar que la tabla de contraste del documento coincide con la realidad**

```bash
cd frontend && npx vitest run tests/brand-tokens.test.ts
```

Expected: PASS. Los valores de la tabla del brandbook son los mismos que afirma el test; si divergen, manda el test.

- [ ] **Step 4: Commit**

```bash
git add docs/brand/brand-guidelines.md
git commit -m "docs(brand): brandbook de Residencia Fiscal

Documento canónico: concepto, color con la tabla de contraste calculada,
tipografía, composición, identidad gráfica, voz y mensaje, superficies,
artefactos, checklist QA y las cuatro reglas del gate.

Explica y restringe los tokens de index.css; no los duplica como sistema
paralelo. Cada regla lleva su motivo, porque una regla sin motivo se salta en
cuanto estorba."
```

---

### Task 9: Enganchar la marca en `CLAUDE.md`

Sin esto, la siguiente sesión de Claude Code no sabe que el brandbook existe y volverá a inventarse los colores.

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Añadir la sección de marca**

Modify `CLAUDE.md` — insertar antes de la sección `## Referencias`:

```markdown
## Marca

La identidad vive en [`docs/brand/`](docs/brand/) y es **canónica**: cualquier
pieza (UI, OG, correo, copy) se produce leyendo esos dos documentos.

| Documento | Rol |
|-----------|-----|
| [`docs/brand/brand-guidelines.md`](docs/brand/brand-guidelines.md) | Brandbook: color, tipografía, logo, composición, voz, superficies, QA |
| [`docs/brand/manifiesto.md`](docs/brand/manifiesto.md) | Narrativa canónica en sus tres versiones de uso |

**Fuente única de color:** `frontend/src/index.css`. El brandbook explica y
restringe esos tokens; no los duplica. Si cambias un token, actualizas el
brandbook en el mismo commit.

**Identidad gráfica:** los cinco SVG se generan con `npm run identity`
(`frontend/brand/build-identity.py`) y **se commitean** — el build de Netlify no
ejecuta Python. Los binarios salen de `npm run favicon` y `npm run og`; son
artefactos y no se editan a mano.

**Gate:** `frontend/tests/brand-tokens.test.ts` recalcula la tabla de contraste
desde `index.css` y bloquea HEX literales, clases de color sobre tokens
inexistentes y utilidades `control-*` sin definir. Entra en `npm run fast-check`.

Dos avisos que ahorran tiempo:

- El ámbar `accent-500` (`#d97706`) **no lleva texto encima ni es color de
  texto**: 3.19:1 sobre blanco. Para texto ámbar, `accent-600`.
- `muted-foreground` sobre `muted`/`secondary` se queda en 4.34:1. Los metadatos
  sobre superficie teñida van en `secondary-foreground`.
```

- [ ] **Step 2: Actualizar la estructura de archivos del propio `CLAUDE.md`**

Modify `CLAUDE.md` — en el bloque `## Estructura de Archivos`, añadir bajo `frontend/`:

```
├── docs/
│   └── brand/               # Brandbook y manifiesto (canónicos)
├── frontend/                # SPA React (residenciafiscal.org)
│   ├── brand/               # build-identity.py, render.sh, render-favicon.sh
│   ├── src/                 # Código de la aplicación
│   ├── scripts/             # build-corpus.mjs
│   └── tests/               # Suites Vitest
```

- [ ] **Step 3: Actualizar la tabla de comandos del frontend**

Modify `CLAUDE.md` — en el bloque de comandos de `### Comandos` del frontend, tras `npm run build`:

```bash
npm run identity    # regenera los SVG de identidad desde Space Grotesk
npm run favicon     # favicon.ico + apple-touch-icon.png
npm run og          # public/og-image.png (1200x630)
```

- [ ] **Step 4: Verificación final completa**

```bash
cd frontend && npm run fast-check
```

Expected: biome, tsc y vitest en verde.

```bash
cd /home/ubuntu/ai_projects/residenciafiscal && make fast-check
```

Expected: ruff, mypy y pytest en verde. (Interesa porque `test_frontend_seo_assets.py` lee ficheros de `frontend/public/` y esta rama toca ese directorio.)

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: engancha el brandbook en CLAUDE.md

Sin esto la siguiente sesión no sabe que la marca existe y vuelve a
inventarse los colores. Incluye los dos avisos de contraste que más fácil es
pisar: accent-500 no lleva texto y muted-foreground no va sobre superficie
teñida."
```

---

### Task 10: Cross-review con Codex

`CLAUDE.md` lo pide para features relevantes, y esta lo es: multi-archivo, con scripts de shell, un gate nuevo y cambios en la configuración del build.

- [ ] **Step 1: Lanzar la review**

```
/codex:review --wait --scope branch --base main
```

- [ ] **Step 2: Si hay hallazgos serios, aplicarlos antes de push**

```
/codex:rescue --resume "aplica los fixes propuestos"
```

- [ ] **Step 3: Commit final de la review**

```bash
git add -A
git commit -m "fix(brand): address codex review"
```

---

## Verificación de cobertura del spec

| Sección del spec | Task |
| --- | --- |
| §1 Narrativa y concepto visual | 1 (manifiesto), 8 (brandbook §2–3) |
| §2 Identidad gráfica, token ámbar | 2 (token), 4 (SVG), 8 (reglas) |
| §3 Color y tabla de contraste | 2 (test), 8 (tabla) |
| §4 Tipografía, rol de evidencia, deuda CDN | 8 |
| §5 Composición | 8 |
| §6 Voz, claims, promesas, vetos | 1, 8 |
| §7 Superficies, dominio canónico | 6 (OG), 7 (metaetiquetas), 8 (tabla) |
| §8 Artefactos y reproducibilidad | 4, 5, 6 |
| §9 Comprobación determinista, 4 reglas | 2 (regla 1), 3 (reglas 2–4) |
| §10 Entregables | todas |
| §11 Riesgos: contorno de letras | Resuelto en 4 — hay acceso a la TTF, los glifos son reales |
| §11 Riesgos: modo oscuro, doble audiencia | 8 (sección Pendientes) |
