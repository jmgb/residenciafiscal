# Frontend chatbot residenciafiscal.org — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir en `frontend/` una SPA React desplegable en Netlify que ofrezca un chatbot sobre las 106 sentencias de residencia fiscal, con el motor de conversación resuelto por un stub que implementa la interfaz definitiva del backend RAG.

**Architecture:** Proyecto Vite independiente dentro del repositorio Python existente. Shell de dos columnas (sidebar colapsable + barra fina + área de contenido) portado del área privada de Presupuestor, con una vista de chat propia. Toda la comunicación con el «cerebro» pasa por un único módulo `src/lib/chat-engine.ts`, de modo que conectar el backend real sea sustituir una implementación sin tocar la UI. El historial vive en localStorage; no hay autenticación ni backend.

**Tech Stack:** Vite 7, React 19, TypeScript 5.9, Tailwind CSS v4 (`@tailwindcss/vite`), Radix UI (dialog, tooltip, slot), lucide-react, react-router-dom 7, react-markdown + remark-gfm, zustand 5, Vitest 3 + Testing Library, Biome (lint/format).

**Spec de referencia:** `docs/superpowers/specs/2026-07-29-frontend-chatbot-design.md`

**Repositorio de origen para los ficheros copiados:** `/home/ubuntu/ai_projects/presupuestor/frontend/`

---

## Estructura de ficheros

Todo lo nuevo cuelga de `frontend/`, salvo `netlify.toml` y las actualizaciones de documentación, que van en la raíz.

| Fichero | Responsabilidad |
|---|---|
| `netlify.toml` | Configuración de build, redirect SPA y cabeceras (raíz del repo) |
| `frontend/package.json` | Dependencias y scripts |
| `frontend/vite.config.ts` | Build, alias `@`, configuración de Vitest |
| `frontend/tsconfig.json`, `tsconfig.node.json` | TypeScript |
| `frontend/biome.json` | Lint y formato |
| `frontend/index.html` | Documento raíz, metadatos SEO |
| `frontend/scripts/build-corpus.mjs` | Genera `public/data/corpus.json` desde `output/*.jsonl` |
| `frontend/src/index.css` | Tokens de diseño Tailwind v4 (paleta jurídica) |
| `frontend/src/main.tsx` | Punto de entrada React |
| `frontend/src/App.tsx` | Router y composición del layout |
| `frontend/src/types/chat.ts` | `ChatMessage`, `ChatSource`, `ChatChunk`, `CorpusEntry` |
| `frontend/src/shared/lib/utils.ts` | `cn` |
| `frontend/src/shared/components/ui/*` | Primitivos: button, textarea, sheet, separator, tooltip |
| `frontend/src/lib/corpus.ts` | Carga y cachea `corpus.json` |
| `frontend/src/lib/chat-engine.ts` | Interfaz `ChatEngine` + selección de implementación |
| `frontend/src/lib/chat-engine.stub.ts` | Implementación simulada con streaming y fuentes reales |
| `frontend/src/stores/useConversations.ts` | Historial de conversaciones (zustand + localStorage) |
| `frontend/src/components/layout/AppLayout.tsx` | Shell de dos columnas |
| `frontend/src/components/layout/AppSidebar.tsx` | Sidebar: marca, nueva consulta, historial, pie |
| `frontend/src/components/layout/MobileNavigation.tsx` | Drawer con el mismo contenido |
| `frontend/src/components/layout/SidebarContent.tsx` | Contenido compartido sidebar/drawer |
| `frontend/src/components/layout/useSidebarCollapsed.ts` | Preferencia de colapso persistida |
| `frontend/src/components/chat/ChatView.tsx` | Contenedor de la conversación |
| `frontend/src/components/chat/ChatWelcome.tsx` | Bienvenida + prompts sugeridos |
| `frontend/src/components/chat/ChatBubble.tsx` | Burbuja de mensaje |
| `frontend/src/components/chat/ChatMessageContent.tsx` | Render markdown |
| `frontend/src/components/chat/ChatSources.tsx` | Panel de fuentes citadas |
| `frontend/src/components/chat/ChatComposer.tsx` | Textarea + envío + detener |
| `frontend/src/pages/MetodologiaPage.tsx` | Página estática de método y corpus |
| `frontend/tests/*` | Suites de Vitest |

**Desviación respecto a la spec §5:** la spec preveía portar `ChatPanelFrame` recortado. En la práctica su única responsabilidad aquí (contenedor con scroll de mensajes + composer anclado) cabe en `ChatView`, que además necesita ese scroll para el autoscroll. Portar el fichero aparte solo añadiría una capa vacía, así que `ChatView` lo absorbe. `ChatPanelHeader` no se porta: la cabecera la aporta la barra fina del `AppLayout`.

---

## Task 1: Andamiaje del proyecto

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/biome.json`
- Create: `frontend/.gitignore`
- Create: `frontend/src/vite-env.d.ts`

- [ ] **Step 1: Crear `frontend/package.json`**

```json
{
  "name": "residenciafiscal-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "engines": {
    "node": ">=24"
  },
  "description": "residenciafiscal.org - Chatbot sobre jurisprudencia de residencia fiscal (Art. 9 LIRPF)",
  "scripts": {
    "dev": "vite",
    "prebuild": "node scripts/build-corpus.mjs",
    "build": "tsc --noEmit && vite build",
    "preview": "vite preview",
    "lint": "biome check .",
    "format": "biome format --write .",
    "typecheck": "tsc --noEmit",
    "test": "vitest run",
    "test:watch": "vitest",
    "fast-check": "npm run lint && npm run typecheck && npm run test"
  },
  "dependencies": {
    "@radix-ui/react-dialog": "1.1.18",
    "@radix-ui/react-slot": "1.3.0",
    "@radix-ui/react-tooltip": "1.2.11",
    "class-variance-authority": "0.7.1",
    "clsx": "2.1.1",
    "lucide-react": "1.23.0",
    "react": "19.2.7",
    "react-dom": "19.2.7",
    "react-markdown": "10.1.0",
    "react-router-dom": "7.18.1",
    "remark-gfm": "4.0.1",
    "tailwind-merge": "3.6.0",
    "zustand": "5.0.14"
  },
  "devDependencies": {
    "@biomejs/biome": "2.5.2",
    "@tailwindcss/vite": "4.3.2",
    "@testing-library/dom": "10.4.1",
    "@testing-library/jest-dom": "6.9.1",
    "@testing-library/react": "16.3.2",
    "@testing-library/user-event": "14.6.1",
    "@types/node": "24.13.1",
    "@types/react": "19.2.17",
    "@types/react-dom": "19.2.3",
    "@vitejs/plugin-react": "5.1.4",
    "jsdom": "29.1.1",
    "tailwindcss": "4.3.2",
    "typescript": "5.9.3",
    "vite": "7.3.1",
    "vitest": "3.2.4"
  }
}
```

- [ ] **Step 2: Crear `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": false,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"],
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src", "tests"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 3: Crear `frontend/tsconfig.node.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2023"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "noEmit": true,
    "types": ["node"]
  },
  "include": ["vite.config.ts", "scripts/**/*.mjs"]
}
```

- [ ] **Step 4: Crear `frontend/vite.config.ts`**

```ts
/// <reference types="vitest/config" />
import path from 'node:path';
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '127.0.0.1',
    port: 5174,
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.ts'],
    include: ['tests/**/*.test.{ts,tsx}'],
  },
});
```

- [ ] **Step 5: Crear `frontend/index.html`**

```html
<!doctype html>
<html lang="es">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Residencia Fiscal — Consulta la jurisprudencia del art. 9 LIRPF</title>
    <meta
      name="description"
      content="Consulta en lenguaje natural 106 sentencias del Tribunal Supremo y la Audiencia Nacional sobre residencia fiscal de personas físicas en España."
    />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap"
      rel="stylesheet"
    />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 6: Crear `frontend/src/vite-env.d.ts`**

```ts
/// <reference types="vite/client" />
```

- [ ] **Step 7: Crear `frontend/biome.json`**

```json
{
  "$schema": "https://biomejs.dev/schemas/2.5.2/schema.json",
  "files": {
    "includes": ["src/**", "tests/**", "scripts/**"]
  },
  "formatter": {
    "enabled": true,
    "indentStyle": "space",
    "indentWidth": 2,
    "lineWidth": 100
  },
  "javascript": {
    "formatter": {
      "quoteStyle": "single",
      "jsxQuoteStyle": "single",
      "semicolons": "always",
      "trailingCommas": "es5"
    }
  },
  "linter": {
    "enabled": true,
    "rules": {
      "recommended": true
    }
  },
  "assist": {
    "actions": {
      "source": {
        "organizeImports": "on"
      }
    }
  }
}
```

- [ ] **Step 8: Crear `frontend/.gitignore`**

```
node_modules
dist
coverage
.netlify
public/data/corpus.json
*.local
```

- [ ] **Step 9: Instalar dependencias**

Run: `cd frontend && npm install`
Expected: se crea `node_modules/` y `package-lock.json` sin errores de resolución.

- [ ] **Step 10: Commit**

```bash
cd /home/ubuntu/ai_projects/residenciafiscal
git add frontend/package.json frontend/package-lock.json frontend/tsconfig.json \
  frontend/tsconfig.node.json frontend/vite.config.ts frontend/index.html \
  frontend/biome.json frontend/.gitignore frontend/src/vite-env.d.ts
git commit -m "chore(frontend): andamiaje Vite + React + TypeScript"
```

---

## Task 2: Tokens de diseño y utilidades

**Files:**
- Create: `frontend/src/index.css`
- Create: `frontend/src/shared/lib/utils.ts`
- Create: `frontend/public/favicon.svg`

La paleta cambia respecto a Presupuestor (spec §6): primario azul pizarra `#1e3a5f`, acento ámbar, sin la escala `construction`.

- [ ] **Step 1: Crear `frontend/src/shared/lib/utils.ts`**

```ts
import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 2: Crear `frontend/src/index.css`**

```css
@import 'tailwindcss';

@theme {
  /* Tipografías duales */
  --font-heading: 'Space Grotesk', system-ui, sans-serif;
  --font-sans: 'Inter', system-ui, sans-serif;

  /* Base */
  --color-background: #ffffff;
  --color-foreground: #0f172a;
  --color-card: #ffffff;
  --color-card-foreground: #0f172a;
  --color-popover: #ffffff;
  --color-popover-foreground: #0f172a;

  /* Primario — azul pizarra jurídico */
  --color-primary: #1e3a5f;
  --color-primary-foreground: #f8fafc;
  --color-primary-50: #f2f6fa;
  --color-primary-100: #e2ebf4;
  --color-primary-200: #c5d7e9;
  --color-primary-300: #9bb9d6;
  --color-primary-400: #6892bd;
  --color-primary-500: #43719f;
  --color-primary-600: #2f5580;
  --color-primary-700: #1e3a5f;
  --color-primary-800: #18304e;
  --color-primary-900: #14273f;
  --color-primary-950: #0c1826;

  /* Acento — ámbar sobrio para citas y destacados */
  --color-accent: #fffbeb;
  --color-accent-foreground: #78350f;
  --color-accent-500: #d97706;
  --color-accent-600: #b45309;

  /* Secundario y neutros fríos */
  --color-secondary: #f1f5f9;
  --color-secondary-foreground: #1e293b;
  --color-muted: #f1f5f9;
  --color-muted-foreground: #64748b;
  --color-border: #e2e8f0;
  --color-input: #e2e8f0;
  --color-ring: #1e3a5f;

  /* Estados */
  --color-success: #15803d;
  --color-success-foreground: #ffffff;
  --color-warning: #b45309;
  --color-warning-foreground: #ffffff;
  --color-destructive: #b91c1c;
  --color-destructive-foreground: #ffffff;

  /* Sidebar */
  --color-sidebar: #f8fafc;
  --color-sidebar-foreground: #0f172a;
  --color-sidebar-accent: #e2ebf4;
  --color-sidebar-accent-foreground: #1e3a5f;
  --color-sidebar-border: #e2e8f0;
  --color-sidebar-ring: #1e3a5f;
}

@layer base {
  * {
    border-color: var(--color-border);
  }

  html {
    -webkit-text-size-adjust: 100%;
  }

  body {
    margin: 0;
    background-color: var(--color-background);
    color: var(--color-foreground);
    font-family: var(--font-sans);
    -webkit-font-smoothing: antialiased;
  }

  h1,
  h2,
  h3,
  h4 {
    font-family: var(--font-heading);
  }

  img,
  video {
    max-width: 100%;
    height: auto;
  }
}

@layer components {
  /* Utilidades compartidas por los primitivos portados de Presupuestor.
     `button.tsx` las referencia por nombre, así que deben existir. */
  .control-focus {
    @apply focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2;
  }

  .control-disabled {
    @apply disabled:cursor-not-allowed disabled:opacity-50 data-[disabled]:pointer-events-none data-[disabled]:opacity-50;
  }

  .control-press {
    @apply active:scale-[0.98];
  }
}
```

- [ ] **Step 3: Crear `frontend/public/favicon.svg`**

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <rect width="32" height="32" rx="7" fill="#1e3a5f"/>
  <path d="M9 22V10h5.6c2.5 0 4 1.3 4 3.4 0 1.6-.9 2.7-2.4 3.1L19.6 22h-3.1l-2.9-4.9h-1.8V22H9zm2.8-7.1h2.4c1.1 0 1.7-.5 1.7-1.4s-.6-1.4-1.7-1.4h-2.4v2.8z" fill="#fff"/>
  <rect x="20.5" y="9.5" width="2.2" height="13" rx="1.1" fill="#d97706"/>
</svg>
```

