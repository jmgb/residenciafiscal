/**
 * Comprobación de versión desplegada.
 *
 * Es el mecanismo que permite a un navegador con la pestaña abierta desde hace
 * días enterarse de que su bundle ya no es el vigente. Falla siempre hacia «no
 * hay nada nuevo»: una falsa alarma recarga la página en la cara del usuario,
 * que es peor que tardar un rato más en actualizarse.
 */
import { describe, expect, it, vi } from 'vitest';
import { isNewVersionDeployed, VERSION_MANIFEST_PATH } from '@/lib/app-version';

function respondWith(body: string, init: ResponseInit = {}): typeof fetch {
  return vi.fn(
    async () =>
      new Response(body, {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        ...init,
      })
  ) as unknown as typeof fetch;
}

describe('isNewVersionDeployed', () => {
  it('detecta que el despliegue publicado ya no es el del bundle', async () => {
    const fetchImpl = respondWith(JSON.stringify({ release: 'b2b2b2b2b2b2' }));

    expect(await isNewVersionDeployed({ currentRelease: 'a1a1a1a1a1a1', fetchImpl })).toBe(true);
  });

  it('no señala nada cuando el despliegue publicado es el mismo', async () => {
    const fetchImpl = respondWith(JSON.stringify({ release: 'a1a1a1a1a1a1' }));

    expect(await isNewVersionDeployed({ currentRelease: 'a1a1a1a1a1a1', fetchImpl })).toBe(false);
  });

  it('pide el manifiesto saltándose la caché', async () => {
    const fetchImpl = respondWith(JSON.stringify({ release: 'a1a1a1a1a1a1' }));

    await isNewVersionDeployed({ currentRelease: 'a1a1a1a1a1a1', fetchImpl });

    expect(fetchImpl).toHaveBeenCalledWith(
      VERSION_MANIFEST_PATH,
      expect.objectContaining({ cache: 'no-store' })
    );
  });

  it('ignora la shell HTML que devuelve el fallback de la SPA', async () => {
    // Si algún día se cae la regla de 404, `/version.json` responde 200 con el
    // index. Interpretarlo como versión nueva recargaría en bucle infinito.
    const fetchImpl = respondWith('<!doctype html><html lang="es"></html>', {
      headers: { 'Content-Type': 'text/html; charset=UTF-8' },
    });

    expect(await isNewVersionDeployed({ currentRelease: 'a1a1a1a1a1a1', fetchImpl })).toBe(false);
  });

  it('ignora un manifiesto sin release utilizable', async () => {
    const fetchImpl = respondWith(JSON.stringify({ release: '   ' }));

    expect(await isNewVersionDeployed({ currentRelease: 'a1a1a1a1a1a1', fetchImpl })).toBe(false);
  });

  it('ignora una respuesta de error', async () => {
    const fetchImpl = respondWith('', { status: 404 });

    expect(await isNewVersionDeployed({ currentRelease: 'a1a1a1a1a1a1', fetchImpl })).toBe(false);
  });

  it('ignora un fallo de red', async () => {
    const fetchImpl = vi.fn(async () => {
      throw new TypeError('Failed to fetch');
    }) as unknown as typeof fetch;

    expect(await isNewVersionDeployed({ currentRelease: 'a1a1a1a1a1a1', fetchImpl })).toBe(false);
  });

  it('no compara nada cuando el bundle es de desarrollo', async () => {
    // `local` es lo que devuelve el cálculo de release fuera de un despliegue:
    // comparar ahí recargaría el navegador del desarrollador sin parar.
    const fetchImpl = respondWith(JSON.stringify({ release: 'b2b2b2b2b2b2' }));

    expect(await isNewVersionDeployed({ currentRelease: 'local', fetchImpl })).toBe(false);
    expect(fetchImpl).not.toHaveBeenCalled();
  });
});
