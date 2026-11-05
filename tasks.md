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

## P1

- 🔲 **El digest semanal ya no se actualiza solo en alfredo (2026-11-05, auditoría GitHub G02).**
  `residenciafiscal-weekly-ga4-telegram` hacía `fetch`+`merge` de `main` y ejecutaba el checkout como
  `ubuntu`, que tiene `sudo` y `docker`; el repo es público, así que esa ruta no necesitaba credencial.
  Un drop-in (`10-no-autoupdate.conf`) quitó esos pasos: un cambio en
  `scripts/weekly_ga4_telegram.py` ya no llega a producción hasta hacer a mano
  `git merge --ff-only` en `/home/ubuntu/residenciafiscal`. **Cierre:** el digest corre con usuario
  propio y runtime fijo fuera del checkout, como `comunicador-weekly`, o queda documentado el paso
  manual en la guía de operación, y una pasada natural de lunes llega por Telegram. Primera pasada
  con el cambio: 2026-11-09, 09:10.

## P2

- 🔲 **Decidir #72: sustituir `@google/genai` por `fetch` en el chat.** Es un borrador con el smoke en rojo desde la auditoría de dependencias del 4 nov 2026 (`repos/residenciafiscal.md`, candidata 7). **Cierre:** smoke en verde e integrado, o PR cerrado.

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
  **2026-09-03:** dependabot ignora ahora `pypdf` en `.github/dependabot.yml`. Reabría el bump cada
  lunes dentro del grupo `python-runtime` y arrastraba al resto del grupo —openai, pydantic— a un PR
  que no se podía mergear, así que el pin se sostenía a base de cerrar PRs a mano.
  **2026-10-21:** 28 alertas Dependabot de pypdf 6.14.2 (16 high, todas DoS por PDF manipulado,
  corregidas entre 6.15.0 y 6.19.0) descartadas como *tolerable risk*: el `ignore` hacía fallar el
  security update job (`all_versions_ignored`). Motivo en `docs/jurisprudence/VERBATIM_CORPUS.md`.
  Al migrar, el objetivo mínimo es 6.19.0.
  **Cierre:** `pypdf` sin pin exacto en `pyproject.toml`, sin la entrada `ignore` de dependabot, y
  `make test` en verde con los artefactos regenerados.

## Mantenimiento periódico

- [ ] **Rotar secretos de alto impacto cada 90 días (próxima: 2027-02-03).** Alcance en este repo: Supabase, R2, Cloudflare. El resto, una vez al año o tras un incidente. Al terminar, mover la fecha 90 días. Excepción: un secreto expuesto en un sitio público o a terceros (repo, Sentry, email, servicio externo) o invalidado se rota en el momento; una aparición en la transcripción local de una sesión espera al calendario.