- [ ] **Step 4: Verificar que Tailwind compila**

Run: `cd frontend && npx vite build --mode development 2>&1 | tail -5`
Expected: falla con `Could not resolve entry module` o similar porque `src/main.tsx` aún no existe. Eso confirma que la configuración de Vite se carga; el CSS se validará en la Task 9. Si el error menciona `@apply` o `@theme`, la sintaxis de Tailwind v4 está mal y hay que corregirla antes de seguir.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/index.css frontend/src/shared/lib/utils.ts frontend/public/favicon.svg
git commit -m "feat(frontend): tokens de diseño con paleta jurídica"
```

---

## Task 3: Primitivos de UI portados

Se copian verbatim desde Presupuestor y se ajusta la ruta de importación de `cn`. Son cinco: `button`, `textarea`, `sheet`, `separator`, `tooltip`. Todos dependen únicamente de `cn`, `class-variance-authority` y Radix; ninguno arrastra MUI, auth ni stores.

**Files:**
- Create: `frontend/src/shared/components/ui/button.tsx`
- Create: `frontend/src/shared/components/ui/textarea.tsx`
- Create: `frontend/src/shared/components/ui/sheet.tsx`
- Create: `frontend/src/shared/components/ui/separator.tsx`
- Create: `frontend/src/shared/components/ui/tooltip.tsx`

- [ ] **Step 1: Copiar los cinco ficheros**

```bash
cd /home/ubuntu/ai_projects/residenciafiscal
SRC=/home/ubuntu/ai_projects/presupuestor/frontend/src/shared/components/ui
mkdir -p frontend/src/shared/components/ui
cp "$SRC/button.tsx" "$SRC/textarea.tsx" "$SRC/sheet.tsx" \
   "$SRC/separator.tsx" "$SRC/tooltip.tsx" frontend/src/shared/components/ui/
```

- [ ] **Step 2: Verificar que todos los tokens que usa `button.tsx` existen**

`button.tsx` declara variantes que referencian tokens de color (`bg-warning`, `bg-destructive`, `from-primary-500`…). Todos están definidos en nuestro `index.css`, así que en principio **no hay que tocar nada**. Confirmarlo: verificar que las clases referenciadas por `buttonVariants` (`bg-primary`, `bg-destructive`, `bg-warning`, `bg-secondary`, `bg-accent`, `from-primary-500`, `to-primary-600`, `primary-700`) tienen token equivalente en `index.css`:

Run: `cd frontend && grep -oE '\b(bg|text|from|to|border|ring)-[a-z0-9-]+' src/shared/components/ui/button.tsx | sort -u`
Expected: todas las familias que aparezcan (`primary`, `primary-500`, `primary-600`, `primary-700`, `destructive`, `warning`, `secondary`, `accent`, `input`, `background`) están definidas en `src/index.css`. Si alguna falta, añadir el token correspondiente a `@theme`.

- [ ] **Step 3: Verificar que los imports resuelven**

Los cinco ficheros importan `cn` como `from '../../lib/utils'`, que en nuestra estructura resuelve a `src/shared/lib/utils.ts`. Correcto, no hay que cambiar nada.

Run: `cd frontend && grep -n "from '" src/shared/components/ui/*.tsx | grep -v "@radix-ui\|lucide-react\|class-variance-authority\|'react'"`
Expected: solo líneas `from '../../lib/utils'`. Cualquier otra ruta (por ejemplo `@/lib/utils`) hay que corregirla a `'../../lib/utils'`.

- [ ] **Step 4: Comprobar tipos**

Run: `cd frontend && npx tsc --noEmit`
Expected: PASS sin errores.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/shared/components/ui
git commit -m "feat(frontend): primitivos de UI portados de Presupuestor"
```

---

## Task 4: Tipos de dominio

**Files:**
- Create: `frontend/src/types/chat.ts`

- [ ] **Step 1: Crear `frontend/src/types/chat.ts`**

```ts
/**
 * Tipos compartidos por el motor de chat, el store de conversaciones y la UI.
 *
 * `ChatEngine` es el contrato que hoy cumple el stub y que mañana cumplirá el
 * backend RAG real (Netlify Function, Supabase o VPS). Sustituir la
 * implementación no debe obligar a tocar nada fuera de `src/lib/`.
 */

/** Resultado del fallo, tal y como lo clasifica el pipeline Python. */
export type ResultadoFinal =
  | 'GANA_AEAT'
  | 'GANA_CONTRIBUYENTE'
  | 'PARCIAL'
  | 'RETROACCION'
  | 'INADMISION'
  | 'DESCONOCIDO';

/** Entrada del corpus ligero generado desde `output/analisis_*.jsonl`. */
export interface CorpusEntry {
  archivo: string;
  roj: string;
  ecli: string;
  organo: string;
  fecha: string;
  resultado: ResultadoFinal;
  criterioDecisivo: string[];
  esCasoResidencia: boolean;
}

/** Sentencia citada por una respuesta del asistente. */
export interface ChatSource extends CorpusEntry {
  /** Extracto mostrado al desplegar la fuente. */
  extracto: string;
}

export type ChatRole = 'user' | 'assistant';

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  /** ISO 8601. */
  createdAt: string;
  sources?: ChatSource[];
  /** true mientras se están recibiendo tokens. */
  isStreaming?: boolean;
}

/** Unidad de la respuesta en streaming. */
export type ChatChunk =
  | { type: 'token'; text: string }
  | { type: 'sources'; sources: ChatSource[] }
  | { type: 'done' };

export interface ChatEngine {
  askQuestion(messages: ChatMessage[], signal: AbortSignal): AsyncIterable<ChatChunk>;
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
}
```

- [ ] **Step 2: Comprobar tipos**

Run: `cd frontend && npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/chat.ts
git commit -m "feat(frontend): tipos de dominio del chat y del corpus"
```

---

## Task 5: Generación del corpus

El script lee el JSONL más reciente de `output/` y produce un JSON ligero. Se ordena por fecha de modificación porque los nombres usan formato `DDMMYYYY_HHMMSS`, que no ordena lexicográficamente.

**Files:**
- Create: `frontend/scripts/build-corpus.mjs`
- Test: manual (script de build, no código de aplicación)

- [ ] **Step 1: Crear `frontend/scripts/build-corpus.mjs`**

```js
#!/usr/bin/env node
/**
 * Genera `public/data/corpus.json` a partir del análisis más reciente del
 * pipeline Python (`output/analisis_*.jsonl`).
 *
 * Solo se publican metadatos ligeros: el JSONL completo (~900 KB con
 * razonamientos y pruebas) no se sirve al navegador.
 *
 * Se ejecuta en `prebuild`. Si no encuentra ningún JSONL, escribe un corpus
 * vacío y avisa, en lugar de romper el build: Netlify construye desde un clon
 * limpio donde `output/` puede no estar versionado.
 */
import { existsSync, mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const frontendDir = join(scriptDir, '..');
const outputDir = join(frontendDir, '..', 'output');
const targetDir = join(frontendDir, 'public', 'data');
const targetFile = join(targetDir, 'corpus.json');

const VALID_RESULTS = new Set([
  'GANA_AEAT',
  'GANA_CONTRIBUYENTE',
  'PARCIAL',
  'RETROACCION',
  'INADMISION',
]);

function findLatestJsonl() {
  if (!existsSync(outputDir)) return null;
  const candidates = readdirSync(outputDir)
    .filter((name) => name.startsWith('analisis_') && name.endsWith('.jsonl'))
    .map((name) => {
      const path = join(outputDir, name);
      return { path, mtime: statSync(path).mtimeMs };
    })
    .sort((a, b) => b.mtime - a.mtime);
  return candidates[0]?.path ?? null;
}

function toEntry(raw) {
  const ids = raw.identificadores ?? {};
  const resultado = VALID_RESULTS.has(raw.resultado_final) ? raw.resultado_final : 'DESCONOCIDO';
  const criterio = Array.isArray(raw.Criterio_decisivo)
    ? raw.Criterio_decisivo.filter((c) => typeof c === 'string')
    : [];
  return {
    archivo: raw.archivo ?? '',
    roj: ids.ROJ ?? '',
    ecli: ids.ECLI ?? '',
    organo: raw.organo ?? '',
    fecha: raw.fecha_resolucion ?? '',
    resultado,
    criterioDecisivo: criterio,
    esCasoResidencia: raw.es_caso_residencia_irpf === 'SI',
  };
}

function main() {
  mkdirSync(targetDir, { recursive: true });

  const source = findLatestJsonl();
  if (!source) {
    console.warn('[build-corpus] No se encontró ningún analisis_*.jsonl en output/. Corpus vacío.');
    writeFileSync(targetFile, '[]\n', 'utf8');
    return;
  }

  const entries = [];
  for (const line of readFileSync(source, 'utf8').split('\n')) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    try {
      entries.push(toEntry(JSON.parse(trimmed)));
    } catch {
      console.warn('[build-corpus] Línea JSON inválida omitida.');
    }
  }

  entries.sort((a, b) => b.fecha.localeCompare(a.fecha));
  writeFileSync(targetFile, `${JSON.stringify(entries)}\n`, 'utf8');
  console.log(`[build-corpus] ${entries.length} sentencias escritas en public/data/corpus.json`);
}

main();
```

- [ ] **Step 2: Ejecutar el script**

Run: `cd frontend && node scripts/build-corpus.mjs`
Expected: `[build-corpus] 106 sentencias escritas en public/data/corpus.json`

- [ ] **Step 3: Verificar la salida**

Run: `cd frontend && node -e "const c=require('./public/data/corpus.json'); console.log(c.length, JSON.stringify(c[0]))"`
Expected: `106` seguido de un objeto con `archivo`, `roj`, `ecli`, `organo`, `fecha`, `resultado`, `criterioDecisivo`, `esCasoResidencia`.

- [ ] **Step 4: Commit**

```bash
git add frontend/scripts/build-corpus.mjs
git commit -m "feat(frontend): script de generación del corpus ligero"
```

---

## Task 6: Motor de chat (stub) — TDD

**Files:**
- Create: `frontend/tests/setup.ts`
- Create: `frontend/tests/chat-engine.stub.test.ts`
- Create: `frontend/src/lib/chat-engine.stub.ts`
- Create: `frontend/src/lib/corpus.ts`
- Create: `frontend/src/lib/chat-engine.ts`

- [ ] **Step 1: Crear `frontend/tests/setup.ts`**

```ts
import '@testing-library/jest-dom/vitest';
```

- [ ] **Step 2: Escribir el test que falla**

Crear `frontend/tests/chat-engine.stub.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { createStubChatEngine, pickSources, STUB_TOPICS } from '@/lib/chat-engine.stub';
import type { ChatChunk, ChatMessage, CorpusEntry } from '@/types/chat';

const corpus: CorpusEntry[] = [
  {
    archivo: 'STS_107_2018.pdf',
    roj: 'STS 107/2018',
    ecli: 'ECLI:ES:TS:2018:107',
    organo: 'Tribunal Supremo. Sala de lo Contencioso-Administrativo',
    fecha: '2018-01-16',
    resultado: 'GANA_AEAT',
    criterioDecisivo: ['CRIT_183_DIAS'],
    esCasoResidencia: true,
  },
  {
    archivo: 'STS_3942_2021.pdf',
    roj: 'STS 3942/2021',
    ecli: 'ECLI:ES:TS:2021:3942',
    organo: 'Tribunal Supremo. Sala de lo Contencioso-Administrativo',
    fecha: '2021-11-04',
    resultado: 'GANA_CONTRIBUYENTE',
    criterioDecisivo: ['CRIT_CDI_TIEBREAKER'],
    esCasoResidencia: true,
  },
  {
    archivo: 'SAN_1071_2025.pdf',
    roj: 'SAN 1071/2025',
    ecli: 'ECLI:ES:AN:2025:1071',
    organo: 'Audiencia Nacional. Sala de lo Contencioso-Administrativo',
    fecha: '2025-02-18',
    resultado: 'PARCIAL',
    criterioDecisivo: ['CRIT_CENTRO_INTERESES_ECONOMICOS'],
    esCasoResidencia: true,
  },
  {
    archivo: 'STS_9999_2019.pdf',
    roj: 'STS 9999/2019',
    ecli: 'ECLI:ES:TS:2019:9999',
    organo: 'Tribunal Supremo. Sala de lo Contencioso-Administrativo',
    fecha: '2019-05-05',
    resultado: 'INADMISION',
    criterioDecisivo: [],
    esCasoResidencia: false,
  },
];

function userMessage(content: string): ChatMessage[] {
  return [{ id: 'm1', role: 'user', content, createdAt: '2026-07-29T10:00:00.000Z' }];
}

async function drain(iterable: AsyncIterable<ChatChunk>): Promise<ChatChunk[]> {
  const chunks: ChatChunk[] = [];
  for await (const chunk of iterable) chunks.push(chunk);
  return chunks;
}

