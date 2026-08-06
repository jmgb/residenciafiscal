# Privacidad y marco legal del sitio

> **Estado:** `/privacidad` publicada y completa el 1 de agosto de 2026.
> **Responsable:** Intangible Land LLC (EIN 92-2584862), Brickell Dr #1111,
> Miami, FL 33131, Estados Unidos. Contacto: `info@residenciafiscal.org`.
> **Decisión firme:** no se designa representante en la UE (art. 27 RGPD).

Este documento explica de dónde sale cada afirmación de la página pública, qué
se ha decidido y qué sigue abierto. La página es
`frontend/src/pages/PrivacyPage.tsx`; la persistencia que describe está
contratada en [`SUPABASE_CHAT.md`](SUPABASE_CHAT.md) y las copias en
[`BACKUPS.md`](BACKUPS.md).

## Por qué esta página es también el aviso legal

No hay ruta `/aviso-legal` ni `/cookies` separadas, a diferencia de otros
proyectos de la misma titularidad. La identificación que exige el art. 10
LSSI-CE —titular, identificador fiscal, domicilio y correo— se publica dentro de
la sección 1 de `/privacidad`, y las cookies en la sección 9. Es deliberado: tres
páginas para un sitio sin contratación ni cuentas de usuario reparten en tres
sitios lo que se lee mejor de una vez.

Si algún día el sitio incorpora pagos, cuentas o contratación, esa decisión se
revisa: las condiciones de uso sí piden documento propio.

## Cada afirmación pública tiene su origen en el código

La página no describe intenciones, describe el sistema. Al cambiar cualquiera de
estas piezas hay que revisar la sección correspondiente, o la política pasa a
mentir:

| Afirmación publicada | Dónde se verifica |
|---|---|
| Del contenido conversacional, el navegador solo transmite la última pregunta | `frontend/src/lib/chat-engine.live.ts` |
| El servidor añade los seis últimos turnos de esa conversación, recortados y sin ampliar lo almacenado | `read_chat_history` en [`SUPABASE_CHAT.md`](SUPABASE_CHAT.md), `MAX_HISTORY_TURNS` en `frontend/netlify/functions/chat/conversation-history.ts` |
| Conocer el UUID de `/c/...` no permite leer el hilo; hace falta el secreto local y solo se guarda su SHA-256 | `authorize_chat_conversation` y `read_chat_history` en la migración forward-only `20260806015000_chat_history_possession.sql` |
| A pide al proveedor que no conserve la conversación | `store: false` en `frontend/netlify/functions/chat/provider-adapters.ts` |
| B busca en el almacén de los 106 PDF | `frontend/netlify/functions/chat/file-search-strategy.ts` |
| No se guardan IP, agente de usuario ni diagnóstico bruto | RPC de `public` descritas en [`SUPABASE_CHAT.md`](SUPABASE_CHAT.md) |
| Base de datos en Irlanda, esquema privado sin acceso del navegador | proyecto `eu-west-1`, schema `private` con RLS |
| Cinco peticiones por IP y minuto | `config.rateLimit` en `frontend/netlify/functions/chat/chat.ts` |
| 15 días de conservación con purga diaria auditada | `CHAT_RETENTION_DAYS` y `scripts/privacy/purge-chat-data.sh` |
| Las copias tienen su propio plazo y no se reescriben una a una | `BACKUP_RETENTION_DAYS` en [`BACKUPS.md`](BACKUPS.md) |
| Exclusión permanente de la analítica en un clic | `frontend/src/lib/analytics-optout.ts` |
| El registro de errores borra cabeceras, cookies y cuerpo | `frontend/src/lib/sentry-runtime.ts`, `src/api/sentry_config.py` |

Los ocho encargados listados en la sección 6 son los que intervienen hoy. **No se
listan proveedores previstos ni se conserva uno retirado**: una tabla de
encargados que no corresponde con la realidad es peor que no tenerla.

## Decisión: sin representante en la UE

**Decidido el 1 de agosto de 2026. No es una tarea pendiente ni un olvido.**

