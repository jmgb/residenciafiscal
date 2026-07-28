# Frontend chatbot para residenciafiscal.org — Diseño

**Fecha**: 2026-07-29
**Estado**: aprobado
**Dominio**: residenciafiscal.org (adquirido)

## 1. Objetivo

Construir el frontend de residenciafiscal.org: un chatbot que responde consultas
sobre residencia fiscal (Art. 9 LIRPF) apoyándose en las 106 sentencias ya
analizadas por el pipeline Python de este repositorio.

Esta iteración entrega **solo el frontend**, desplegable en Netlify, con el motor
de conversación resuelto por un *stub* local. El backend real queda fuera de
alcance y se decidirá después.

### Aclaración técnica

«Entrenado con las sentencias» se implementará como **RAG** (recuperación +
generación con citas), no como fine-tuning. Es más barato, más preciso y permite
citar la sentencia exacta. Esto condiciona la UI: cada respuesta del asistente
lleva un panel de fuentes.

## 2. Alcance

### Dentro

- Proyecto Vite + React + TypeScript nuevo en `frontend/`.
- Shell visual copiado del área privada de Presupuestor (sidebar + topbar).
- UI de chat con streaming, historial local y panel de fuentes.
- Stub del motor de chat con la interfaz definitiva del backend.
- Script que genera un corpus ligero de metadatos desde el JSONL de salida.
- Tests unitarios (Vitest + Testing Library).
- Configuración de despliegue en Netlify.
- Actualización de `README.md` y `CLAUDE.md` con el dominio y el frontend.

### Fuera

- Backend RAG (Netlify Functions, Supabase pgvector o VPS).
- Autenticación, cuentas de usuario y sincronización de conversaciones.
- Explorador tabular de sentencias y dashboards de estadísticas.
- Tests E2E, analítica, PWA, i18n.

## 3. Decisiones tomadas

| Decisión | Elección | Motivo |
|---|---|---|
| Propósito del sitio | Chatbot sobre las sentencias | Decisión del usuario |
| Acceso | Abierto y público, sin login | Máximo alcance; el stub no tiene coste |
| Backend | Stub local por ahora | Entrega rápida del frontend; motor se decide después |
| Alcance de la copia | Proyecto nuevo con piezas selectas de Presupuestor | Evita arrastrar MUI, Supabase, Sentry, PWA |
| Identidad visual | Misma estructura de tokens, paleta jurídica | El naranja de obra no encaja en legal-fiscal |
| Historial | localStorage, sin cuentas | Sin backend no hay dónde persistir |

## 4. Arquitectura

### Ubicación

El frontend vive en `frontend/` dentro de este mismo repositorio. El pipeline
Python de la raíz no se toca.

```
residenciafiscal/
├── residenciafiscal.py        # pipeline (sin cambios)
├── output/                    # fuente del corpus
├── netlify.toml               # base = "frontend"
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    ├── index.html
    ├── scripts/build-corpus.mjs
    ├── public/data/corpus.json   # generado
    ├── src/
    │   ├── main.tsx
    │   ├── App.tsx
    │   ├── index.css
    │   ├── components/
    │   │   ├── layout/
    │   │   └── chat/
    │   ├── lib/
    │   ├── stores/
    │   ├── shared/components/ui/
    │   └── types/
    └── tests/
```

### Stack

Vite 7, React 19, TypeScript, Tailwind CSS v4, Radix UI, lucide-react,
react-router-dom, react-markdown + remark-gfm, zustand, Vitest + Testing Library.

Explícitamente **excluidos** respecto a Presupuestor: MUI, Supabase, Sentry,
PostHog, vite-plugin-pwa, dexie, axios, react-hook-form, la capa offline.

Gestor de paquetes: npm. Node 24 (igual que Presupuestor).

## 5. Qué se copia de Presupuestor

Origen: `/home/ubuntu/ai_projects/presupuestor/frontend/src/`.