describe('pickSources', () => {
  it('selecciona sentencias cuyo criterio decisivo coincide con el tema detectado', () => {
    const sources = pickSources('¿Cómo se computan los 183 días de permanencia?', corpus);
    expect(sources.map((s) => s.roj)).toContain('STS 107/2018');
  });

  it('detecta el tema de CDI y prioriza el tie-breaker', () => {
    const sources = pickSources('¿Cuándo se aplica el convenio de doble imposición?', corpus);
    expect(sources.map((s) => s.roj)).toContain('STS 3942/2021');
  });

  it('nunca devuelve sentencias fuera de alcance', () => {
    const sources = pickSources('cualquier cosa sin palabras clave', corpus);
    expect(sources.every((s) => s.esCasoResidencia)).toBe(true);
  });

  it('devuelve entre 2 y 4 fuentes aunque no haya coincidencias', () => {
    const sources = pickSources('pregunta genérica', corpus);
    expect(sources.length).toBeGreaterThanOrEqual(2);
    expect(sources.length).toBeLessThanOrEqual(4);
  });

  it('adjunta un extracto no vacío a cada fuente', () => {
    const sources = pickSources('183 días', corpus);
    expect(sources.every((s) => s.extracto.length > 0)).toBe(true);
  });

  it('con un corpus vacío devuelve una lista vacía', () => {
    expect(pickSources('183 días', [])).toEqual([]);
  });
});

describe('createStubChatEngine', () => {
  it('emite tokens, después fuentes y termina con done', async () => {
    const engine = createStubChatEngine(corpus, { tokenDelayMs: 0 });
    const chunks = await drain(engine.askQuestion(userMessage('¿Y los 183 días?'), new AbortController().signal));

    expect(chunks.filter((c) => c.type === 'token').length).toBeGreaterThan(0);
    expect(chunks.at(-1)).toEqual({ type: 'done' });

    const sourcesChunk = chunks.find((c) => c.type === 'sources');
    expect(sourcesChunk).toBeDefined();
  });

  it('el texto concatenado incluye el aviso de motor simulado', async () => {
    const engine = createStubChatEngine(corpus, { tokenDelayMs: 0 });
    const chunks = await drain(engine.askQuestion(userMessage('183 días'), new AbortController().signal));
    const text = chunks
      .filter((c): c is { type: 'token'; text: string } => c.type === 'token')
      .map((c) => c.text)
      .join('');

    expect(text.toLowerCase()).toContain('simulad');
  });

  it('deja de emitir cuando se aborta la señal', async () => {
    const controller = new AbortController();
    const engine = createStubChatEngine(corpus, { tokenDelayMs: 0 });
    const chunks: ChatChunk[] = [];

    for await (const chunk of engine.askQuestion(userMessage('183 días'), controller.signal)) {
      chunks.push(chunk);
      if (chunks.length === 3) controller.abort();
    }

    expect(chunks.length).toBeLessThan(20);
    expect(chunks.at(-1)).not.toEqual({ type: 'done' });
  });

  it('no emite nada si la señal ya viene abortada', async () => {
    const controller = new AbortController();
    controller.abort();
    const engine = createStubChatEngine(corpus, { tokenDelayMs: 0 });
    const chunks = await drain(engine.askQuestion(userMessage('183 días'), controller.signal));

    expect(chunks).toEqual([]);
  });

  it('cada tema declarado tiene una respuesta no vacía', () => {
    for (const topic of STUB_TOPICS) {
      expect(topic.answer.trim().length).toBeGreaterThan(0);
      expect(topic.keywords.length).toBeGreaterThan(0);
    }
  });
});
```

- [ ] **Step 3: Ejecutar el test para verificar que falla**

Run: `cd frontend && npx vitest run tests/chat-engine.stub.test.ts`
Expected: FAIL — `Failed to resolve import "@/lib/chat-engine.stub"`.

- [ ] **Step 4: Implementar `frontend/src/lib/chat-engine.stub.ts`**

```ts
/**
 * Implementación SIMULADA del motor de chat.
 *
 * Existe para poder construir y validar toda la interfaz antes de decidir el
 * backend RAG. Emite tokens con retardo para que el streaming, el indicador de
 * escritura y el botón de detener se comporten igual que con el motor real, y
 * cita sentencias REALES del corpus para que el panel de fuentes sea
 * representativo.
 *
 * Toda respuesta lleva un aviso explícito de que el contenido es simulado: no
 * puede confundirse con análisis jurídico real.
 */
import type { ChatChunk, ChatEngine, ChatMessage, ChatSource, CorpusEntry } from '@/types/chat';

const DISCLAIMER =
  '> **Respuesta simulada.** El motor de análisis todavía no está conectado. ' +
  'El texto siguiente es un ejemplo del formato de respuesta; las sentencias ' +
  'citadas sí son reales y provienen del corpus analizado.\n\n';

export interface StubTopic {
  id: string;
  keywords: string[];
  /** Criterios del pipeline con los que se emparejan las sentencias citadas. */
  criterios: string[];
  answer: string;
}

export const STUB_TOPICS: StubTopic[] = [
  {
    id: 'dias',
    keywords: ['183', 'dias', 'días', 'permanencia', 'computo', 'cómputo', 'estancia'],
    criterios: ['CRIT_183_DIAS', 'CRIT_AUSENCIAS_ESPORADICAS'],
    answer:
      'El cómputo de los **183 días** del art. 9.1.a) LIRPF es el campo de batalla principal: ' +
      'aparece como criterio decisivo en la mayoría de los casos analizados.\n\n' +
      'Los tribunales valoran hechos verificables por encima de formalidades:\n\n' +
      '- **Presencia física acreditada**: sellos de pasaporte, tarjetas de embarque y registros ' +
      'de entrada/salida, siempre que cubran el ejercicio completo y no periodos sueltos.\n' +
      '- **Consumos con patrón continuo**: extractos bancarios y de tarjetas agregados por mes, ' +
      'no tickets aislados.\n' +
      '- **Coherencia temporal**: las contradicciones entre lo alegado y los consumos pesan más ' +
      'que cualquier certificado.\n\n' +
      'La carga de la prueba recae normalmente en quien alega la excepción a la permanencia.',
  },
  {
    id: 'ausencias',
    keywords: ['ausencia', 'ausencias', 'esporadic', 'esporádic', 'temporal'],
    criterios: ['CRIT_AUSENCIAS_ESPORADICAS', 'CRIT_183_DIAS'],
    answer:
      'Las **ausencias esporádicas** del art. 9.1.a), segundo párrafo, LIRPF se computan como ' +
      'permanencia en España salvo que se acredite residencia fiscal en otro país.\n\n' +
      'La doctrina consolidada trata el concepto como **objetivo**: no depende de la intención ' +
      'de volver ni de la duración de la ausencia, sino del dato fáctico de dónde se ha estado ' +
      'y de si existe un certificado de residencia fiscal del otro Estado.\n\n' +
      'Sin ese certificado, las ausencias suman a la permanencia en España.',
  },
  {
    id: 'cdi',
    keywords: ['cdi', 'convenio', 'doble imposicion', 'doble imposición', 'tiebreaker', 'ocde', 'desempate'],
    criterios: ['CRIT_CDI_TIEBREAKER'],
    answer:
      'El **tie-breaker del art. 4 del Modelo OCDE** solo entra en juego cuando existe doble ' +
      'residencia real: ambos Estados consideran residente al contribuyente conforme a su ' +
      'normativa interna.\n\n' +
      'El orden de aplicación es escalonado y no se salta pasos:\n\n' +
      '1. Vivienda permanente a disposición.\n' +
      '2. Centro de intereses vitales.\n' +
      '3. Residencia habitual.\n' +
      '4. Nacionalidad.\n' +
      '5. Procedimiento amistoso.\n\n' +
      'Un certificado de residencia fiscal emitido por el otro Estado es condición para abrir ' +
      'el convenio, pero no resuelve por sí solo el desempate.',
  },
  {
    id: 'intereses',
    keywords: ['interes', 'interés', 'intereses', 'economic', 'económic', 'nucleo', 'núcleo', 'vital', 'centro'],
    criterios: ['CRIT_CENTRO_INTERESES_ECONOMICOS', 'CRIT_CENTRO_INTERESES_VITALES'],
    answer:
      'El **centro de intereses** (art. 9.1.b) LIRPF) entra cuando el cómputo de días no es ' +
      'concluyente o hay doble anclaje.\n\n' +
      'En la vertiente **económica** se compara la localización de las fuentes de renta y del ' +
      'patrimonio gestionado, no solo dónde se tributa. En la vertiente **vital** pesan los ' +
      'vínculos personales y familiares estables.\n\n' +
      'Es un criterio de segunda línea: rara vez decide solo, pero refuerza o desmonta la ' +
      'versión construida sobre la presencia física.',
  },
  {
    id: 'vivienda',
    keywords: ['vivienda', 'domicilio', 'suministro', 'consumo', 'luz', 'agua', 'alquiler'],
    criterios: ['CRIT_183_DIAS', 'CRIT_CENTRO_INTERESES_VITALES'],
    answer:
      'La **vivienda y su uso efectivo** es la categoría probatoria con mejor rendimiento para ' +
      'la Administración en el corpus analizado.\n\n' +
      'Lo que convence a los tribunales no es la titularidad, sino la combinación de:\n\n' +
      '- contrato (propiedad o alquiler) **más** facturas de suministros;\n' +
      '- consumos con coherencia mes a mes;\n' +
      '- contradicciones detectadas, como una vivienda declarada como alquilada a terceros con ' +
      'consumos incompatibles con esa cesión.\n\n' +
      'Disponer de vivienda sin prueba de uso efectivo se admite como indicio, pero raramente decide.',
  },
  {
    id: 'familia',
    keywords: ['familia', 'conyuge', 'cónyuge', 'hijos', 'menores', 'presuncion', 'presunción'],
    criterios: ['CRIT_PRESUNCION_FAMILIA', 'CRIT_CENTRO_INTERESES_VITALES'],
    answer:
      'La **presunción del art. 9.1.b), segundo párrafo, LIRPF** opera cuando el cónyuge no ' +
      'separado legalmente y los hijos menores dependientes residen habitualmente en España.\n\n' +
      'Es una presunción **iuris tantum**: admite prueba en contrario, y desvirtuarla exige ' +
      'acreditar residencia efectiva en otro Estado, no simplemente alegar separación de hecho ' +
      'o desplazamiento laboral.',
  },
];

const FALLBACK_ANSWER =
  'El corpus analizado reúne **106 resoluciones** del Tribunal Supremo y de la Audiencia ' +
  'Nacional sobre residencia fiscal de personas físicas (2015-2025).\n\n' +
  'Puedes preguntar por los criterios del art. 9 LIRPF (permanencia de 183 días, ausencias ' +
  'esporádicas, centro de intereses económicos o vitales, presunción familiar), por las reglas ' +
  'de desempate del art. 4 del Modelo OCDE, o por qué pruebas concretas admiten y rechazan los ' +
  'tribunales.';

const EXTRACTO_POR_RESULTADO: Record<string, string> = {
  GANA_AEAT:
    'El tribunal confirma la residencia fiscal en España y desestima el recurso del contribuyente.',
  GANA_CONTRIBUYENTE:
    'El tribunal estima el recurso: la Administración no acreditó suficientemente la residencia en España.',
  PARCIAL: 'Estimación parcial: el tribunal acoge algunos motivos y rechaza otros.',
  RETROACCION: 'El tribunal ordena retrotraer actuaciones por defectos en la instrucción.',
  INADMISION: 'Recurso inadmitido sin entrar en el fondo del asunto.',
  DESCONOCIDO: 'Resolución del corpus analizado sobre residencia fiscal de personas físicas.',
};

/** Minúsculas sin acentos, para comparar palabras clave de forma robusta. */
function normalize(text: string): string {
  return text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');
}

function detectTopic(question: string): StubTopic | null {
  const haystack = normalize(question);
  let best: { topic: StubTopic; hits: number } | null = null;

  for (const topic of STUB_TOPICS) {
    const hits = topic.keywords.filter((kw) => haystack.includes(normalize(kw))).length;
    if (hits > 0 && (!best || hits > best.hits)) best = { topic, hits };
  }

  return best?.topic ?? null;
}

function toSource(entry: CorpusEntry): ChatSource {
  return {
    ...entry,
    extracto: EXTRACTO_POR_RESULTADO[entry.resultado] ?? EXTRACTO_POR_RESULTADO.DESCONOCIDO,
  };
}

/**
 * Elige entre 2 y 4 sentencias del corpus relevantes para la pregunta.
 * Prioriza las que tienen como criterio decisivo alguno del tema detectado;
 * completa con las más recientes dentro de alcance.
 */
export function pickSources(question: string, corpus: CorpusEntry[]): ChatSource[] {
  const inScope = corpus.filter((entry) => entry.esCasoResidencia);
  if (inScope.length === 0) return [];

  const topic = detectTopic(question);
  const matching = topic
    ? inScope.filter((entry) => entry.criterioDecisivo.some((c) => topic.criterios.includes(c)))
    : [];

  const selected: CorpusEntry[] = [...matching];
  for (const entry of inScope) {
    if (selected.length >= 4) break;
    if (!selected.includes(entry)) selected.push(entry);
  }

  return selected.slice(0, 4).map(toSource);
}

export interface StubEngineOptions {
  /** Retardo entre tokens. 0 en tests para que corran instantáneos. */
  tokenDelayMs?: number;
}

const DEFAULT_TOKEN_DELAY_MS = 18;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** Trocea el texto en unidades de token (palabra + espacio) para el streaming. */
function tokenize(text: string): string[] {
  return text.match(/\S+\s*/g) ?? [];
}

