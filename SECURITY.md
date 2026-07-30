# Política de seguridad

## Cómo reportar

**No abras una issue pública para un fallo de seguridad.**

Usa el aviso privado de GitHub:
[Security → Report a vulnerability](https://github.com/jmgb/residenciafiscal/security/advisories/new).

Incluye qué versión o commit has probado, cómo reproducirlo y qué impacto crees
que tiene. Respondo en cuanto pueda; este es un proyecto personal, así que no
hay un SLA formal.

## Qué entra en el alcance

- **`POST /analizar`** (`src/api/main.py`): es la única ruta que gasta dinero. Sus
  guardarraíles son un token opcional (`RESIDENCIAFISCAL_API_TOKEN` +
  cabecera `X-API-Token`), un límite de subida de 25 MB cortado por
  `Content-Length` antes de parsear el multipart, una allowlist de modelos y
  validación de `reasoning_effort` y `max_pages`.
- Fugas de claves de API o de datos del entorno a través de logs, respuestas o
  mensajes de error.
- Inyección de prompt que consiga que el pipeline ejecute algo distinto de
  extraer datos de la sentencia, o que exfiltre contenido del sistema.
- Cualquier forma de conseguir que un tercero gaste presupuesto de API ajeno.

## Qué NO entra en el alcance

- **Ausencia de rate limiting.** Es conocido y está documentado en `CLAUDE.md`.
  La API está pensada para `127.0.0.1`. `make dev-public` avisa al arrancar.
- **La ruta abierta sin `RESIDENCIAFISCAL_API_TOKEN`.** Es el comportamiento
  deliberado en local; define el token si la expones.
- Errores u omisiones del análisis producido por el LLM. Son un problema de
  calidad, no de seguridad: abre una issue normal.
- Vulnerabilidades de dependencias sin explotabilidad demostrada en este
  proyecto. Dependabot ya vigila las actualizaciones.

## Manejo de secretos

Las claves viven en `.env`, que está en `.gitignore` y **nunca** debe
versionarse. `.env.example` documenta las variables sin valores. Los workflows
de CI no usan secrets a propósito: la suite por defecto no llama a ningún
proveedor LLM.

Si crees que una clave se ha filtrado en un commit, revócala en el panel del
proveedor **antes** de reportar nada.

## Datos personales

Las resoluciones de `sentencias/` las publica el CENDOJ ya pseudonimizadas. Si
detectas un dato personal identificable en algún fichero del repositorio o en
una salida del pipeline, repórtalo por el canal privado: se retira el fichero.
Ver [`sentencias/AVISO_LEGAL.md`](sentencias/AVISO_LEGAL.md).
