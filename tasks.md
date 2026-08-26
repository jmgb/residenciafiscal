# Tasks — residenciafiscal

> Índice **ligero** de tareas vivas. Creado el 2026-08-26 con el mismo formato que ya usan
> `apps`, `presupuestor` y `sofia-financial-reports`, para dejar de perder trabajo accionable
> detectado de pasada.

## Reglas de este archivo

1. **Toda tarea declara prioridad.** Una tarea sin prioridad no compite por atención.
2. **Toda tarea declara criterio de cierre verificable.** "Revisar si compensa" no se cierra nunca.
3. **El texto de una tarea no es evidencia.** Antes de accionar, comprobar el código vivo.
4. **Al cerrar, se borra la entrada** (git la conserva).

Estados: `🔲 pendiente` · `🏗️ en progreso` · `⏸️ pausada`
Prioridades: **P0** bloquea producción · **P1** evita regresión relevante · **P2** deuda importante ·
**P3** backlog sin urgencia.

---

## P2

- 🔲 **`pypdf` está pineado en `==6.14.2` porque los artefactos guardan la versión del extractor.**
  Los casos de `knowledge/jurisprudencia-v3/` y los artefactos verbatim registran
  `extractor: pypdf/6.14.2`, y `src/verbatim_validation.py:49` compara ese valor con
  `version("pypdf")` de la librería instalada: cualquier otra versión levanta
  `ValueError: extractor no coincide con la versión de validación`. Detectado el 2026-08-26 al
  actualizar dependencias: `uv lock --upgrade` subía a 6.16.2 y tumbaba 5 tests
  (`test_export_jurisprudence_case`, los dos de `..._derivatives` y los dos de
  `test_verbatim_pilot_artifact`), incluido el de bytes reproducibles.

  El pin desbloquea la actualización del resto de dependencias, pero congela `pypdf`: subirlo exige
  **regenerar los artefactos versionados con la nueva versión y revisar los bytes resultantes**,
  porque un cambio en la extracción de texto altera el contenido, no solo la etiqueta. Decidir
  entonces si la validación debe seguir siendo por igualdad exacta o basta con registrar la versión
  usada sin exigir coincidencia.
  **Cierre:** `pypdf` sin pin exacto en `pyproject.toml` y `make test` en verde con los artefactos
  regenerados.
