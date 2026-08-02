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
- El sidecar de roles jurisdiccionales de cada sentencia (`jurisdicciones/`).
- La proyección pública de las 67 candidatas y su manifiesto (`publico/`).
  **Se versiona porque el build de Netlify la necesita**: allí solo corre npm, y
  sin estos ficheros el Deploy Preview de la fase C1 se quedaría sin fichas.
  Su contenido es derivado puro y su hash está en el manifiesto.

Los ficheros bajo `knowledge/jurisprudencia-v3` son derivados reproducibles y
no deben editarse a mano. La corrección se hace en la entrada canónica o en el
generador y luego se regenera el derivado.

`output/` continúa siendo transitorio salvo
`output/jurisprudence-v3-rollout-state.json`, que se conserva porque el build
publicado referencia directamente su hash.

## Presupuesto y gate

`make rollout-verify` falla si el árbol publicado alcanza cualquiera de estos
tres límites, y el mensaje dice cuál:

| Límite | Valor | Qué vigila |
|---|---|---|
| `MAX_ARTIFACT_BYTES` | 50.000.000 | Lo que de verdad encarece el clon. Hoy: 15,9 MB (32 %). |
| `MAX_ARTIFACT_FILES_PER_DOCUMENT` | 10 | La **causa** del crecimiento. Hoy: 8,8. |
| `MAX_ARTIFACT_FILES` | 2.500 | Backstop de lo que no crece por sentencia. Hoy: 935. |

**Por qué tres y no uno.** El presupuesto era de 1.000 ficheros y 50 MB, y al
incorporar los sidecars de roles y las proyecciones públicas de las fases A y C1
el árbol llegó al 93 % del recuento con solo el 36 % del peso: el límite total
medía cuántas sentencias hay, no si el árbol estaba engordando. Lo que hay que
vigilar es **cuántos derivados carga cada sentencia**, porque es lo que se
multiplica por 106 —y por 212 cuando entre el segundo corpus de la fase E—.

Hoy cada documento deja nueve artefactos: caso canónico, verbatim, perfil OKF/3,
índice de recuperación, evaluación, propuesta, sidecar de roles, proyección
pública y su informe. Añadir un décimo hace saltar el gate, y esa es la
intención: que sea una decisión registrada aquí y no un efecto lateral de
generar algo nuevo.

Subir cualquiera de los tres exige justificarlo en este documento, no solo en el
código.

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
