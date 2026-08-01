# Netlify Edge Functions — límites medidos

Resultados del *spike* de plataforma de la fase 0 del backend de chat. Son
mediciones reales contra un Deploy Preview del proyecto, no lecturas de la
documentación.

**Fecha**: 2026-07-29 · **Región de ejecución**: ES · **Deploy**: draft
`spike-fase0`

| Paquete | Versión |
|---|---|
| `netlify-cli` | 27.0.1 |
| `@netlify/edge-functions` | 3.0.8 |
| `@netlify/blobs` | 10.7.11 |
| `openai` | 7.1.0 |
| `zod` | 4.4.3 |

El spike se ejecutó con un corpus sintético de **891 KB**, calibrado para igualar
el tamaño que tendrá `_corpus.ts` con las 106 sentencias reales (el JSONL de
origen pesa 888 KB). Medir con un bundle más pequeño habría dado un CPU
optimista.

## Resumen

| # | Criterio | Objetivo | Medido | Veredicto |
|---|---|---|---|---|
| 1 | `openai`, `zod` y `@netlify/blobs` cargan en Deno | los tres | los tres `true` | ✅ |
| 2 | p95 de CPU propio | < 40 ms | **15,3 ms** | ✅ |
| 3 | Streaming más allá de los 10 s de las Functions | > 10 s | **19,87 s** | ✅ |
| 4 | Cabeceras antes del límite de 40 s | < 10 s | **0,30 s** | ✅ |
| 5 | Compare-and-swap sin perder incrementos | exacto | **incrementos perdidos** | ❌ |

Cuatro de cinco. El quinto invalida el diseño de cuotas y presupuesto del
[spec del backend de chat](../superpowers/specs/2026-07-29-chat-backend-design.md),
sección 4.

## Criterio 2 — CPU y el corpus en dos niveles

El límite documentado es **50 ms de CPU propio por petición**; la espera de red
no cuenta. La medición demuestra que el reparto del corpus en dos niveles no es
una optimización opcional, es **obligatorio**.

| Estrategia | Parseo | Arranque en frío | p95 | Máximo | Peticiones > 50 ms |
|---|---:|---:|---:|---:|---:|
| Índice y fichas parseados juntos | 24,5–26,9 ms | 46,6 ms | 12,1 ms | **53,9 ms** | 1 de 40 |
| Índice eager, fichas bajo demanda | 2,7–3,1 ms | 23,1 ms | 15,3 ms | 40,6 ms | 0 de 60 |

Parsear las 106 fichas en el arranque **supera el límite duro**. Con el índice
como cadena JSON (153 KB) y las fichas como literal de objeto de cadenas —de las
que solo se materializan las candidatas del ranking— el parseo baja de 26,9 ms a
3,1 ms.

En caliente el trabajo por petición es despreciable: **0,13–0,19 ms**. Todo el
coste está en el arranque de cada isolate nuevo, que en 60 peticiones ocurrió 9
veces.

Margen restante: el peor caso medido deja **9,4 ms** hasta el límite. La
implementación real hará más trabajo que el spike —validación de entrada, hash
de IP, búfer de citas, serialización SSE—, así que ese margen hay que vigilarlo.

> **Nota sin resolver**: la petición de 53,9 ms devolvió `200`. El límite de 50 ms
> no se comportó como una terminación inmediata en esta prueba. No conviene
> apoyarse en ello.

## Criterios 3 y 4 — Streaming

Una emisión de 20 segundos llegó completa: 20 eventos `data:` más el terminal
`event: done`, total 19,87 s. Las Functions con streaming se habrían cortado a
los 10 s.

Tiempo hasta la primera cabecera: **0,30 s**, muy lejos del límite de 40 s.

Esto confirma la decisión de runtime del spec: las Edge Functions son el único
sitio de Netlify donde cabe una respuesta larga en streaming.

## Criterio 5 — El compare-and-swap de Blobs no es atómico

**Este es el hallazgo que bloquea.**

En secuencial todo funciona: el ETag es una cadena, cambia en cada escritura y
la lectura con `consistency: 'strong'` refleja siempre la anterior.

Bajo concurrencia se pierden incrementos. Cinco peticiones simultáneas sobre un
contador inicializado a 0:

| Petición | Leyó | Escribió | ETag usado en `onlyIfMatch` | `modified` |
|---|---:|---:|---|---|
| 1 | 0 | 1 | `4bb9e0de…` | `true` |
| 3 | 0 | 1 | `4bb9e0de…` | `true` |
| 2 | 1 | 2 | `082c26c8…` | `true` |
| 4 | 1 | 2 | `082c26c8…` | `true` |
| 5 | 1 | 2 | `082c26c8…` | `true` |

Contador final: **2**. Esperado: 5.

Las peticiones 2, 4 y 5 leyeron el mismo valor con el mismo ETag, escribieron
con `onlyIfMatch` sobre ese ETag y **las tres recibieron `modified: true`**.
Nadie pierde la carrera, así que el bucle de reintento nunca se dispara y las
escrituras se pisan.

