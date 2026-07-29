# Qué cambia

<!-- Una o dos frases: qué hace este PR y por qué. Enlaza la issue si existe (Closes #123). -->

## Cómo se ha comprobado

<!-- Comandos ejecutados y su resultado. Si has probado a mano, di con qué PDF o ruta. -->

- [ ] `make fast-check` en verde
- [ ] `cd frontend && npm run fast-check` en verde *(si tocas `frontend/`)*
- [ ] `cd frontend && npm run build` en verde *(si tocas `frontend/`: CI compila y `fast-check` no)*

## Impacto

- [ ] Cambia el schema de salida del análisis *(si sí: documentado en `CLAUDE.md` y en `prompt.py`)*
- [ ] Cambia el comportamiento del CLI o de la API *(si sí: documentado en `README.md`)*
- [ ] Afecta al coste por sentencia
- [ ] Toca piezas de marca *(si sí: revisado contra `docs/brand/brand-guidelines.md`)*
- [ ] Añade dependencias *(si sí: `uv.lock` / `package-lock.json` regenerados en este PR)*

## Notas para quien revise

<!-- Decisiones discutibles, alternativas descartadas, deuda que dejas a propósito. -->
