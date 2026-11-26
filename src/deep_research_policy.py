"""Inference policy owned by the asynchronous deep-research profile."""

# Copia a mano del modelo de Codex (decisión del 2026-11-26): el runtime corre con
# `--ignore-user-config` y no lee el config.toml del contenedor. Cambiarlo exige un
# bundle nuevo con su tarifa y la transición de docs/operations/DEEP_RESEARCH.md.
DEEP_RESEARCH_MODEL = "gpt-6.2-sol"
DEEP_RESEARCH_REASONING_EFFORT = "high"
