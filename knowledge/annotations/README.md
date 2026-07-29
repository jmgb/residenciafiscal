# Anotaciones jurisprudenciales

Esta carpeta contiene decisiones editoriales separadas de los datos generados.
Cada sidecar se llama como el `slug` del concepto y declara el PDF mediante
`source_file`.

Reglas:

- nunca editar el PDF, una cita, `source_excerpt_verbatim` ni otro texto de la
  sentencia;
- `proposed` documenta una propuesta y no modifica el perfil;
- `approved` exige `reviewed_by` y `reviewed_at`;
- solo pueden corregirse los metadatos derivados que permite
  `okf_annotations.py`;
- cada `source_anchor` debe ser una subcadena exacta de la página física del
  PDF;
- para rechazar o sustituir una propuesta, conservar la trazabilidad en Git en
  vez de editar un artefacto de `knowledge/jurisprudencia/`.

El contrato, los campos y el flujo completo están en
[`docs/OKF_PIPELINE.md`](../../docs/OKF_PIPELINE.md).
