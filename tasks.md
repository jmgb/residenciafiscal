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

- 🔲 **`pypdf` sigue fuera de Dependabot: falta un gate que revalide todo el corpus.**
  **2026-11-15:** subido de 6.14.2 a 6.21.4 por 18 alertas Dependabot (10 high, DoS por PDF
  manipulado). `src/verbatim_validation.py` ya no exige que `extractor.version` coincida con el
  pypdf instalado: es procedencia, y la validación exige reproducir el texto página a página.
  Las 1.312 páginas de los 106 PDF salen idénticas con ambas versiones, así que el corpus no se
  regeneró. Historial y procedimiento: `docs/jurisprudence/VERBATIM_CORPUS.md` §Versión del
  extractor. Queda el pin exacto y el `ignore` de `.github/dependabot.yml` porque los tests solo
  reextraen el piloto SAN 1210/2023; con el `ignore`, cada alerta nueva hace fallar el security
  update job (`all_versions_ignored`) y hay que subirlo a mano.
  **Cierre:** un `make` que revalide los 106 artefactos verbatim contra el pypdf instalado, en CI
  o como requisito de los PR de pypdf, y entonces quitar el `ignore` de pypdf.

## Mantenimiento periódico

- [ ] **Rotar secretos de alto impacto cada 90 días (próxima: 2027-02-03).** Alcance en este repo: Supabase, R2, Cloudflare. El resto, una vez al año o tras un incidente. Al terminar, mover la fecha 90 días. Excepción: un secreto expuesto en un sitio público o a terceros (repo, Sentry, email, servicio externo) o invalidado se rota en el momento; una aparición en la transcripción local de una sesión espera al calendario.
