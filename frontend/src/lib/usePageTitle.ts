import { useEffect } from 'react';

/** Título por defecto: el mismo que declara index.html para la home. */
const BASE_TITLE = 'Residencia Fiscal — Consulta la jurisprudencia del art. 9 LIRPF';
const BASE_DESCRIPTION =
  'Consulta en lenguaje natural 106 sentencias del Tribunal Supremo y la Audiencia Nacional sobre residencia fiscal de personas físicas en España.';

const ORIGIN = 'https://residenciafiscal.org';

/**
 * Fija el título del documento y el canonical de la página actual. Sin
 * argumentos restaura los valores por defecto de la home (las conversaciones
 * `/c/:id` son privadas y canonicalizan a la raíz).
 *
 * Limitación conocida: los bots sociales no ejecutan JS, así que las tarjetas
 * OG de las rutas internas muestran los metadatos de la home hasta que haya
 * prerender. Google sí renderiza JS y respeta este canonical.
 */
export function usePageTitle(title?: string, canonicalPath = '/', description = BASE_DESCRIPTION) {
  useEffect(() => {
    document.title = title ? `${title} — Residencia Fiscal` : BASE_TITLE;
    document
      .querySelector('link[rel="canonical"]')
      ?.setAttribute('href', `${ORIGIN}${canonicalPath}`);
    document.querySelector('meta[name="description"]')?.setAttribute('content', description);
    document.querySelector('meta[property="og:title"]')?.setAttribute('content', document.title);
    document.querySelector('meta[property="og:description"]')?.setAttribute('content', description);
    document
      .querySelector('meta[property="og:url"]')
      ?.setAttribute('content', `${ORIGIN}${canonicalPath}`);
    document.querySelector('meta[name="twitter:title"]')?.setAttribute('content', document.title);
    document
      .querySelector('meta[name="twitter:description"]')
      ?.setAttribute('content', description);
  }, [title, canonicalPath, description]);
}
