import { jsonLdScript } from '@/lib/structured-data';

/**
 * Bloque `application/ld+json` incrustado en la página.
 *
 * Va dentro del árbol de React, y no en `index.html` ni en `prerender.mjs`, por
 * el mismo motivo que el resto del contenido: así el HTML prerenderizado y la
 * SPA no pueden divergir, y el dato se compone una sola vez desde el corpus.
 * Un `<script>` de datos no se ejecuta, así que el navegador lo ignora y el bot
 * lo lee.
 *
 * El JSON viaja como hijo de texto —React no lo escapa como HTML dentro de un
 * `<script>`— y `jsonLdScript` deja escapado el `<`, de modo que ninguna cadena
 * del BOE pueda cerrar la etiqueta ni en el servidor ni en el navegador.
 */
export function JsonLd({ data }: { data: unknown }) {
  return <script type='application/ld+json'>{jsonLdScript(data)}</script>;
}