El art. 3.2 RGPD aplica al sitio: se ofrece en español a personas que están en
España y se mide su comportamiento con analítica. El art. 27 exige, a quien no
está establecido en la Unión y cae bajo ese supuesto, designar por escrito un
representante en un Estado miembro. **La titularidad es estadounidense, no hay
establecimiento en la Unión y no se va a designar representante.**

Consecuencias asumidas, escritas para que nadie las descubra por sorpresa:

- El incumplimiento del art. 27 está en el bloque sancionador del art. 83.4
  (techo de 10 M€ o el 2 % de la facturación mundial), graduable a la baja por el
  art. 83.2 según gravedad, volumen y ánimo de lucro.
- La excepción del art. 27.2.a —tratamiento ocasional, sin categorías especiales
  a gran escala y sin riesgo— **no se invoca**: las Directrices 3/2018 del CEPD
  leen «ocasional» como no regular ni estructural, y un chat disponible de forma
  continua que conserva preguntas quince días es tratamiento regular aunque tenga
  poco tráfico. Apoyarse en esa excepción sería construir una coartada, no un
  argumento.
- El disparador realista no es una inspección de oficio, sino una reclamación de
  un usuario: la identificación del responsable y el representante es lo primero
  que revisa una autoridad de control cuando abre expediente.

Reglas que se derivan de la decisión y que **no deben romperse al editar la
página**:

1. **No publicar un representante que no existe**, ni un buzón de terceros
   presentado como tal. Publicar uno inexistente convierte un incumplimiento
   formal en una declaración falsa.
2. **No afirmar que el representante no es necesario.** La página guarda silencio
   sobre el art. 27, que es distinto de negar la obligación. El silencio es
   sostenible; una negación publicada, no.
3. **No presentar la titularidad estadounidense como si eximiera del RGPD.** La
   política declara expresamente que el tratamiento se rige por el RGPD y la
   LOPDGDD, porque así es.
4. El resto del reglamento se cumple igual: bases jurídicas, minimización,
   plazos, derechos, autoridad de control y encargados están publicados y son
   verificables. La ausencia de representante es un hueco acotado, no una
   renuncia al marco.

Cuándo reabrir la decisión: si el sitio incorpora contratación o cuentas, si el
tráfico europeo deja de ser marginal, si llega una reclamación ante la AEPD, o si
la actividad pasa a ejercerse de forma estable desde la Unión —en cuyo caso el
supuesto aplicable sería el art. 3.1 y el art. 27 dejaría de venir al caso, con
las consecuencias societarias que eso arrastra y que exceden este documento.

## Lo que sigue abierto

- **Consentimiento previo de la analítica.** GA4 y PostHog se instalan sin
  recabarlo; `?no_analytics=1` es exclusión posterior, no el consentimiento
  previo del art. 22.2 LSSI. La política declara la medición bajo interés
  legítimo, que es lo que ocurre de hecho y no lo que la AEPD acepta para
  cookies. Se cierra con un banner que bloquee la analítica por defecto o con una
  configuración sin identificadores.
- **Contratos de encargo verificados** con Supabase, OpenAI, Google, Netlify,
  Cloudflare, Sentry y PostHog, y archivo de las condiciones de tratamiento en
  las que se apoyan las transferencias declaradas en la sección 6.
- **Validación jurídica formal del texto** y del plazo de quince días. La
  activación operativa del purgado no sustituye esa aprobación.

Ninguno de los tres bloquea el uso interno del chat. Los tres deben cerrarse
antes de difundirlo a terceros como servicio disponible.

## Ejercicio de derechos

Sin cuentas de usuario, una conversación se localiza operativamente por la
referencia técnica de supresión que `/privacidad` lee del estado local. Suele
coincidir con el UUID de la URL; tras migrar un historial antiguo puede ser el
`ledgerId` nuevo, que la página muestra sin revelar el secreto. Ni la referencia
ni el secreto **acreditan identidad**: el procedimiento exige verificación
por un canal separado y un ticket operativo antes de borrar nada
([`SUPABASE_CHAT.md`](SUPABASE_CHAT.md)). La respuesta al solicitante debe
informar de que la copia de seguridad que contenga el registro desaparece al
expirar su propio plazo, y **no puede prometer borrado inmediato de las copias**.
