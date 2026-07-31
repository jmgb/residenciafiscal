# Aviso legal sobre las resoluciones judiciales

Este directorio contiene 106 resoluciones judiciales españolas en PDF sobre
residencia fiscal de personas físicas (Art. 9 LIRPF), junto con el inventario
(`readme.txt`) y la lista de sentencias clave (`sentencias_CLAVE.txt`).

## Origen

Todas proceden del **CENDOJ** (Centro de Documentación Judicial del Consejo
General del Poder Judicial), buscador público en
<https://www.poderjudicial.es/search/>. Se descargaron tal cual las publica el
CENDOJ, sin modificar su contenido.

## Naturaleza de los documentos

- Son **documentos públicos**. El art. 107 LOPJ encomienda al CGPJ la
  publicación oficial de las sentencias del Tribunal Supremo y del resto de
  órganos judiciales.
- El CENDOJ las publica ya **pseudonimizadas**: los datos identificativos de las
  personas físicas han sido sustituidos por iniciales o suprimidos en origen.
  **Este repositorio no ha añadido ni retirado ninguna anonimización.**
- La reutilización de la jurisprudencia difundida por el CENDOJ está sujeta a
  las condiciones que el propio CGPJ publica en su portal. Consúltalas antes de
  redistribuir estos ficheros o construir un producto sobre ellos.

## Cómo se usan aquí

Los PDFs se incluyen para que la extracción literal, los hashes, las citas y la
compilación del corpus sean **reproducibles**. El workflow combina Python y una
propuesta de agente; el repositorio no envía los PDF a una API LLM.

No se persigue crear una base de datos jurisprudencial alternativa ni sustituir
al CENDOJ como fuente oficial. Para citar una resolución en un contexto
profesional, usa siempre el texto oficial del CENDOJ y su ROJ/ECLI.

## Si eres titular de derechos o detectas un problema

Si consideras que la inclusión de alguno de estos documentos vulnera derechos de
terceros, protección de datos o condiciones de reutilización, repórtalo por el
canal privado —
[aviso de seguridad de GitHub](https://github.com/jmgb/residenciafiscal/security/advisories/new)
— y no en una issue pública: así el dato personal concreto no queda expuesto al
reportarlo. Se retirará el fichero afectado. Ver [`SECURITY.md`](../SECURITY.md).

## Descargo de responsabilidad

El análisis automático que produce este proyecto se genera con modelos de
lenguaje y **puede contener errores u omisiones**. No es asesoramiento jurídico
ni fiscal, ni sustituye la lectura del texto íntegro de la resolución ni el
criterio de un profesional.
