/**
 * Renderiza la aplicación a HTML en tiempo de build.
 *
 * La SPA solo existía en el navegador: el HTML que servía Netlify era una shell
 * con `<div id="root"></div>`, así que sin JavaScript no había ni una línea de
 * texto. Un buscador que no ejecute el bundle —o que lo posponga— indexaba
 * páginas vacías, y eso vaciaba de sentido publicar las rutas de país.
 *
 * Aquí no hay servidor en producción: esto corre una vez por ruta durante
 * `npm run build` (`scripts/prerender.mjs`) y su salida se escribe en el HTML
 * estático. En el navegador sigue montando la misma aplicación de siempre.
 */
import { StrictMode } from 'react';
import { renderToString } from 'react-dom/server';
import { StaticRouter } from 'react-router';
import { App } from './App';
import { PreceptoPreloadContext, type PreceptoPreloadMap } from './lib/precepto-preload';
import { type SentenciaPreload, SentenciaPreloadContext } from './lib/sentencia-preload';
import { TreatyPreloadContext, type TreatyPreloadMap } from './lib/treaty-preload';

// Metadatos de las fichas de precepto: el prerender escribe exactamente los
// mismos títulos y descripciones que fija la página en runtime.
export {
  fichaDescription,
  fichaPath,
  fichaTitle,
  NORMATIVA_INDEX_PATH,
} from './lib/normativa-fichas';
export { PRECEPTO_PRELOAD_ELEMENT_ID } from './lib/precepto-preload';
// Metadatos de las fichas de sentencia, por el mismo motivo que los de las
// fichas de precepto: el prerender no puede componer un título distinto del
// que fija la página en runtime.
export {
  esBorrador,
  SENTENCIAS_INDEX_PATH,
  sentenciaDescription,
  sentenciaPath,
  sentenciasIndexDescription,
  sentenciasIndexPath,
  sentenciasIndexTitle,
  sentenciaTitle,
} from './lib/sentencia-metadata';
export { SENTENCIA_PRELOAD_ELEMENT_ID } from './lib/sentencia-preload';
// El prerender necesita el mismo identificador que leerá el navegador, y este
// módulo es su única puerta de entrada al código de la aplicación.
export { TREATY_PRELOAD_ELEMENT_ID } from './lib/treaty-preload';

export function render(
  url: string,
  treaties: TreatyPreloadMap = {},
  preceptos: PreceptoPreloadMap = {},
  sentencias: SentenciaPreload = { indexes: {}, fichas: {} }
): string {
  return renderToString(
    <StrictMode>
      <TreatyPreloadContext.Provider value={treaties}>
        <PreceptoPreloadContext.Provider value={preceptos}>
          <SentenciaPreloadContext.Provider value={sentencias}>
            <StaticRouter location={url}>
              <App />
            </StaticRouter>
          </SentenciaPreloadContext.Provider>
        </PreceptoPreloadContext.Provider>
      </TreatyPreloadContext.Provider>
    </StrictMode>
  );
}