export function createStubChatEngine(
  corpus: CorpusEntry[],
  options: StubEngineOptions = {}
): ChatEngine {
  const tokenDelayMs = options.tokenDelayMs ?? DEFAULT_TOKEN_DELAY_MS;

  return {
    async *askQuestion(messages: ChatMessage[], signal: AbortSignal): AsyncIterable<ChatChunk> {
      if (signal.aborted) return;

      const question = [...messages].reverse().find((m) => m.role === 'user')?.content ?? '';
      const topic = detectTopic(question);
      const body = topic?.answer ?? FALLBACK_ANSWER;

      for (const token of tokenize(DISCLAIMER + body)) {
        if (signal.aborted) return;
        if (tokenDelayMs > 0) await sleep(tokenDelayMs);
        if (signal.aborted) return;
        yield { type: 'token', text: token };
      }

      if (signal.aborted) return;
      const sources = pickSources(question, corpus);
      if (sources.length > 0) yield { type: 'sources', sources };

      if (signal.aborted) return;
      yield { type: 'done' };
    },
  };
}
```

- [ ] **Step 5: Ejecutar el test para verificar que pasa**

Run: `cd frontend && npx vitest run tests/chat-engine.stub.test.ts`
Expected: PASS, 12 tests.

- [ ] **Step 6: Crear `frontend/src/lib/corpus.ts`**

```ts
import type { CorpusEntry } from '@/types/chat';

/**
 * Carga el corpus ligero generado en build time. Se cachea en memoria: el
 * fichero es inmutable durante la vida de la página.
 *
 * Un fallo de red o un JSON corrupto degradan a corpus vacío en lugar de
 * romper la aplicación: el chat sigue respondiendo, solo que sin citas.
 */
let cache: Promise<CorpusEntry[]> | null = null;

export function loadCorpus(): Promise<CorpusEntry[]> {
  if (!cache) {
    cache = fetch('/data/corpus.json')
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => (Array.isArray(data) ? (data as CorpusEntry[]) : []))
      .catch(() => []);
  }
  return cache;
}

/** Solo para tests: invalida la caché entre casos. */
export function resetCorpusCache(): void {
  cache = null;
}
```

- [ ] **Step 7: Crear `frontend/src/lib/chat-engine.ts`**

```ts
/**
 * Punto único de selección del motor de chat.
 *
 * Hoy solo existe el stub. Cuando llegue el backend RAG, aquí se decidirá
 * entre implementaciones y `chatEngineMode` pasará a `'live'`, lo que apaga
 * automáticamente el aviso de contenido simulado en la UI.
 */
import { createStubChatEngine } from '@/lib/chat-engine.stub';
import { loadCorpus } from '@/lib/corpus';
import type { ChatChunk, ChatEngine, ChatMessage } from '@/types/chat';

export type ChatEngineMode = 'stub' | 'live';

export const chatEngineMode: ChatEngineMode = 'stub';

export const chatEngine: ChatEngine = {
  async *askQuestion(messages: ChatMessage[], signal: AbortSignal): AsyncIterable<ChatChunk> {
    const corpus = await loadCorpus();
    yield* createStubChatEngine(corpus).askQuestion(messages, signal);
  },
};
```

- [ ] **Step 8: Ejecutar toda la suite y comprobar tipos**

Run: `cd frontend && npx vitest run && npx tsc --noEmit`
Expected: PASS en ambos.

- [ ] **Step 9: Commit**

```bash
git add frontend/tests/setup.ts frontend/tests/chat-engine.stub.test.ts \
  frontend/src/lib/chat-engine.stub.ts frontend/src/lib/corpus.ts frontend/src/lib/chat-engine.ts
git commit -m "feat(frontend): motor de chat simulado con streaming y citas reales"
```

---

## Task 7: Store de conversaciones — TDD

**Files:**
- Create: `frontend/tests/useConversations.test.ts`
- Create: `frontend/src/stores/useConversations.ts`

- [ ] **Step 1: Escribir el test que falla**

Crear `frontend/tests/useConversations.test.ts`:

```ts
import { beforeEach, describe, expect, it } from 'vitest';
import {
  CONVERSATIONS_STORAGE_KEY,
  deriveTitle,
  useConversations,
} from '@/stores/useConversations';

function reset() {
  window.localStorage.clear();
  useConversations.setState({ conversations: [] });
}

describe('deriveTitle', () => {
  it('usa el primer mensaje del usuario recortado', () => {
    expect(deriveTitle('¿Cómo se computan los 183 días?')).toBe('¿Cómo se computan los 183 días?');
  });

  it('trunca los títulos largos añadiendo puntos suspensivos', () => {
    const long = 'a'.repeat(80);
    const title = deriveTitle(long);
    expect(title.length).toBeLessThanOrEqual(61);
    expect(title.endsWith('…')).toBe(true);
  });

  it('usa un título por defecto cuando el texto está vacío', () => {
    expect(deriveTitle('   ')).toBe('Consulta sin título');
  });

  it('colapsa los saltos de línea', () => {
    expect(deriveTitle('primera\nsegunda')).toBe('primera segunda');
  });
});

describe('useConversations', () => {
  beforeEach(reset);

  it('crea una conversación con id y sin mensajes', () => {
    const id = useConversations.getState().createConversation();
    const conversation = useConversations.getState().getConversation(id);

    expect(conversation).toBeDefined();
    expect(conversation?.messages).toEqual([]);
    expect(useConversations.getState().conversations).toHaveLength(1);
  });

  it('añade mensajes y actualiza el título con el primero del usuario', () => {
    const store = useConversations.getState();
    const id = store.createConversation();

    store.appendMessage(id, {
      id: 'm1',
      role: 'user',
      content: '¿Qué son las ausencias esporádicas?',
      createdAt: '2026-07-29T10:00:00.000Z',
    });

    const conversation = useConversations.getState().getConversation(id);
    expect(conversation?.messages).toHaveLength(1);
    expect(conversation?.title).toBe('¿Qué son las ausencias esporádicas?');
  });

  it('no cambia el título con mensajes posteriores', () => {
    const store = useConversations.getState();
    const id = store.createConversation();

    store.appendMessage(id, {
      id: 'm1',
      role: 'user',
      content: 'primera pregunta',
      createdAt: '2026-07-29T10:00:00.000Z',
    });
    store.appendMessage(id, {
      id: 'm2',
      role: 'user',
      content: 'segunda pregunta',
      createdAt: '2026-07-29T10:01:00.000Z',
    });

    expect(useConversations.getState().getConversation(id)?.title).toBe('primera pregunta');
  });

  it('actualiza un mensaje existente por id', () => {
    const store = useConversations.getState();
    const id = store.createConversation();

    store.appendMessage(id, {
      id: 'a1',
      role: 'assistant',
      content: '',
      createdAt: '2026-07-29T10:00:00.000Z',
      isStreaming: true,
    });
    store.updateMessage(id, 'a1', { content: 'respuesta completa', isStreaming: false });

    const message = useConversations.getState().getConversation(id)?.messages[0];
    expect(message?.content).toBe('respuesta completa');
    expect(message?.isStreaming).toBe(false);
  });

  it('borra una conversación', () => {
    const store = useConversations.getState();
    const id = store.createConversation();
    store.deleteConversation(id);

    expect(useConversations.getState().conversations).toHaveLength(0);
    expect(useConversations.getState().getConversation(id)).toBeUndefined();
  });

  it('ordena las conversaciones por actualización descendente', async () => {
    const store = useConversations.getState();
    const first = store.createConversation();
    const second = store.createConversation();

    // `createConversation` deja la más reciente arriba; sin la espera, ambas
    // podrían compartir el mismo `updatedAt` al milisegundo y el orden no sería
    // determinista.
    expect(useConversations.getState().conversations[0].id).toBe(second);
    await new Promise((resolve) => setTimeout(resolve, 5));

    store.appendMessage(first, {
      id: 'm1',
      role: 'user',
      content: 'reactivo la primera',
      createdAt: '2026-07-29T11:00:00.000Z',
    });

    expect(useConversations.getState().conversations[0].id).toBe(first);
    expect(useConversations.getState().conversations[1].id).toBe(second);
  });

  it('persiste en localStorage bajo una clave versionada', () => {
    useConversations.getState().createConversation();
    expect(window.localStorage.getItem(CONVERSATIONS_STORAGE_KEY)).not.toBeNull();
  });

  it('ignora operaciones sobre una conversación inexistente', () => {
    const store = useConversations.getState();
    expect(() =>
      store.appendMessage('no-existe', {
        id: 'm1',
        role: 'user',
        content: 'hola',
        createdAt: '2026-07-29T10:00:00.000Z',
      })
    ).not.toThrow();
    expect(useConversations.getState().conversations).toHaveLength(0);
  });
});
```

- [ ] **Step 2: Ejecutar el test para verificar que falla**

Run: `cd frontend && npx vitest run tests/useConversations.test.ts`
Expected: FAIL — `Failed to resolve import "@/stores/useConversations"`.

- [ ] **Step 3: Implementar `frontend/src/stores/useConversations.ts`**

```ts
/**
 * Historial de conversaciones, persistido en localStorage.
 *
 * No hay cuentas ni backend: el historial es local al navegador. La clave está
 * VERSIONADA para poder cambiar la forma de los datos sin dejar al usuario con
 * un store corrupto.
 */
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import type { ChatMessage, Conversation } from '@/types/chat';

export const CONVERSATIONS_STORAGE_KEY = 'rf.conversations.v1';

const TITLE_MAX_LENGTH = 60;
const DEFAULT_TITLE = 'Consulta sin título';

export function deriveTitle(content: string): string {
  const flat = content.replace(/\s+/g, ' ').trim();
  if (!flat) return DEFAULT_TITLE;
  if (flat.length <= TITLE_MAX_LENGTH) return flat;
  return `${flat.slice(0, TITLE_MAX_LENGTH)}…`;
}

function newId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return crypto.randomUUID();
  return `id-${Math.random().toString(36).slice(2)}-${Date.now()}`;
}

function byUpdatedDesc(a: Conversation, b: Conversation): number {
  return b.updatedAt.localeCompare(a.updatedAt);
}

interface ConversationsState {
  conversations: Conversation[];
  createConversation: () => string;
  deleteConversation: (id: string) => void;
  getConversation: (id: string) => Conversation | undefined;
  appendMessage: (conversationId: string, message: ChatMessage) => void;
  updateMessage: (
    conversationId: string,
    messageId: string,
    patch: Partial<ChatMessage>
  ) => void;
}

export const useConversations = create<ConversationsState>()(
  persist(
    (set, get) => ({
      conversations: [],

      createConversation: () => {
        const now = new Date().toISOString();
        const conversation: Conversation = {
          id: newId(),
          title: DEFAULT_TITLE,
          createdAt: now,
          updatedAt: now,
          messages: [],
        };
        set((state) => ({ conversations: [conversation, ...state.conversations] }));
        return conversation.id;
      },

      deleteConversation: (id) => {
        set((state) => ({ conversations: state.conversations.filter((c) => c.id !== id) }));
      },

      getConversation: (id) => get().conversations.find((c) => c.id === id),

      appendMessage: (conversationId, message) => {
        set((state) => {
          const conversations = state.conversations.map((conversation) => {
            if (conversation.id !== conversationId) return conversation;

            const isFirstUserMessage =
              message.role === 'user' && !conversation.messages.some((m) => m.role === 'user');

            return {
              ...conversation,
              title: isFirstUserMessage ? deriveTitle(message.content) : conversation.title,
              updatedAt: new Date().toISOString(),
              messages: [...conversation.messages, message],
            };
          });
          return { conversations: [...conversations].sort(byUpdatedDesc) };
        });
      },

      updateMessage: (conversationId, messageId, patch) => {
        set((state) => ({
          conversations: state.conversations.map((conversation) => {
            if (conversation.id !== conversationId) return conversation;
            return {
              ...conversation,
              messages: conversation.messages.map((message) =>
                message.id === messageId ? { ...message, ...patch } : message
              ),
            };
          }),
        }));
      },
    }),
    {
      name: CONVERSATIONS_STORAGE_KEY,
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ conversations: state.conversations }),
    }
  )
);
```

- [ ] **Step 4: Ejecutar el test para verificar que pasa**

Run: `cd frontend && npx vitest run tests/useConversations.test.ts`
Expected: PASS, 13 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend/tests/useConversations.test.ts frontend/src/stores/useConversations.ts
git commit -m "feat(frontend): store de conversaciones con persistencia local"
```

---

## Task 8: Shell del layout

Porta el shell del área privada de Presupuestor, retirando analytics, personas, banner de simulación e indicador offline.

**Files:**
- Create: `frontend/src/components/layout/useSidebarCollapsed.ts`
- Create: `frontend/src/components/layout/SidebarContent.tsx`
- Create: `frontend/src/components/layout/AppSidebar.tsx`
- Create: `frontend/src/components/layout/MobileNavigation.tsx`
- Create: `frontend/src/components/layout/AppLayout.tsx`
- Test: `frontend/tests/AppLayout.test.tsx`

- [ ] **Step 1: Crear `frontend/src/components/layout/useSidebarCollapsed.ts`**

