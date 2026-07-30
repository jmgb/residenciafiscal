# Protocolo de revisión jurídica ciega F0.3

**Estado:** pendiente de ejecución.
**Fecha de definición:** 2026-07-30.
**Alcance:** ocho preguntas y dieciséis respuestas sobre la muestra piloto de
cinco sentencias.

## 1. Objetivo

Este protocolo convierte la revisión F0.3 en un gate jurídico auditable antes
de corregir el corpus, repetir llamadas o ampliar la evaluación. No determina
qué estrategia es mejor por sí solo: fija quién puede revisar, qué puede abrir
y cuándo puede revelarse la correspondencia X/Y.

La revisión técnica, automática o realizada por un agente no sustituye este
gate.

## 2. Revisor requerido

La revisión debe realizarla un abogado o abogada con experiencia acreditable en
fiscalidad y residencia fiscal española. No debe haber participado en la
generación de las respuestas ni conocer la correspondencia X/Y.

El repositorio solo conserva un identificador estable del revisor, su función y
las fechas de revisión. El responsable del proyecto conserva fuera del
repositorio la comprobación de identidad y cualificación profesional. No se
versionan número de colegiación, firma, correo ni otros datos personales.

Si el revisor conoce la correspondencia antes de cerrar el formulario, la
revisión puede conservarse como exploratoria, pero no supera el gate ciego.

## 3. Material permitido y material vedado

El revisor solo debe abrir:

- [rúbrica congelada](CHAT_STRATEGY_F03_RUBRIC.md);
- [paquete ciego](CHAT_STRATEGY_F03_BLIND_REVIEW.md);
- [plantilla de revisión](CHAT_STRATEGY_F03_REVIEW_FORM_TEMPLATE.md);
- este protocolo.

Hasta cerrar y congelar la revisión no debe abrir:

- `CHAT_STRATEGY_F03_REVEAL_KEY.json`;
- `CHAT_STRATEGY_F03_BUILD.json`, porque también contiene el orden X/Y;
- `CHAT_STRATEGY_F02_RESULTS.md`;
- los artefactos originales de `output/file-search/`;
- el código del generador o los tests que permitan reconstruir la asignación.

La ceguera es procedimental, no criptográfica. El custodio no debe entregar el
directorio del repositorio. Debe construir y enviar únicamente el ZIP saneado:

```bash
make build-chat-f03-legal-bundle
```

El ZIP contiene exactamente los cuatro Markdown permitidos y `MANIFEST.json`
con el SHA-256 de cada uno. No contiene la clave, el manifiesto de build, los
resultados F0.2, artefactos de proveedor ni código. El constructor usa nombres,
permisos y fecha ZIP fijos, por lo que dos ejecuciones sobre las mismas entradas
producen los mismos bytes.

## 4. Procedimiento

1. Copiar `CHAT_STRATEGY_F03_REVIEW_FORM_TEMPLATE.md` como
   `CHAT_STRATEGY_F03_REVIEW_COMPLETED.md`.
2. Completar la declaración inicial del revisor sin introducir datos de
   clientes ni datos personales innecesarios.
3. Evaluar primero cada respuesta por separado conforme a la rúbrica.
4. Elegir la preferencia X/Y únicamente después de puntuar ambas respuestas.
5. Completar las ocho parejas, fechar el cierre y marcar la declaración final.
6. Comprobar que no quedan selecciones múltiples, puntuaciones vacías ni
   motivos pendientes mediante:

   ```bash
   make validate-chat-f03-review
   ```

7. Versionar el formulario cerrado antes de abrir cualquier material vedado.
8. Calcular su SHA-256 y entregarlo al custodio del experimento; el hash se
   registrará después en el artefacto de resultados, no dentro del propio
   formulario.

## 5. Criterio de revisión completa

Para cada una de las dieciséis respuestas deben constar:

- una única selección en cada gate G1–G5;
- las seis puntuaciones `0`, `1`, `2` o `N/A`, con motivo cuando sea `N/A`;
- una única selección sobre error crítico;
- observaciones suficientes para entender los fallos materiales.

Para cada una de las ocho parejas deben constar:

- una preferencia: X, Y, empate o ninguna;
- un nivel de confianza;
- un motivo.

El formulario debe incluir además identificador del revisor, función,
experiencia pertinente, fechas de inicio y cierre, declaración de ceguera y
confirmación de revisión completa.

## 6. Cierre y revelado

El gate queda cerrado cuando el formulario completo tiene fecha, un commit
anterior al revelado y un SHA-256 calculado sobre ese contenido ya congelado.
Además, `make validate-chat-f03-review` debe terminar correctamente. Solo
entonces se abre la clave.

El resultado revelado se documenta en artefactos nuevos, sin modificar el
formulario cerrado. El compilador falla si la revisión está incompleta, si la
clave no corresponde al paquete o si falta la confirmación explícita:

```bash
make compile-chat-f03-results \
  CONFIRM_REVEAL=1 \
  CHAT_F03_REVIEW_COMMIT=<commit-del-formulario>
```

El comando solo se ejecuta después de versionar el formulario cerrado. Genera
JSON auditable y un resumen Markdown e incluye:

- commit y SHA-256 del formulario;
- versiones y hashes de rúbrica, paquete y banco de preguntas;
- correspondencia X/Y;
- gates, puntuaciones y preferencias agregadas.

El compilador no inventa incidencias, desacuerdos ni decisiones. Esos tres
elementos se documentan después como interpretación humana del resultado,
referenciando el JSON compilado, antes de corregir datos o repetir llamadas.

Mientras no exista el formulario cerrado no se generan resultados ficticios ni
se abre la clave para completar el informe a mano.

Una revisión de ocho parejas sirve como baseline y detector de fallos. No basta
para declarar una estrategia ganadora ni para autorizar por sí sola el rollout
de cinco a 106 sentencias.
