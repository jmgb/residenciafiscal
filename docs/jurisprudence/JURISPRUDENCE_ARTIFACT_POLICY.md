# Política de artefactos del corpus jurisprudencial v3

## Decisión vigente

Los artefactos del rollout de 106 sentencias se conservan en Git mientras no
exista un almacén externo con retención, versionado e integridad equivalentes.
La trazabilidad offline pesa más que el ahorro actual: el árbol
`knowledge/jurisprudencia-v3` ocupa aproximadamente 14,5 MB y menos de 1.000
ficheros.

Esta decisión no convierte los borradores en contenido aprobado. Su estado
sigue siendo `AGENT_REVIEWED_ONLY` y el corpus completo permanece aislado del
chat.

## Qué se versiona

- El manifiesto de entrada y el estado final del rollout, con hashes SHA-256.
- El corpus verbatim, los casos canónicos, perfiles e índices por cuestión.
- Los bancos de evaluación y los informes técnicos, de auditoría y cobertura.
- El corpus agregado aislado `retrieval/rollout-106.corpus.json` y su build.

Los ficheros bajo `knowledge/jurisprudencia-v3` son derivados reproducibles y
no deben editarse a mano. La corrección se hace en la entrada canónica o en el
generador y luego se regenera el derivado.

`output/` continúa siendo transitorio salvo
`output/jurisprudence-v3-rollout-state.json`, que se conserva porque el build
publicado referencia directamente su hash.

## Presupuesto y gate

`make rollout-verify` falla si el árbol publicado alcanza cualquiera de estos
límites:

- 1.000 ficheros;
- 50.000.000 bytes.

También comprueba los hashes del manifiesto, estado, fuentes, propuestas,
evaluaciones, casos y derivados; la correspondencia exacta entre manifiesto y
corpus; y los conteos agregados. `make rollout-reproducibility` vuelve a generar
corpus, calidad y build y exige un diff vacío. Ambos controles se ejecutan en
CI sin claves ni llamadas a modelos.

## Cuándo cambiar la política

Antes de superar el presupuesto se debe mover el material secundario a un
bundle de release u object storage inmutable. Git debe conservar como mínimo el
manifiesto, los hashes, los contratos, los informes de gates y un procedimiento
probado de restauración. No se elimina ningún artefacto hasta verificar que una
copia recuperada reproduce los hashes publicados.
