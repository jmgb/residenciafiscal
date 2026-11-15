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

Los pendientes operativos de esta revisión están cerrados; su evidencia vive
en [`docs/project/TASKS_ARCHIVE.md`](docs/project/TASKS_ARCHIVE.md#cierres-operativos-del-15-de-noviembre-de-2026).
El backlog de producto, SEO y sus bloqueos sigue en
[`docs/project/TASKS.md`](docs/project/TASKS.md).

## Mantenimiento periódico

- [ ] **Rotar secretos de alto impacto cada 90 días (próxima: 2027-02-03).** Alcance en este repo: Supabase, R2, Cloudflare. El resto, una vez al año o tras un incidente. Al terminar, mover la fecha 90 días. Excepción: un secreto expuesto en un sitio público o a terceros (repo, Sentry, email, servicio externo) o invalidado se rota en el momento; una aparición en la transcripción local de una sesión espera al calendario.
