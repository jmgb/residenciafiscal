/**
 * Comprobación de la versión desplegada.
 *
 * Una SPA solo vuelve a pedir el HTML si el navegador decide revalidarlo, y un
 * móvil que conserva la pestaña abierta durante días no lo hace nunca. Esta es
 * la única vía por la que ese navegador se entera de que su bundle ya no es el
 * vigente: comparar la revisión compilada con la que publica `/version.json`
 * (`frontend/scripts/build-version.mjs`, servido con `no-store`).
 *
 * Todo error se traduce a «no hay nada nuevo». Una falsa alarma recarga la
 * página en la cara del usuario, y si el manifiesto no fuese fiable la recarga
 * se repetiría en bucle.
 */

/** Revisión compilada en este bundle. */
export const APP_RELEASE = __APP_RELEASE__;

export const VERSION_MANIFEST_PATH = '/version.json';

/** Valor que devuelve el cálculo de release fuera de un despliegue. */
const DEVELOPMENT_RELEASE = 'local';

interface VersionCheckOptions {
  currentRelease?: string;
  fetchImpl?: typeof fetch;
}

async function fetchDeployedRelease(fetchImpl: typeof fetch): Promise<string | null> {
  try {
    const response = await fetchImpl(VERSION_MANIFEST_PATH, {
      cache: 'no-store',
      headers: { Accept: 'application/json' },
    });
    if (!response.ok) return null;

    // El fallback `/* → /index.html` de Netlify devolvería la shell con 200. Sin
    // esta comprobación, un JSON.parse fallido o —peor— un HTML interpretado
    // como manifiesto acabaría en recarga infinita.
    if (!(response.headers.get('content-type') ?? '').includes('application/json')) return null;

    const payload: unknown = await response.json();
    const release = (payload as { release?: unknown }).release;
    return typeof release === 'string' && release.trim() !== '' ? release : null;
  } catch {
    return null;
  }
}

/** `true` solo si el despliegue publicado es demostrablemente otro. */
export async function isNewVersionDeployed({
  currentRelease = APP_RELEASE,
  fetchImpl = fetch,
}: VersionCheckOptions = {}): Promise<boolean> {
  if (!currentRelease || currentRelease === DEVELOPMENT_RELEASE) return false;

  const deployedRelease = await fetchDeployedRelease(fetchImpl);
  return deployedRelease !== null && deployedRelease !== currentRelease;
}