| Origen | Destino | Adaptación |
|---|---|---|
| `shared/lib/utils.ts` (`cn`) | `src/shared/lib/utils.ts` | Verbatim |
| `shared/components/ui/{button,input,textarea,scroll-area,tooltip,separator,sheet,skeleton,dialog}.tsx` | `src/shared/components/ui/` | Verbatim; se añaden más solo si algún componente portado los exige |
| `index.css` | `src/index.css` | Podado a los tokens en uso + paleta jurídica |
| `components/layout/private/PrivateLayout.tsx` | `src/components/layout/AppLayout.tsx` | Se eliminan analytics, personas, `SimulationBanner`, `OfflineIndicator`, `useActiveProjectNavContext`, `usePersonaNavigation`. Se conservan: shell de dos columnas, barra fina sticky, medición de `--header-height`, scroll-reset y foco a11y |
| `components/layout/private/PrivateSidebar.tsx` + `PrivateSidebarHeader.tsx` | `src/components/layout/AppSidebar.tsx` | Sin `PlanWidget`, `ProjectsListSection`, `PersonaSwitcher`, `UserMenu` |
| `components/layout/private/PrivateMobileNavigation.tsx` | `src/components/layout/MobileNavigation.tsx` | Drawer con el mismo contenido del sidebar |
| `components/layout/private/PrivateTopbar.tsx` | `src/components/layout/Topbar.tsx` | Contexto de título y slot de acciones; sin lo demás |
| `components/layout/private/useSidebarCollapsed.ts` | `src/components/layout/useSidebarCollapsed.ts` | Verbatim |
| `components/chat/ChatBubble.tsx` | `src/components/chat/ChatBubble.tsx` | Se añaden fuentes bajo la burbuja del asistente |
| `components/chat/ChatComposer.tsx` | `src/components/chat/ChatComposer.tsx` | Se eliminan adjuntos y planos (`onAttachFloorPlan*`, `allowFloorPlanUpload`) |
| `components/chat/ChatMessageContent.tsx` | idem | Verbatim (markdown) |
| `components/chat/ChatPanelFrame.tsx` | `src/components/chat/ChatPanelFrame.tsx` | Recortado al scroll de mensajes y anclaje del composer |
| `components/chat/ChatTypingWelcome.tsx` | `src/components/chat/ChatWelcome.tsx` | Texto, logo y eyebrow propios |

**No se copia** `UnifiedChatWidget.tsx` (1258 líneas acopladas a presupuestos,
project picker, acciones y adjuntos). Se escribe en su lugar `ChatView.tsx`,
un contenedor limpio.

## 6. Identidad visual

Se conserva el sistema de tokens `@theme` de Tailwind v4 de Presupuestor y las
tipografías duales (`Space Grotesk` para headings, `Inter` para texto).

Cambia la paleta:

| Token | Valor | Uso |
|---|---|---|
| `--color-primary` | `#1e3a5f` (azul pizarra profundo) | Marca, botones, énfasis |
| Escala `--color-primary-{50..950}` | Derivada del primario | Fondos, hovers, bordes |
| `--color-accent` | Ámbar sobrio (`#b45309` como base) | Citas y destacados |
| Neutros | Grises fríos (slate) | Igual que Presupuestor |

Se elimina toda la escala `--color-construction` (naranja de obra).

## 7. Estructura de la interfaz

Layout de dos columnas idéntico al área privada de Presupuestor.

### Sidebar (desktop `lg+`, drawer por debajo)

- Cabecera con logo y nombre del sitio.
- Botón «Nueva consulta».
- Lista de conversaciones guardadas (título derivado del primer mensaje del
  usuario), con acción de borrar.
- Pie con enlaces a Metodología y al corpus analizado.
- Colapsable en desktop, con el estado persistido (`useSidebarCollapsed`).

### Barra fina superior

Toggle de colapso (desktop) / hamburguesa (móvil) y título de la conversación
activa.

### Área principal — `ChatView`

- **Bienvenida** cuando no hay mensajes: tarjeta con el propósito del sitio y
  4 prompts sugeridos, por ejemplo:
  - «¿Qué pruebas acepta el Tribunal Supremo para desvirtuar los 183 días?»
  - «¿Cómo se valoran las ausencias esporádicas del art. 9.1.a) LIRPF?»
  - «¿Qué peso tiene un certificado de residencia fiscal extranjero?»
  - «¿Cuándo entra el tie-breaker del art. 4 del Modelo OCDE?»
- **Lista de mensajes** con burbujas usuario/asistente y markdown.
- **Panel de fuentes** bajo cada respuesta del asistente: chips con ROJ, órgano
  abreviado y año; al desplegar, el extracto citado y el resultado del fallo.
- **Composer sticky** abajo: textarea autoexpandible, envío con Enter, salto de
  línea con Shift+Enter, botón de detener mientras hay streaming.

### Rutas

| Ruta | Contenido |
|---|---|
| `/` | Conversación nueva (pantalla de bienvenida) |
| `/c/:conversationId` | Conversación guardada |
| `/metodologia` | Página estática: cómo se construyó el análisis, qué corpus lo respalda (106 sentencias, 74 STS / 32 SAN, 2015-2025) y qué limitaciones tiene |
| `*` | Redirige a `/` |

Los dos enlaces del pie del sidebar apuntan a `/metodologia`, uno a la sección
del método y otro al ancla del corpus.

## 8. Capa de datos

### Interfaz del motor de chat

Toda la comunicación pasa por un único módulo, `src/lib/chat-engine.ts`. Es el
punto de sustitución cuando llegue el backend real: no debe cambiar nada más.

```ts
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: string;      // ISO
  sources?: ChatSource[];
}

export interface ChatSource {
  archivo: string;        // "STS_107_2018.pdf"
  roj: string;            // "STS 107/2018"
  ecli: string;
  organo: string;
  fecha: string;          // ISO
  resultado: string;      // GANA_AEAT | GANA_CONTRIBUYENTE | ...
  criterioDecisivo: string[];
  extracto: string;
}

export interface ChatChunk {
  type: 'token' | 'sources' | 'done';
  text?: string;
  sources?: ChatSource[];
}

export interface ChatEngine {
  askQuestion(
    messages: ChatMessage[],
    signal: AbortSignal
  ): AsyncIterable<ChatChunk>;
}
```

