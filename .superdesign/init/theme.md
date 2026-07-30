# Theme

## Compact token summary

- Product: Residencia Fiscal, a jurisprudence research chat.
- Visual principle: “El expediente, legible”: restrained legal-document aesthetic; borders before shadows; no gradients for brand work, no decorative legal clichés.
- Fonts: Space Grotesk 500–700 for headings; Inter 400–700 for interface and body; system monospace only for verifiable evidence identifiers.
- Background/card/popover: `#ffffff`.
- Foreground/card-foreground/popover-foreground: `#0f172a`.
- Primary: `#1e3a5f`; foreground `#f8fafc`; complete slate-blue scale 50–950.
- Accent surface: `#fffbeb`; accent foreground `#78350f`; accent-400 `#f59e0b` is reserved for amber over primary surfaces.
- Secondary/muted: `#f1f5f9`; secondary foreground `#1e293b`; muted foreground `#64748b`.
- Border/input: `#e2e8f0`; focus ring: `#1e3a5f`.
- Success `#15803d`; warning `#b45309`; destructive `#b91c1c`.
- Base radius: 0.5rem; interactive components typically rounded-lg or rounded-xl.
- Motion: 200ms restrained tone/shadow transitions; no hover scaling; press may move to 0.98.
- Focus: 2px primary ring with 2px offset via `control-focus`.
- Spacing and responsive breakpoints use Tailwind CSS 4 defaults.
- Important contrast: muted-foreground is only valid on white; use secondary-foreground on tinted surfaces.
- One primary action per view. In chat, that action is sending the query.

## Raw source

### `frontend/src/index.css`

```css
@import 'tailwindcss';
@import 'tw-animate-css';

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
  --color-accent-400: #f59e0b; /* solo ámbar sobre superficie primary (isotipo): 5.36:1 */
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
  .control-field {
    @apply w-full rounded-md border border-input bg-background px-3 py-1 text-sm text-foreground shadow-sm transition-colors;
  }

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
