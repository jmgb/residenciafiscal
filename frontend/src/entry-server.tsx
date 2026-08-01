/**
 * Renderiza la aplicación a HTML en tiempo de build.
 *
 * La SPA solo existía en el navegador: el HTML que servía Netlify era una shell
 * con `<div id="root"></div>`, así que sin JavaScript no había ni una línea de
 * texto. Un buscador que no ejecute el bundle —o que lo posponga— indexaba
 * páginas vacías, y eso vaciaba de sentido publicar 29 rutas de país.
 *
 * Aquí no hay servidor en producción: esto corre una vez por ruta durante
 * `npm run build` (`scripts/prerender.mjs`) y su salida se escribe en el HTML
 * estático. En el navegador sigue montando la misma aplicación de siempre.
 */
import { StrictMode } from 'react';
import { renderToString } from 'react-dom/server';
import { StaticRouter } from 'react-router';
import { App } from './App';
import { TreatyPreloadContext, type TreatyPreloadMap } from './lib/treaty-preload';

// El prerender necesita el mismo identificador que leerá el navegador, y este
// módulo es su única puerta de entrada al código de la aplicación.
export { TREATY_PRELOAD_ELEMENT_ID } from './lib/treaty-preload';

export function render(url: string, treaties: TreatyPreloadMap = {}): string {
  return renderToString(
    <StrictMode>
      <TreatyPreloadContext.Provider value={treaties}>
        <StaticRouter location={url}>
          <App />
        </StaticRouter>
      </TreatyPreloadContext.Provider>
    </StrictMode>
  );
}