### Stub

`src/lib/chat-engine.stub.ts` implementa `ChatEngine`:

- Emite los tokens de una respuesta predefinida con retardo, para que el
  streaming y el botón de detener se comporten como en producción.
- Respeta `AbortSignal`: cancelar detiene la emisión.
- Selecciona 2–4 fuentes reales del corpus según palabras clave de la pregunta
  (183 días, ausencias, CDI, vivienda, centro de intereses), con fallback a las
  sentencias marcadas como clave.

Las respuestas del stub llevan un aviso visible de que el motor todavía no está
conectado, para no confundir contenido simulado con análisis real.

### Corpus

`frontend/scripts/build-corpus.mjs` lee el JSONL más reciente de `output/` y
genera `public/data/corpus.json` con solo metadatos ligeros:

```json
{
  "archivo": "SAN_1071_2025.pdf",
  "roj": "SAN 1071/2025",
  "ecli": "ECLI:ES:AN:2025:1071",
  "organo": "Audiencia Nacional. Sala de lo Contencioso-Administrativo, Sección Cuarta",
  "fecha": "2025-02-18",
  "resultado": "PARCIAL",
  "criterioDecisivo": ["CRIT_CENTRO_INTERESES_ECONOMICOS"],
  "esCasoResidencia": true
}
```

Se ejecuta en `prebuild`. El JSON resultante pesa unas decenas de KB; el JSONL
completo (898 KB) no se publica.

### Estado

`src/stores/useConversations.ts` (zustand + persistencia en localStorage):
lista de conversaciones, conversación activa, alta, borrado y anexado de
mensajes. Clave de almacenamiento versionada (`rf.conversations.v1`) para poder
migrar sin romper.

## 9. Tests

Vitest con entorno jsdom y Testing Library.

| Suite | Cubre |
|---|---|
| `tests/chat-engine.stub.test.ts` | Emisión de tokens, cancelación por `AbortSignal`, selección de fuentes por palabra clave, fallback |
| `tests/useConversations.test.ts` | Alta, anexado, borrado, persistencia y rehidratación desde localStorage |
| `tests/ChatView.test.tsx` | Envío de mensaje, estado de streaming, render de fuentes, prompts sugeridos, botón de detener |
| `tests/AppLayout.test.tsx` | Colapso del sidebar y persistencia del estado |

Se sigue TDD: test primero, implementación después.

## 10. Despliegue

`netlify.toml` en la raíz del repositorio:

- `base = "frontend"`, `command = "npm run build"`, `publish = "dist"`.
- `NODE_VERSION = "24"`.
- Redirect SPA `/* → /index.html` con status 200.
- Cabeceras de seguridad adaptadas de Presupuestor: `X-Frame-Options: DENY`,
  `X-Content-Type-Options: nosniff`, `Referrer-Policy`,
  `Strict-Transport-Security`, y una CSP restrictiva (`default-src 'self'`) sin
  los orígenes de terceros de Presupuestor. Cuando se conecte el backend habrá
  que ampliar `connect-src`.
- Cache inmutable para `/assets/*`, sin caché para `/index.html`.

Dominio: residenciafiscal.org, apuntado a Netlify con HTTPS automático.

## 11. Documentación a actualizar

- **`README.md`**: hoy contiene una sola línea. Pasa a describir el proyecto, el
  dominio y las dos partes (pipeline Python y frontend).
- **`CLAUDE.md`**: añadir el dominio, una sección de arquitectura del frontend,
  los comandos de desarrollo (`npm run dev`, `build`, `test`), el despliegue en
  Netlify y la extensión de la estructura de archivos.

## 12. Riesgos y decisiones diferidas

- **Sin autenticación**: aceptable con el stub. Cuando se conecte un LLM real,
  un chat público es una factura abierta; habrá que añadir rate limiting,
  captcha o captura de email antes de exponer el backend.
- **Divergencia con Presupuestor**: los componentes copiados son una bifurcación,
  no una dependencia compartida. Las mejoras en Presupuestor no llegarán solas.
  Es el precio de no montar un monorepo compartido y se acepta.
- **Contenido simulado**: el aviso del stub debe ser inequívoco. Publicar
  respuestas jurídicas simuladas sin marcar sería un problema real de confianza.
- **Motor RAG por decidir**: las opciones evaluadas siguen abiertas y la
  interfaz `ChatEngine` sirve a todas. El repositorio ya expone una **API
  FastAPI** (`api/main.py`, puerto 8010) que envuelve el pipeline, así que
  ampliarla con un endpoint `/chat` es hoy el camino de menor fricción; las
  alternativas son Netlify Functions + OpenAI file_search o Netlify Functions +
  Supabase pgvector.