```ts
import { useCallback, useEffect, useState } from 'react';

/**
 * Preferencia de colapso del sidebar (solo desktop), persistida bajo una clave
 * versionada. Cualquier fallo de storage degrada a EXPANDIDO: nunca rompe el shell.
 */
export const SIDEBAR_COLLAPSED_STORAGE_KEY = 'rf.sidebar-collapsed.v1';

function readInitialCollapsed(): boolean {
  try {
    return window.localStorage.getItem(SIDEBAR_COLLAPSED_STORAGE_KEY) === 'true';
  } catch {
    return false;
  }
}

export interface UseSidebarCollapsedResult {
  collapsed: boolean;
  toggle: () => void;
}

export function useSidebarCollapsed(): UseSidebarCollapsedResult {
  const [collapsed, setCollapsed] = useState<boolean>(readInitialCollapsed);

  useEffect(() => {
    try {
      window.localStorage.setItem(SIDEBAR_COLLAPSED_STORAGE_KEY, String(collapsed));
    } catch {
      // Persistir es best-effort.
    }
  }, [collapsed]);

  const toggle = useCallback(() => setCollapsed((prev) => !prev), []);

  return { collapsed, toggle };
}
```

- [ ] **Step 2: Crear `frontend/src/components/layout/SidebarContent.tsx`**

Contenido compartido por el sidebar de desktop y el drawer móvil, como en Presupuestor (una sola fuente de verdad).

```tsx
import { BookOpen, MessageSquarePlus, Scale, Trash2 } from 'lucide-react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { Button } from '@/shared/components/ui/button';
import { cn } from '@/shared/lib/utils';
import { useConversations } from '@/stores/useConversations';

export interface SidebarContentProps {
  /** Modo rail: solo iconos. Nunca se activa en el drawer móvil. */
  collapsed?: boolean;
  /** El drawer lo usa para cerrarse al navegar. */
  onNavigate?: () => void;
}

export function SidebarBrand({ collapsed = false, onNavigate }: SidebarContentProps) {
  return (
    <div
      className={cn(
        'flex shrink-0 items-center gap-3 border-b border-sidebar-border py-4',
        collapsed ? 'justify-center px-2' : 'px-4'
      )}
    >
      <Link
        to='/'
        onClick={onNavigate}
        aria-label='Ir al inicio'
        className='flex shrink-0 items-center rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring'
      >
        <span className='flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground'>
          <Scale className='h-5 w-5' aria-hidden='true' />
        </span>
      </Link>
      {!collapsed && (
        <div className='min-w-0'>
          <div className='truncate font-heading text-sm font-semibold'>Residencia Fiscal</div>
          <div className='truncate text-xs text-muted-foreground'>Art. 9 LIRPF</div>
        </div>
      )}
    </div>
  );
}

export function SidebarNavigation({ collapsed = false, onNavigate }: SidebarContentProps) {
  const navigate = useNavigate();
  const { conversationId } = useParams();
  const conversations = useConversations((state) => state.conversations);
  const deleteConversation = useConversations((state) => state.deleteConversation);

  // La conversación se crea de forma perezosa en `ChatView` con el primer
  // mensaje, así que «Nueva consulta» solo navega a la raíz.
  const handleNew = () => {
    onNavigate?.();
    navigate('/');
  };

  const handleDelete = (id: string) => {
    deleteConversation(id);
    if (id === conversationId) navigate('/');
  };

  return (
    <nav aria-label='Conversaciones' className={cn('flex flex-col gap-1', collapsed ? 'px-2' : 'px-3')}>
      <Button
        type='button'
        onClick={handleNew}
        className={cn('mb-2 w-full', collapsed && 'px-0')}
        aria-label='Nueva consulta'
        title='Nueva consulta'
      >
        <MessageSquarePlus className='h-4 w-4 shrink-0' aria-hidden='true' />
        {!collapsed && <span>Nueva consulta</span>}
      </Button>

      {!collapsed && conversations.length === 0 && (
        <p className='px-2 py-4 text-xs text-muted-foreground'>
          Todavía no has hecho ninguna consulta.
        </p>
      )}

      {!collapsed &&
        conversations.map((conversation) => {
          const isActive = conversation.id === conversationId;
          return (
            <div
              key={conversation.id}
              className={cn(
                'group flex items-center gap-1 rounded-lg pr-1 transition-colors',
                isActive ? 'bg-sidebar-accent text-sidebar-accent-foreground' : 'hover:bg-sidebar-accent/60'
              )}
            >
              <Link
                to={`/c/${conversation.id}`}
                onClick={onNavigate}
                aria-current={isActive ? 'page' : undefined}
                className='min-w-0 flex-1 truncate rounded-lg px-2 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring'
                title={conversation.title}
              >
                {conversation.title}
              </Link>
              <button
                type='button'
                onClick={() => handleDelete(conversation.id)}
                aria-label={`Borrar conversación: ${conversation.title}`}
                className='shrink-0 rounded p-1 text-muted-foreground opacity-0 transition-opacity hover:text-destructive focus-visible:opacity-100 group-hover:opacity-100'
              >
                <Trash2 className='h-3.5 w-3.5' aria-hidden='true' />
              </button>
            </div>
          );
        })}
    </nav>
  );
}

export function SidebarFooter({ collapsed = false, onNavigate }: SidebarContentProps) {
  if (collapsed) {
    return (
      <div className='shrink-0 border-t border-sidebar-border px-2 py-3'>
        <Link
          to='/metodologia'
          onClick={onNavigate}
          aria-label='Metodología'
          title='Metodología'
          className='flex justify-center rounded-lg p-2 text-muted-foreground outline-none hover:bg-sidebar-accent focus-visible:ring-2 focus-visible:ring-sidebar-ring'
        >
          <BookOpen className='h-4 w-4' aria-hidden='true' />
        </Link>
      </div>
    );
  }

  return (
    <div className='shrink-0 border-t border-sidebar-border px-3 py-3 text-xs'>
      <Link
        to='/metodologia'
        onClick={onNavigate}
        className='block rounded px-2 py-1.5 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-sidebar-ring'
      >
        Metodología
      </Link>
      <Link
        to='/metodologia#corpus'
        onClick={onNavigate}
        className='block rounded px-2 py-1.5 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-sidebar-ring'
      >
        Corpus analizado
      </Link>
    </div>
  );
}
```

- [ ] **Step 3: Crear `frontend/src/components/layout/AppSidebar.tsx`**

```tsx
import { cn } from '@/shared/lib/utils';
import { SidebarBrand, SidebarFooter, SidebarNavigation } from './SidebarContent';

export interface AppSidebarProps {
  collapsed: boolean;
  /** `id` del landmark, enlazado desde el toggle mediante `aria-controls`. */
  id?: string;
  className?: string;
}

export function AppSidebar({ collapsed, id, className }: AppSidebarProps) {
  return (
    <aside
      id={id}
      data-collapsed={collapsed}
      className={cn(
        'flex h-full shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground',
        'transition-[width] duration-200 motion-reduce:transition-none',
        collapsed ? 'w-16' : 'w-64',
        className
      )}
    >
      <SidebarBrand collapsed={collapsed} />
      <div className='min-h-0 flex-1 overflow-y-auto py-4'>
        <SidebarNavigation collapsed={collapsed} />
      </div>
      <SidebarFooter collapsed={collapsed} />
    </aside>
  );
}
```

- [ ] **Step 4: Crear `frontend/src/components/layout/MobileNavigation.tsx`**

```tsx
import { Menu } from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/shared/components/ui/button';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetTitle,
  SheetTrigger,
} from '@/shared/components/ui/sheet';
import { SidebarBrand, SidebarFooter, SidebarNavigation } from './SidebarContent';

const SHEET_CONTENT_ID = 'mobile-navigation';

/**
 * Drawer de navegación por debajo de `lg`. Reutiliza exactamente las mismas
 * piezas que el sidebar desktop, siempre en modo expandido.
 */
export function MobileNavigation() {
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button
          type='button'
          variant='ghost'
          size='icon'
          className='lg:hidden'
          aria-label='Abrir menú de navegación'
          aria-controls={SHEET_CONTENT_ID}
        >
          <Menu className='h-5 w-5' aria-hidden='true' />
        </Button>
      </SheetTrigger>

      <SheetContent
        id={SHEET_CONTENT_ID}
        side='left'
        className='flex w-[min(20rem,88vw)] flex-col gap-0 border-sidebar-border bg-sidebar p-0 text-sidebar-foreground sm:max-w-none'
      >
        <div className='sr-only'>
          <SheetTitle>Navegación</SheetTitle>
          <SheetDescription>Menú de navegación de la aplicación</SheetDescription>
        </div>

        <SidebarBrand onNavigate={close} />
        <div className='min-h-0 flex-1 overflow-y-auto py-4'>
          <SidebarNavigation onNavigate={close} />
        </div>
        <SidebarFooter onNavigate={close} />
      </SheetContent>
    </Sheet>
  );
}
```

- [ ] **Step 5: Crear `frontend/src/components/layout/AppLayout.tsx`**

```tsx
import { PanelLeft, PanelLeftClose } from 'lucide-react';
import { useEffect, useRef } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Button } from '@/shared/components/ui/button';
import { AppSidebar } from './AppSidebar';
import { MobileNavigation } from './MobileNavigation';
import { useSidebarCollapsed } from './useSidebarCollapsed';

const SIDEBAR_ID = 'app-sidebar';

/**
 * Shell de dos columnas: sidebar persistente en desktop, drawer por debajo de
 * `lg`, y columna de contenido con un único scroll vertical.
 *
 * Portado del `PrivateLayout` de Presupuestor, conservando su barra fina sticky
 * y el reset de scroll + foco a11y al navegar (el `<main>` es un contenedor de
 * scroll independiente, así que el scroll del documento no sirve).
 */
export function AppLayout() {
  const { collapsed, toggle } = useSidebarCollapsed();
  const location = useLocation();
  const mainRef = useRef<HTMLElement>(null);
  const hasMountedRef = useRef(false);

  useEffect(() => {
    const isInitialMount = !hasMountedRef.current;
    hasMountedRef.current = true;
    const main = mainRef.current;
    if (!main) return;
    if (typeof main.scrollTo === 'function') {
      main.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      main.scrollTop = 0;
    }
    if (isInitialMount) return;
    main.focus({ preventScroll: true });
  }, [location.pathname]);

  return (
    <div className='flex h-screen supports-[height:100dvh]:h-dvh overflow-hidden bg-background'>
      <AppSidebar id={SIDEBAR_ID} collapsed={collapsed} className='hidden lg:flex' />

      <div className='flex min-w-0 flex-1 flex-col'>
        <main
          ref={mainRef}
          tabIndex={-1}
          aria-label='Contenido principal'
          className='flex min-h-0 flex-1 flex-col overflow-hidden focus:outline-none'
        >
          <div className='sticky top-0 z-30 flex shrink-0 items-center gap-3 border-b border-border bg-background/95 px-4 py-2 backdrop-blur supports-[backdrop-filter]:bg-background/80'>
            <MobileNavigation />
            <Button
              type='button'
              variant='ghost'
              size='icon'
              onClick={toggle}
              aria-controls={SIDEBAR_ID}
              aria-expanded={!collapsed}
              aria-label={collapsed ? 'Expandir menú lateral' : 'Colapsar menú lateral'}
              className='hidden lg:inline-flex'
            >
              {collapsed ? (
                <PanelLeft className='h-4 w-4' aria-hidden='true' />
              ) : (
                <PanelLeftClose className='h-4 w-4' aria-hidden='true' />
              )}
            </Button>
            <span className='truncate font-heading text-sm font-semibold text-foreground'>
              Residencia Fiscal
            </span>
          </div>

          <Outlet />
        </main>
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Escribir el test del layout**

Crear `frontend/tests/AppLayout.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';
import { AppLayout } from '@/components/layout/AppLayout';
import { SIDEBAR_COLLAPSED_STORAGE_KEY } from '@/components/layout/useSidebarCollapsed';
import { useConversations } from '@/stores/useConversations';

function renderLayout(initialPath = '/') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path='/' element={<div>contenido</div>} />
          <Route path='/c/:conversationId' element={<div>conversación</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
}

