# Aviso sobre el contenido no software

La licencia [MIT](LICENSE) de este repositorio cubre **el código fuente y la
documentación**, y nada más.

Este fichero existe porque `LICENSE` debe contener el texto MIT íntegro y sin
añadidos: cualquier nota intercalada impide que GitHub y las herramientas de
análisis reconozcan la licencia, y un colaborador deja de verla. La salvedad
jurídica, que es real e importante, se declara aquí.

## Lo que la licencia MIT NO cubre

Los documentos jurídicos que el repositorio incluye no son obra de este
proyecto. Cada corpus se rige por las condiciones de reutilización de su fuente,
que prevalecen sobre la licencia MIT:

| Directorio | Fuente | Condiciones |
|---|---|---|
| `sentencias/` | CENDOJ (Consejo General del Poder Judicial) | [`sentencias/AVISO_LEGAL.md`](sentencias/AVISO_LEGAL.md) |
| `normativa/es/` | Agencia Estatal Boletín Oficial del Estado | [`normativa/es/AVISO_LEGAL.md`](normativa/es/AVISO_LEGAL.md) |

Dos matices que esos avisos desarrollan:

- Las resoluciones judiciales de `sentencias/` son documentos públicos que el
  CENDOJ publica **ya pseudonimizados**; el repositorio no los reidentifica ni
  altera su texto.
- De los textos legales de `normativa/es/`, **la única versión con valor
  jurídico es la edición oficial del BOE**. Lo que aquí se versiona es una copia
  para trabajar sobre ella, no una fuente de derecho.

## Contenido derivado

`knowledge/` contiene material generado por el proyecto a partir de esas
fuentes: extractos literales, perfiles, índices y anotaciones. El código que lo
produce es MIT, pero **el texto legal citado sigue perteneciendo a su fuente** y
mantiene sus condiciones. El invariante del proyecto es que ese texto nunca se
reescribe: una cita solo se publica como subcadena exacta del original.

Ninguna parte de este repositorio es asesoramiento jurídico.