Dato adicional: los ETag son **deterministas por contenido**. Escribir `{n:1}`
produce siempre `082c26c8…`. No son tokens de versión, así que `onlyIfMatch` no
puede distinguir «el valor que yo leí» de «un valor idéntico que escribió otro».

### Consecuencia

El algoritmo de la sección 4 del spec —leer con ETag, calcular, escribir con
`onlyIfMatch`, reintentar si otro ganó— **no aporta atomicidad**. Aplicado tal
cual:

- la cuota horaria por IP contaría de menos y el límite tendría fugas;
- la reserva de gasto contaría de menos y **el techo diario podría superarse**,
  que es justo la garantía que protege el dinero.

### Alternativa validada: una clave por petición

Si cada petición escribe su **propia** clave y el recuento se obtiene listando
el prefijo, dos escritores nunca tocan la misma clave y el *lost update* es
imposible por construcción.

Medido: 50 peticiones concurrentes, 50 respuestas `200`, el recuento pasó de 93
a **143 exactas** y siguió estable 10 s después.

Coste a cambio:

| Entradas en el prefijo | Latencia de `list()` |
|---:|---:|
| 0 | 115 ms |
| 20 | 123 ms |
| 143 | 248–422 ms |

Son 130–420 ms de red antes del primer token, y hay que pagarlos dos veces si se
comprueban cuota y presupuesto por separado. La latencia no cuenta como CPU,
pero sí la nota el usuario.

Queda una ventana entre contar y escribir que permite sobrepasar el techo por
aproximadamente el factor de concurrencia. Es un error acotado y muy preferible
a perder incrementos, pero no es una transacción.

**`store.list()` pagina.** Un recuento ingenuo sobre un prefijo grande
sub-reporta, y un borrado masivo en una sola invocación agota el tiempo de la
edge function. Cualquier implementación tiene que iterar con `paginate: true`.

## Otros hallazgos operativos

### El prefijo `_` no exime a un fichero de ser una edge function

Netlify trata **todo `.ts` en la raíz de `netlify/edge-functions/`** como una
edge function y exige que exporte por defecto una función. Un módulo compartido
llamado `_corpus.ts` rompe el build:

```
Bundling of edge function failed
Default export in '…/netlify/edge-functions/_corpus.ts' must be a function.
```

Los módulos compartidos van en un **subdirectorio** (`netlify/edge-functions/lib/`),
que el bundler no escanea como funciones. El spec y el plan del backend de chat
afirmaban lo contrario y se han corregido.

### `netlify-cli` no arranca en este proyecto

`netlify dev` y `netlify deploy --build` fallan con:

```
TypeError: Cannot read properties of undefined (reading 'Intrinsic')
    at .../node_modules/ts-api-utils/lib/index.cjs:787:57
    at .../precinct/node_modules/@typescript-eslint/typescript-estree/dist/convert-comments.js
```

Es `ts-api-utils`, dependencia del CLI vía `precinct`, contra el **TypeScript
7.0.2** hoisteado del proyecto. No es un fallo del código del sitio.

Workaround: instalar el CLI **fuera del árbol del proyecto** para que resuelva
sus propias dependencias.

```bash
mkdir -p /tmp/netlify-cli && cd /tmp/netlify-cli
npm init -y && npm install netlify-cli
cd /ruta/al/repo/frontend
/tmp/netlify-cli/node_modules/.bin/netlify deploy --alias mi-prueba
```

Esto afecta a la tarea de integración local del plan del chat, que daba por
hecho que `netlify dev` funcionaría.

### El plugin de Sentry exige un token válido

Con un `SENTRY_TOKEN` inválido, `@sentry/vite-plugin` registra HTTP 401 al crear
la release y subir sourcemaps, aunque el build puede continuar. Si la variable
falta, la configuración actual no activa el plugin. El build de producción del
1 de agosto de 2026 confirmó autenticación correcta, creación de release y
subida de los cuatro artefactos de sourcemap; un 401 futuro vuelve a ser una
incidencia de credencial, no ruido esperado.

## Cómo reproducir

El código del spike era temporal y se ha borrado. Para rehacerlo:

1. Generar un corpus sintético de ~890 KB con la estructura de `CorpusIndexEntry`
   y 106 fichas.
2. Emitir `INDEX_JSON` como cadena y `FICHAS` como literal de objeto de cadenas.
3. Una edge function en `netlify/edge-functions/` con el módulo generado en
   `lib/`, que parsee el índice de forma perezosa y cronometre con
   `performance.now()`.
4. Modos `?modo=stream`, `?modo=cas` y `?modo=uniq` para los criterios 3 a 5.
5. Desplegar con `netlify deploy --alias <nombre>` (draft, producción intacta) y
   medir contra la URL del draft.

`netlify dev` **no vale como evidencia**: no reproduce ni los límites de CPU ni
la latencia del edge real.