describe('AppLayout', () => {
  beforeEach(() => {
    window.localStorage.clear();
    useConversations.setState({ conversations: [] });
  });

  it('renderiza el contenido de la ruta', () => {
    renderLayout();
    expect(screen.getByText('contenido')).toBeInTheDocument();
  });

  it('arranca con el sidebar expandido', () => {
    renderLayout();
    expect(screen.getByRole('button', { name: 'Colapsar menú lateral' })).toBeInTheDocument();
  });

  it('colapsa y persiste la preferencia', async () => {
    const user = userEvent.setup();
    renderLayout();

    await user.click(screen.getByRole('button', { name: 'Colapsar menú lateral' }));

    expect(screen.getByRole('button', { name: 'Expandir menú lateral' })).toBeInTheDocument();
    expect(window.localStorage.getItem(SIDEBAR_COLLAPSED_STORAGE_KEY)).toBe('true');
  });

  it('rehidrata el estado colapsado desde localStorage', () => {
    window.localStorage.setItem(SIDEBAR_COLLAPSED_STORAGE_KEY, 'true');
    renderLayout();
    expect(screen.getByRole('button', { name: 'Expandir menú lateral' })).toBeInTheDocument();
  });

  it('muestra el mensaje vacío cuando no hay conversaciones', () => {
    renderLayout();
    expect(screen.getByText('Todavía no has hecho ninguna consulta.')).toBeInTheDocument();
  });

  it('lista las conversaciones guardadas con enlace', () => {
    const id = useConversations.getState().createConversation();
    useConversations.getState().appendMessage(id, {
      id: 'm1',
      role: 'user',
      content: 'pregunta sobre los 183 días',
      createdAt: '2026-07-29T10:00:00.000Z',
    });

    renderLayout();

    const link = screen.getByRole('link', { name: 'pregunta sobre los 183 días' });
    expect(link).toHaveAttribute('href', `/c/${id}`);
  });

  it('borra una conversación desde el sidebar', async () => {
    const user = userEvent.setup();
    const id = useConversations.getState().createConversation();
    useConversations.getState().appendMessage(id, {
      id: 'm1',
      role: 'user',
      content: 'consulta a borrar',
      createdAt: '2026-07-29T10:00:00.000Z',
    });

    renderLayout();
    await user.click(screen.getByRole('button', { name: 'Borrar conversación: consulta a borrar' }));

    expect(screen.queryByRole('link', { name: 'consulta a borrar' })).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 7: Ejecutar el test**

Run: `cd frontend && npx vitest run tests/AppLayout.test.tsx`
Expected: PASS, 7 tests.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/layout frontend/tests/AppLayout.test.tsx
git commit -m "feat(frontend): shell de layout con sidebar colapsable y drawer móvil"
```

---

## Task 9: Componentes de chat

**Files:**
- Create: `frontend/src/components/chat/ChatMessageContent.tsx`
- Create: `frontend/src/components/chat/ChatSources.tsx`
- Create: `frontend/src/components/chat/ChatBubble.tsx`
- Create: `frontend/src/components/chat/ChatComposer.tsx`
- Create: `frontend/src/components/chat/ChatWelcome.tsx`

- [ ] **Step 1: Crear `frontend/src/components/chat/ChatMessageContent.tsx`**

Portado de Presupuestor, sin los embebidos de audio y foto (aquí no hay adjuntos).

```tsx
import type { Components } from 'react-markdown';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const remarkPlugins = [remarkGfm];

function safeMarkdownHref(href: string | undefined): string {
  if (!href) return '#';
  if (href.startsWith('https://') || href.startsWith('http://') || href.startsWith('mailto:')) {
    return href;
  }
  return '#';
}

const markdownComponents: Components = {
  p: ({ children }) => <p className='my-2 text-sm leading-relaxed first:mt-0 last:mb-0'>{children}</p>,
  strong: ({ children }) => <strong className='font-semibold'>{children}</strong>,
  em: ({ children }) => <em className='italic'>{children}</em>,
  a: ({ children, href }) => (
    <a
      href={safeMarkdownHref(href)}
      target='_blank'
      rel='noopener noreferrer'
      className='text-primary underline underline-offset-2 hover:text-primary-500'
    >
      {children}
    </a>
  ),
  ul: ({ children }) => (
    <ul className='my-2 list-disc space-y-1 pl-5 text-sm leading-relaxed'>{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className='my-2 list-decimal space-y-1 pl-5 text-sm leading-relaxed'>{children}</ol>
  ),
  li: ({ children }) => <li className='pl-0.5 text-sm leading-relaxed'>{children}</li>,
  blockquote: ({ children }) => (
    <blockquote className='my-2 border-l-4 border-accent-500 bg-accent px-3 py-2 text-sm text-accent-foreground'>
      {children}
    </blockquote>
  ),
  table: ({ children }) => (
    <div className='my-2 overflow-x-auto'>
      <table className='min-w-full border-collapse text-left text-xs'>{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className='bg-muted'>{children}</thead>,
  th: ({ children }) => (
    <th className='border border-border px-2 py-1 font-semibold text-foreground'>{children}</th>
  ),
  td: ({ children }) => <td className='border border-border px-2 py-1 align-top'>{children}</td>,
  code: ({ children }) => (
    <code className='rounded bg-muted px-1 py-0.5 text-[0.8125em]'>{children}</code>
  ),
};

/** Elimina HTML embebido de las respuestas del asistente antes de renderizar. */
function normalizeAssistantMarkdown(content: string): string {
  return content
    .replace(/<\s*(script|style)\b[\s\S]*?<\s*\/\s*\1\s*>/gi, '')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/?[a-z][^>]*>/gi, '')
    .replace(/&nbsp;/gi, ' ');
}

interface ChatMessageContentProps {
  content: string;
  isUser: boolean;
}

export function ChatMessageContent({ content, isUser }: ChatMessageContentProps) {
  if (isUser) {
    return (
      <p className='whitespace-pre-wrap break-words text-sm leading-relaxed text-foreground'>
        {content}
      </p>
    );
  }

  return (
    <div className='break-words text-sm leading-relaxed text-foreground'>
      <ReactMarkdown remarkPlugins={remarkPlugins} components={markdownComponents}>
        {normalizeAssistantMarkdown(content)}
      </ReactMarkdown>
    </div>
  );
}
```

- [ ] **Step 2: Crear `frontend/src/components/chat/ChatSources.tsx`**

```tsx
import { ChevronDown, FileText } from 'lucide-react';
import { useState } from 'react';
import type { ChatSource } from '@/types/chat';
import { cn } from '@/shared/lib/utils';

const RESULTADO_LABEL: Record<string, string> = {
  GANA_AEAT: 'Gana AEAT',
  GANA_CONTRIBUYENTE: 'Gana contribuyente',
  PARCIAL: 'Parcial',
  RETROACCION: 'Retroacción',
  INADMISION: 'Inadmisión',
  DESCONOCIDO: 'Sin clasificar',
};

/** Abrevia el órgano largo del pipeline a algo legible en un chip. */
function shortOrgano(organo: string): string {
  if (organo.startsWith('Tribunal Supremo')) return 'Tribunal Supremo';
  if (organo.startsWith('Audiencia Nacional')) return 'Audiencia Nacional';
  return organo.split('.')[0] ?? organo;
}

function year(fecha: string): string {
  return fecha.slice(0, 4);
}

interface ChatSourcesProps {
  sources: ChatSource[];
}

export function ChatSources({ sources }: ChatSourcesProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (sources.length === 0) return null;

  return (
    <section aria-label='Sentencias citadas' className='mt-3 border-t border-border pt-3'>
      <h3 className='mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground'>
        Sentencias citadas ({sources.length})
      </h3>
      <ul className='flex flex-col gap-1.5'>
        {sources.map((source) => {
          const isExpanded = expandedId === source.archivo;
          return (
            <li key={source.archivo}>
              <button
                type='button'
                onClick={() => setExpandedId(isExpanded ? null : source.archivo)}
                aria-expanded={isExpanded}
                className='flex w-full items-center gap-2 rounded-lg border border-border bg-background px-2.5 py-2 text-left text-xs transition-colors hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-ring'
              >
                <FileText className='h-3.5 w-3.5 shrink-0 text-primary' aria-hidden='true' />
                <span className='font-semibold text-foreground'>{source.roj}</span>
                <span className='truncate text-muted-foreground'>
                  {shortOrgano(source.organo)} · {year(source.fecha)}
                </span>
                <span className='ml-auto shrink-0 rounded bg-muted px-1.5 py-0.5 text-[0.6875rem] text-muted-foreground'>
                  {RESULTADO_LABEL[source.resultado] ?? source.resultado}
                </span>
                <ChevronDown
                  className={cn('h-3.5 w-3.5 shrink-0 transition-transform', isExpanded && 'rotate-180')}
                  aria-hidden='true'
                />
              </button>
              {isExpanded && (
                <div className='mt-1 rounded-lg bg-muted px-3 py-2 text-xs leading-relaxed text-muted-foreground'>
                  <p>{source.extracto}</p>
                  <p className='mt-1.5 font-mono text-[0.6875rem]'>{source.ecli}</p>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
```

- [ ] **Step 3: Crear `frontend/src/components/chat/ChatBubble.tsx`**

```tsx
import type { ChatMessage } from '@/types/chat';
import { ChatMessageContent } from './ChatMessageContent';
import { ChatSources } from './ChatSources';

function formatTime(isoString: string): string {
  try {
    return new Date(isoString).toLocaleTimeString('es-ES', {
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}

interface ChatBubbleProps {
  message: ChatMessage;
}

export function ChatBubble({ message }: ChatBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        data-testid={isUser ? 'chat-bubble-user' : 'chat-bubble-assistant'}
        className={`relative max-w-[92%] rounded-xl px-3.5 py-2.5 shadow-sm ${
          isUser ? 'rounded-tr-none bg-primary-100' : 'rounded-tl-none bg-card border border-border'
        }`}
      >
        <ChatMessageContent content={message.content} isUser={isUser} />
        {message.isStreaming && <span className='ml-0.5 animate-pulse text-muted-foreground'>▍</span>}
        {!isUser && message.sources && <ChatSources sources={message.sources} />}
        <span className='mt-1 block text-right text-[0.6875rem] text-muted-foreground'>
          {formatTime(message.createdAt)}
        </span>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Crear `frontend/src/components/chat/ChatComposer.tsx`**

Portado de Presupuestor, sin adjuntos ni planos, con botón de detener durante el streaming.

```tsx
import { Send, Square } from 'lucide-react';
import { type KeyboardEvent, useRef, useState } from 'react';
import { Button } from '@/shared/components/ui/button';

const MAX_LENGTH = 2000;
const TEXTAREA_MAX_HEIGHT_PX = 160;

interface ChatComposerProps {
  onSend: (content: string) => void;
  onStop: () => void;
  isStreaming: boolean;
  placeholder?: string;
}

export function ChatComposer({
  onSend,
  onStop,
  isStreaming,
  placeholder = 'Escribe tu consulta sobre residencia fiscal…',
}: ChatComposerProps) {
  const [text, setText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const trimmedLength = text.trim().length;
  const isOverMaxLength = trimmedLength > MAX_LENGTH;
  const showCharCount = trimmedLength > MAX_LENGTH * 0.8;
  const canSend = trimmedLength > 0 && !isStreaming && !isOverMaxLength;

  const resetHeight = () => {
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const handleSubmit = () => {
    if (!canSend) return;
    const message = text.trim();
    setText('');
    resetHeight();
    onSend(message);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className='shrink-0 border-t border-border bg-background px-4 py-3'>
      <div className='mx-auto flex w-full max-w-3xl items-end gap-2'>
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(event) => {
            setText(event.target.value);
            const el = event.target;
            el.style.height = 'auto';
            el.style.height = `${Math.min(el.scrollHeight, TEXTAREA_MAX_HEIGHT_PX)}px`;
          }}
          onKeyDown={handleKeyDown}
          rows={1}
          placeholder={placeholder}
          aria-label='Consulta'
          className='max-h-40 min-h-10 flex-1 resize-none rounded-xl border border-input bg-background px-3 py-2 text-sm leading-relaxed outline-none placeholder:text-muted-foreground focus:ring-2 focus:ring-ring'
        />
        {isStreaming ? (
          <Button type='button' variant='outline' size='icon' onClick={onStop} aria-label='Detener respuesta'>
            <Square className='h-4 w-4' aria-hidden='true' />
          </Button>
        ) : (
          <Button
            type='button'
            size='icon'
            onClick={handleSubmit}
            disabled={!canSend}
            aria-label='Enviar consulta'
          >
            <Send className='h-4 w-4' aria-hidden='true' />
          </Button>
        )}
      </div>
      {showCharCount && (
        <p
          className={`mx-auto mt-1 w-full max-w-3xl text-right text-xs ${
            isOverMaxLength ? 'text-destructive' : 'text-muted-foreground'
          }`}
        >
          {trimmedLength} / {MAX_LENGTH}
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Crear `frontend/src/components/chat/ChatWelcome.tsx`**

```tsx
import { Scale } from 'lucide-react';
import { Button } from '@/shared/components/ui/button';

export const SUGGESTED_PROMPTS = [
  '¿Qué pruebas acepta el Tribunal Supremo para desvirtuar los 183 días?',
  '¿Cómo se valoran las ausencias esporádicas del art. 9.1.a) LIRPF?',
  '¿Qué peso tiene un certificado de residencia fiscal extranjero?',
  '¿Cuándo entra el tie-breaker del art. 4 del Modelo OCDE?',
];

interface ChatWelcomeProps {
  onSelectPrompt: (prompt: string) => void;
}

export function ChatWelcome({ onSelectPrompt }: ChatWelcomeProps) {
  return (
    <div
      data-testid='chat-welcome'
      className='flex flex-1 flex-col items-center justify-center px-4 py-8 text-center'
    >
      <span className='mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground'>
        <Scale className='h-7 w-7' aria-hidden='true' />
      </span>
      <h1 className='mb-2 font-heading text-2xl font-semibold text-foreground'>
        Consulta la jurisprudencia de residencia fiscal
      </h1>
      <p className='mb-8 max-w-xl text-sm leading-relaxed text-muted-foreground'>
        106 sentencias del Tribunal Supremo y la Audiencia Nacional sobre el art. 9 LIRPF,
        analizadas y consultables en lenguaje natural. Cada respuesta cita las resoluciones
        en las que se apoya.
      </p>
      <div className='grid w-full max-w-2xl gap-2 sm:grid-cols-2'>
        {SUGGESTED_PROMPTS.map((prompt) => (
          <Button
            key={prompt}
            type='button'
            variant='outline'
            onClick={() => onSelectPrompt(prompt)}
            className='h-auto whitespace-normal px-3 py-3 text-left text-sm font-normal'
          >
            {prompt}
          </Button>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Comprobar tipos**

Run: `cd frontend && npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/chat
git commit -m "feat(frontend): componentes de chat con panel de fuentes"
```

---

## Task 10: Vista de chat y enrutado — TDD

**Files:**
- Create: `frontend/src/components/chat/ChatView.tsx`
- Create: `frontend/src/pages/MetodologiaPage.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/main.tsx`
- Test: `frontend/tests/ChatView.test.tsx`

- [ ] **Step 1: Escribir el test que falla**

Crear `frontend/tests/ChatView.test.tsx`:

```tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ChatView } from '@/components/chat/ChatView';
import { useConversations } from '@/stores/useConversations';
import type { ChatChunk, ChatEngine, CorpusEntry } from '@/types/chat';

const source: CorpusEntry = {
  archivo: 'STS_107_2018.pdf',
  roj: 'STS 107/2018',
  ecli: 'ECLI:ES:TS:2018:107',
  organo: 'Tribunal Supremo. Sala de lo Contencioso-Administrativo',
  fecha: '2018-01-16',
  resultado: 'GANA_AEAT',
  criterioDecisivo: ['CRIT_183_DIAS'],
  esCasoResidencia: true,
};

/** Motor de prueba: emite dos tokens, una fuente y termina. */
function createFakeEngine(): ChatEngine {
  return {
    async *askQuestion(_messages, signal): AsyncIterable<ChatChunk> {
      if (signal.aborted) return;
      yield { type: 'token', text: 'Respuesta ' };
      yield { type: 'token', text: 'simulada.' };
      yield { type: 'sources', sources: [{ ...source, extracto: 'Extracto de prueba.' }] };
      yield { type: 'done' };
    },
  };
}

function renderChat(engine: ChatEngine = createFakeEngine()) {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route path='/' element={<ChatView engine={engine} isStub />} />
        <Route path='/c/:conversationId' element={<ChatView engine={engine} isStub />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('ChatView', () => {
  beforeEach(() => {
    window.localStorage.clear();
    useConversations.setState({ conversations: [] });
  });

  it('muestra la bienvenida y los prompts sugeridos cuando no hay mensajes', () => {
    renderChat();
    expect(screen.getByTestId('chat-welcome')).toBeInTheDocument();
    expect(
      screen.getByRole('button', {
        name: '¿Qué pruebas acepta el Tribunal Supremo para desvirtuar los 183 días?',
      })
    ).toBeInTheDocument();
  });

  it('muestra el aviso de motor simulado', () => {
    renderChat();
    expect(screen.getByRole('status', { name: /motor simulado/i })).toBeInTheDocument();
  });

  it('envía la consulta y pinta el mensaje del usuario', async () => {
    const user = userEvent.setup();
    renderChat();

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), '¿Y los 183 días?');
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));

    expect(await screen.findByText('¿Y los 183 días?')).toBeInTheDocument();
  });

  it('pinta la respuesta del asistente al terminar el streaming', async () => {
    const user = userEvent.setup();
    renderChat();

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), 'pregunta');
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));

    expect(await screen.findByText(/Respuesta simulada\./)).toBeInTheDocument();
  });

  it('renderiza las fuentes citadas', async () => {
    const user = userEvent.setup();
    renderChat();

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), 'pregunta');
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));

    expect(await screen.findByText('STS 107/2018')).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Sentencias citadas' })).toBeInTheDocument();
  });

  it('despliega el extracto de una fuente al pulsarla', async () => {
    const user = userEvent.setup();
    renderChat();

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), 'pregunta');
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));
    await user.click(await screen.findByRole('button', { name: /STS 107\/2018/ }));

    expect(screen.getByText('Extracto de prueba.')).toBeInTheDocument();
  });

  it('un prompt sugerido lanza la consulta', async () => {
    const user = userEvent.setup();
    renderChat();

    await user.click(
      screen.getByRole('button', {
        name: '¿Cuándo entra el tie-breaker del art. 4 del Modelo OCDE?',
      })
    );

    expect(
      await screen.findByText('¿Cuándo entra el tie-breaker del art. 4 del Modelo OCDE?')
    ).toBeInTheDocument();
  });

  it('guarda la conversación en el store', async () => {
    const user = userEvent.setup();
    renderChat();

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), 'consulta guardada');
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));

    await waitFor(() => {
      expect(useConversations.getState().conversations).toHaveLength(1);
    });
    expect(useConversations.getState().conversations[0].title).toBe('consulta guardada');
  });

  it('muestra el botón de detener mientras se recibe la respuesta', async () => {
    const user = userEvent.setup();
    const slowEngine: ChatEngine = {
      async *askQuestion(_messages, signal): AsyncIterable<ChatChunk> {
        if (signal.aborted) return;
        yield { type: 'token', text: 'primero ' };
        await new Promise((resolve) => setTimeout(resolve, 300));
        if (signal.aborted) return;
        yield { type: 'token', text: 'segundo' };
        yield { type: 'done' };
      },
    };
    renderChat(slowEngine);

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), 'pregunta');
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));

    expect(await screen.findByRole('button', { name: 'Detener respuesta' })).toBeInTheDocument();
  });

  it('detener aborta el streaming y devuelve el botón de enviar', async () => {
    const user = userEvent.setup();
    const slowEngine: ChatEngine = {
      async *askQuestion(_messages, signal): AsyncIterable<ChatChunk> {
        for (const text of ['uno ', 'dos ', 'tres ']) {
          if (signal.aborted) return;
          await new Promise((resolve) => setTimeout(resolve, 200));
          if (signal.aborted) return;
          yield { type: 'token', text };
        }
        yield { type: 'done' };
      },
    };
    renderChat(slowEngine);

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), 'pregunta');
    await user.click(screen.getByRole('button', { name: 'Enviar consulta' }));
    await user.click(await screen.findByRole('button', { name: 'Detener respuesta' }));

    expect(await screen.findByRole('button', { name: 'Enviar consulta' })).toBeInTheDocument();
  });

  it('rehidrata los mensajes de una conversación existente', () => {
    const id = useConversations.getState().createConversation();
    useConversations.getState().appendMessage(id, {
      id: 'm1',
      role: 'user',
      content: 'consulta anterior',
      createdAt: '2026-07-29T10:00:00.000Z',
    });

    render(
      <MemoryRouter initialEntries={[`/c/${id}`]}>
        <Routes>
          <Route path='/c/:conversationId' element={<ChatView engine={createFakeEngine()} isStub />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('consulta anterior')).toBeInTheDocument();
    expect(screen.queryByTestId('chat-welcome')).not.toBeInTheDocument();
  });

  it('no envía consultas vacías', async () => {
    const engine = createFakeEngine();
    const spy = vi.spyOn(engine, 'askQuestion');
    const user = userEvent.setup();
    renderChat(engine);

    await user.type(screen.getByRole('textbox', { name: 'Consulta' }), '   ');

    expect(screen.getByRole('button', { name: 'Enviar consulta' })).toBeDisabled();
    expect(spy).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Ejecutar el test para verificar que falla**

Run: `cd frontend && npx vitest run tests/ChatView.test.tsx`
Expected: FAIL — `Failed to resolve import "@/components/chat/ChatView"`.

- [ ] **Step 3: Implementar `frontend/src/components/chat/ChatView.tsx`**

```tsx
import { AlertTriangle } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useConversations } from '@/stores/useConversations';
import type { ChatEngine, ChatMessage, ChatSource } from '@/types/chat';
import { ChatBubble } from './ChatBubble';
import { ChatComposer } from './ChatComposer';
import { ChatWelcome } from './ChatWelcome';

function newMessageId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return crypto.randomUUID();
  return `msg-${Math.random().toString(36).slice(2)}-${Date.now()}`;
}

function TypingIndicator() {
  return (
    <div className='flex justify-start' role='status' aria-label='Buscando en las sentencias'>
      <div className='flex items-center gap-1.5 rounded-xl rounded-tl-none border border-border bg-card px-4 py-3 text-sm text-muted-foreground shadow-sm'>
        <span>Buscando en las sentencias</span>
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className='h-[7px] w-[7px] animate-bounce rounded-full bg-muted-foreground/60'
            style={{ animationDelay: `${i * 0.2}s`, animationDuration: '1.4s' }}
          />
        ))}
      </div>
    </div>
  );
}

function StubBanner() {
  return (
    <div
      role='status'
      aria-label='Aviso: motor simulado'
      className='mx-auto mb-3 flex w-full max-w-3xl items-start gap-2 rounded-lg border border-accent-500/40 bg-accent px-3 py-2 text-xs leading-relaxed text-accent-foreground'
    >
      <AlertTriangle className='mt-0.5 h-4 w-4 shrink-0' aria-hidden='true' />
      <p>
        <strong>Demo:</strong> el motor de análisis todavía no está conectado. Las respuestas son
        simuladas y no constituyen asesoramiento jurídico. Las sentencias citadas sí son reales.
      </p>
    </div>
  );
}

export interface ChatViewProps {
  engine: ChatEngine;
  /** Muestra el aviso de contenido simulado. */
  isStub: boolean;
}

/**
 * Contenedor de la conversación: orquesta store, motor de chat y UI.
 *
 * La conversación se crea de forma perezosa con el primer mensaje, para no
 * llenar el historial de conversaciones vacías cada vez que alguien abre `/`.
 */
export function ChatView({ engine, isStub }: ChatViewProps) {
  const { conversationId } = useParams();
  const navigate = useNavigate();

  const conversations = useConversations((state) => state.conversations);
  const createConversation = useConversations((state) => state.createConversation);
  const appendMessage = useConversations((state) => state.appendMessage);
  const updateMessage = useConversations((state) => state.updateMessage);

  const conversation = conversations.find((c) => c.id === conversationId);
  const messages = conversation?.messages ?? [];

  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Cancela cualquier streaming en curso al desmontar o al cambiar de conversación.
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
      abortRef.current = null;
    };
  }, []);

  useEffect(() => {
    const container = scrollRef.current;
    if (container) container.scrollTop = container.scrollHeight;
  }, [messages.length]);

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsStreaming(false);
  }, []);

  const handleSend = useCallback(
    async (content: string) => {
      const targetId = conversationId ?? createConversation();
      if (!conversationId) navigate(`/c/${targetId}`, { replace: true });

      const now = new Date().toISOString();
      const userMessage: ChatMessage = {
        id: newMessageId(),
        role: 'user',
        content,
        createdAt: now,
      };
      appendMessage(targetId, userMessage);

      const assistantId = newMessageId();
      appendMessage(targetId, {
        id: assistantId,
        role: 'assistant',
        content: '',
        createdAt: new Date().toISOString(),
        isStreaming: true,
      });

      const controller = new AbortController();
      abortRef.current = controller;
      setIsStreaming(true);

      const history = [
        ...(useConversations.getState().getConversation(targetId)?.messages ?? []),
      ].filter((message) => message.id !== assistantId);

      let buffer = '';
      let sources: ChatSource[] | undefined;

      try {
        for await (const chunk of engine.askQuestion(history, controller.signal)) {
          if (chunk.type === 'token') {
            buffer += chunk.text;
            updateMessage(targetId, assistantId, { content: buffer });
          } else if (chunk.type === 'sources') {
            sources = chunk.sources;
          }
        }
      } catch {
        buffer = buffer || 'No se ha podido completar la consulta. Inténtalo de nuevo.';
      } finally {
        updateMessage(targetId, assistantId, {
          content: buffer,
          sources,
          isStreaming: false,
        });
        if (abortRef.current === controller) abortRef.current = null;
        setIsStreaming(false);
      }
    },
    [appendMessage, conversationId, createConversation, engine, navigate, updateMessage]
  );

  const hasMessages = messages.length > 0;
  const lastMessage = messages.at(-1);
  const showTypingIndicator = isStreaming && lastMessage?.isStreaming && !lastMessage.content;

  return (
    <div className='flex min-h-0 flex-1 flex-col'>
      <div ref={scrollRef} className='flex min-h-0 flex-1 flex-col overflow-y-auto px-4 py-4'>
        {isStub && <StubBanner />}

        {hasMessages ? (
          <div
            className='mx-auto flex w-full max-w-3xl flex-col gap-3'
            role='log'
            aria-label='Mensajes de la conversación'
            aria-live='polite'
            aria-relevant='additions'
          >
            {messages.map((message) => (
              <ChatBubble key={message.id} message={message} />
            ))}
            {showTypingIndicator && <TypingIndicator />}
          </div>
        ) : (
          <ChatWelcome onSelectPrompt={handleSend} />
        )}
      </div>

      <ChatComposer onSend={handleSend} onStop={handleStop} isStreaming={isStreaming} />
    </div>
  );
}
```

- [ ] **Step 4: Ejecutar el test para verificar que pasa**

Run: `cd frontend && npx vitest run tests/ChatView.test.tsx`
Expected: PASS, 12 tests.

- [ ] **Step 5: Crear `frontend/src/pages/MetodologiaPage.tsx`**

```tsx
export function MetodologiaPage() {
  return (
    <div className='mx-auto w-full max-w-3xl overflow-y-auto px-4 py-8'>
      <h1 className='mb-6 font-heading text-2xl font-semibold'>Metodología</h1>

      <section className='mb-8'>
        <h2 className='mb-3 font-heading text-lg font-semibold'>Cómo se construyó el análisis</h2>
        <p className='mb-3 text-sm leading-relaxed text-muted-foreground'>
          Cada sentencia se procesa con un modelo de lenguaje que extrae, en formato estructurado,
          los criterios de residencia aplicados (art. 9 LIRPF), las pruebas aportadas por cada
          parte con su valoración judicial, el razonamiento del tribunal y el resultado del fallo.
        </p>
        <p className='mb-3 text-sm leading-relaxed text-muted-foreground'>
          Las pruebas se clasifican en doce categorías —desde presencia física y desplazamientos
          hasta trazas digitales— y cada una se registra con el criterio que ataca, si fue admitida
          o rechazada, el peso que le dio el tribunal y la cita literal que lo respalda.
        </p>
        <p className='text-sm leading-relaxed text-muted-foreground'>
          Las resoluciones de mayor relevancia doctrinal se procesan con un modelo premium para
          maximizar la precisión de la extracción.
        </p>
      </section>

      <section id='corpus' className='mb-8 scroll-mt-16'>
        <h2 className='mb-3 font-heading text-lg font-semibold'>Corpus analizado</h2>
        <ul className='mb-3 list-disc space-y-1 pl-5 text-sm leading-relaxed text-muted-foreground'>
          <li>106 resoluciones judiciales españolas.</li>
          <li>74 del Tribunal Supremo y 32 de la Audiencia Nacional.</li>
          <li>Período 2015-2025.</li>
          <li>Fuente: CENDOJ (Centro de Documentación Judicial).</li>
        </ul>
        <p className='text-sm leading-relaxed text-muted-foreground'>
          El corpus cubre litigios sobre residencia fiscal de personas físicas. Las resoluciones que
          el análisis identifica como fuera de alcance quedan marcadas y no se citan como apoyo.
        </p>
      </section>

      <section>
        <h2 className='mb-3 font-heading text-lg font-semibold'>Limitaciones</h2>
        <ul className='list-disc space-y-1 pl-5 text-sm leading-relaxed text-muted-foreground'>
          <li>
            El contenido tiene finalidad informativa y de investigación. No constituye
            asesoramiento jurídico ni sustituye el criterio de un profesional.
          </li>
          <li>
            La extracción es automática: puede contener errores de interpretación. Cada respuesta
            cita las sentencias en las que se apoya para que puedan contrastarse en la fuente.
          </li>
          <li>
            El corpus es una selección, no la totalidad de la jurisprudencia sobre la materia.
          </li>
        </ul>
      </section>
    </div>
  );
}
```

- [ ] **Step 6: Crear `frontend/src/App.tsx`**

```tsx
import { Navigate, Route, Routes } from 'react-router-dom';
import { ChatView } from '@/components/chat/ChatView';
import { AppLayout } from '@/components/layout/AppLayout';
import { chatEngine, chatEngineMode } from '@/lib/chat-engine';
import { MetodologiaPage } from '@/pages/MetodologiaPage';

const isStub = chatEngineMode === 'stub';

export function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path='/' element={<ChatView engine={chatEngine} isStub={isStub} />} />
        <Route path='/c/:conversationId' element={<ChatView engine={chatEngine} isStub={isStub} />} />
        <Route path='/metodologia' element={<MetodologiaPage />} />
        <Route path='*' element={<Navigate to='/' replace />} />
      </Route>
    </Routes>
  );
}
```

- [ ] **Step 7: Crear `frontend/src/main.tsx`**

```tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { App } from './App';
import './index.css';

const container = document.getElementById('root');
if (!container) throw new Error('No se encontró el elemento #root');

createRoot(container).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>
);
```

- [ ] **Step 8: Ejecutar toda la suite, tipos y lint**

Run: `cd frontend && npx vitest run && npx tsc --noEmit && npx biome check .`
Expected: PASS los tres. Si Biome señala formato, corregir con `npx biome check --write .` y volver a ejecutar.

- [ ] **Step 9: Construir la aplicación**

Run: `cd frontend && npm run build`
Expected: `prebuild` escribe el corpus y Vite genera `dist/` sin errores.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/components/chat/ChatView.tsx frontend/src/pages/MetodologiaPage.tsx \
  frontend/src/App.tsx frontend/src/main.tsx frontend/tests/ChatView.test.tsx
git commit -m "feat(frontend): vista de chat, página de metodología y enrutado"
```

---

## Task 11: Verificación visual en el navegador

El usuario trabaja en WSL2: las rutas `file://` no le funcionan, hay que servir por HTTP en localhost.

- [ ] **Step 1: Levantar el servidor de desarrollo**

Run: `cd frontend && npm run dev`
Expected: Vite escucha en `http://127.0.0.1:5174`.

- [ ] **Step 2: Comprobar manualmente**

Abrir `http://localhost:5174` y verificar:

1. Se ve la bienvenida con los cuatro prompts sugeridos y el aviso de demo.
2. Al pulsar un prompt aparece el mensaje del usuario, el indicador de escritura y la respuesta con streaming visible.
3. Bajo la respuesta aparecen las sentencias citadas; al pulsar un chip se despliega el extracto y el ECLI.
4. La conversación aparece en el sidebar y la URL pasa a `/c/<id>`.
5. El toggle de colapso reduce el sidebar a rail y el estado sobrevive a un refresco.
6. A menos de 1024 px de ancho el sidebar desaparece y la hamburguesa abre el drawer.
7. `/metodologia` renderiza y el enlace «Corpus analizado» salta al ancla.
8. Detener durante el streaming corta la respuesta y devuelve el botón de enviar.

- [ ] **Step 3: Parar el servidor**

Detener el proceso de `npm run dev`.

---

## Task 12: Configuración de Netlify

**Files:**
- Create: `netlify.toml` (raíz del repositorio)

- [ ] **Step 1: Crear `netlify.toml`**

```toml
[build]
  base = "frontend"
  command = "npm run build"
  publish = "dist"

[build.environment]
  NODE_VERSION = "24"

[[headers]]
  for = "/*"
  [headers.values]
    X-Frame-Options = "DENY"
    X-Content-Type-Options = "nosniff"
    Referrer-Policy = "strict-origin-when-cross-origin"
    Strict-Transport-Security = "max-age=31536000; includeSubDomains; preload"
    Permissions-Policy = "geolocation=(), microphone=(), camera=()"
    # CSP restrictiva: la app es 100% estática y no llama a ningún backend.
    # Al conectar el motor RAG habrá que ampliar `connect-src` con su origen.
    Content-Security-Policy = "default-src 'self'; base-uri 'self'; form-action 'self'; object-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"

[[headers]]
  for = "/assets/*"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"

[[headers]]
  for = "/index.html"
  [headers.values]
    Cache-Control = "no-cache, no-store, must-revalidate"

[[headers]]
  for = "/data/corpus.json"
  [headers.values]
    Cache-Control = "public, max-age=3600"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

- [ ] **Step 2: Validar el build de producción localmente**

Run: `cd frontend && rm -rf dist && npm run build && npx vite preview --port 4174`
Expected: sirve en `http://127.0.0.1:4174`. Comprobar que `/c/algo` y `/metodologia` cargan al refrescar (el preview de Vite ya aplica el fallback SPA).

Detener el preview al terminar.

- [ ] **Step 3: Commit**

```bash
git add netlify.toml
git commit -m "chore: configuración de despliegue en Netlify"
```

---

## Task 13: Documentación

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md`

> **Nota:** el `README.md` y el `CLAUDE.md` actuales ya documentan el pipeline con
> uv + Makefile y la API FastAPI. **No los reescribas**: solo añade el dominio y
> la parte de frontend, respetando lo existente.

- [ ] **Step 1: Añadir el dominio al encabezado del `README.md`**

Sustituir estas dos primeras líneas:

```markdown
# Residencia Fiscal

Pipeline Python que analiza sentencias judiciales españolas sobre **residencia fiscal
```

por:

```markdown
# Residencia Fiscal

**[residenciafiscal.org](https://residenciafiscal.org)**

Pipeline Python que analiza sentencias judiciales españolas sobre **residencia fiscal
```

- [ ] **Step 2: Añadir la sección de frontend al `README.md`**

Insertar esta sección justo ANTES de la sección `## Documentación` (la última del fichero):

```markdown
## Frontend (residenciafiscal.org)

SPA React en `frontend/`, desplegada en Netlify: chatbot que consulta el corpus de
sentencias en lenguaje natural.

```bash
cd frontend
npm install
npm run dev        # http://127.0.0.1:5174
npm run test       # Vitest
npm run fast-check # lint + typecheck + tests
npm run build      # genera el corpus y compila a dist/
```

El motor de conversación es hoy un **stub**: la interfaz está completa y las
sentencias citadas son reales, pero las respuestas son simuladas. El backend RAG
está pendiente de decidir.
```

Y añadir esta línea al final de la lista de `## Documentación`:

```markdown
- `docs/superpowers/` — especificaciones de diseño y planes de implementación
```

- [ ] **Step 3: Actualizar el encabezado del `CLAUDE.md`**

Sustituir la línea:

```markdown
Guía para Claude Code en el proyecto **Residencia Fiscal**.
```

por:

```markdown
Guía para Claude Code en el proyecto **Residencia Fiscal** — [residenciafiscal.org](https://residenciafiscal.org).
```

- [ ] **Step 4: Añadir la sección de frontend al `CLAUDE.md`**

Insertar la siguiente sección justo antes de la sección `## Referencias`:

```markdown
## Frontend (residenciafiscal.org)

SPA React en `frontend/`, desplegada en Netlify. Chatbot que consulta el corpus
de sentencias en lenguaje natural.

### Stack

Vite 7 + React 19 + TypeScript + Tailwind CSS v4 + Radix UI + zustand.
Componentes de layout y chat portados del área privada de
`/home/ubuntu/ai_projects/presupuestor` (sin MUI, Supabase, Sentry ni PWA).

### Comandos

```bash
cd frontend
npm install
npm run dev        # servidor de desarrollo en 127.0.0.1:5174
npm run test       # Vitest
npm run typecheck  # tsc --noEmit
npm run lint       # Biome
npm run build      # prebuild (corpus) + vite build
```

### Estructura

| Ruta | Función |
|---|---|
| `src/lib/chat-engine.ts` | Punto único de selección del motor. Cambiar aquí al conectar el backend |
| `src/lib/chat-engine.stub.ts` | Motor simulado con streaming y citas reales |
| `src/lib/corpus.ts` | Carga `public/data/corpus.json` |
| `src/stores/useConversations.ts` | Historial en localStorage (`rf.conversations.v1`) |
| `src/components/layout/` | Shell: sidebar colapsable, drawer móvil, barra fina |
| `src/components/chat/` | Vista de chat, burbujas, composer, panel de fuentes |
| `scripts/build-corpus.mjs` | Genera el corpus ligero desde `output/analisis_*.jsonl` |

### Estado del motor

El chat funciona hoy con un **stub**. `chatEngineMode` en
`src/lib/chat-engine.ts` vale `'stub'`, lo que activa el aviso de contenido
simulado en la UI. Al conectar el backend real hay que cambiarlo a `'live'`,
que apaga el aviso automáticamente.

Opciones de backend evaluadas y aún abiertas: ampliar la **API FastAPI ya
existente** (`api/main.py`) con un endpoint `/chat`, Netlify Functions + OpenAI
file_search, o Netlify Functions + Supabase pgvector.

### Despliegue

`netlify.toml` en la raíz: `base = "frontend"`, `publish = "dist"`, redirect SPA
y CSP restrictiva. Al conectar el backend hay que ampliar `connect-src` en la
CSP con el origen de la API.
```

- [ ] **Step 5: Actualizar la estructura de archivos del `CLAUDE.md`**

En la sección `## Estructura de Archivos`, añadir estas entradas al árbol
existente (que ya incluye `Makefile`, `pyproject.toml`, `uv.lock`, `api/`,
`test/`, etc.). **No reescribir el árbol entero**: insertar tras la línea de
`output/`:

```
├── frontend/                # SPA React (residenciafiscal.org)
│   ├── src/                 # Código de la aplicación
│   ├── scripts/             # build-corpus.mjs
│   ├── tests/               # Vitest
│   └── package.json
├── netlify.toml             # Despliegue del frontend
├── docs/superpowers/        # Specs y planes de implementación
```

- [ ] **Step 6: Commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs: dominio residenciafiscal.org y documentación del frontend"
```

---

## Task 14: Verificación final y cross-review

- [ ] **Step 1: Ejecutar la verificación completa**

Run: `cd frontend && npm run fast-check && npm run build`
Expected: lint, typecheck, tests y build en verde. Anotar el número real de tests que pasan.

- [ ] **Step 2: Comprobar que no se ha roto el pipeline Python**

Run: `cd /home/ubuntu/ai_projects/residenciafiscal && make fast-check`
Expected: ruff, mypy y pytest en verde. Este trabajo no toca Python, así que
cualquier fallo aquí es preexistente: anotarlo y NO intentar arreglarlo dentro
de esta tarea.

- [ ] **Step 3: Revisar el estado del repositorio**

Run: `git status --short && git log --oneline -12`
Expected: árbol limpio; los commits de las tareas 1-13 presentes.

- [ ] **Step 4: Cross-review con Codex**

Según `CLAUDE.md`, una feature nueva multiarchivo exige pasar el gate de revisión antes del push:

Run: `/codex:review --wait --scope branch --base main`

Si hay hallazgos serios, aplicarlos con `/codex:rescue --resume "aplica los fixes propuestos"` y commitear como `fix: address codex review` antes de continuar.

- [ ] **Step 5: Informar al usuario**

Resumir: qué se ha construido, cuántos tests pasan, cómo levantarlo en local, y los dos pasos que quedan en su mano — apuntar el dominio residenciafiscal.org a Netlify y decidir el backend RAG.
