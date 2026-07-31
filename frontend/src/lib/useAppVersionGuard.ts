/**
 * Mantiene la pestaña en la última versión desplegada.
 *
 * Una SPA no vuelve a pedir el HTML por su cuenta: mientras la pestaña viva,
 * sigue ejecutando el bundle con el que se cargó. En un móvil eso significa
 * días, porque el navegador restaura la pestaña desde el back/forward cache en
 * lugar de recargarla. Aquí se comprueba al arrancar, al recuperar el foco y al
 * volver del bfcache, que son los tres momentos en los que el usuario está
 * mirando.
 *
 * Recargar tiene coste —se pierde la respuesta a medio escribir o a medio
 * llegar—, así que solo es automático si no hay nada en curso. Si lo hay, se
 * avisa y decide el usuario.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { isNewVersionDeployed } from '@/lib/app-version';

/** Cambiar de app y volver dispara `visibilitychange` sin parar. */
const MINIMUM_CHECK_INTERVAL_MS = 30_000;

interface AppVersionGuardOptions {
  /** `true` mientras haya algo que una recarga destruiría. */
  isBusy: () => boolean;
  checkVersion?: () => Promise<boolean>;
  reload?: () => void;
  now?: () => number;
  minimumIntervalMs?: number;
}

interface AppVersionGuard {
  updateAvailable: boolean;
  applyUpdate: () => void;
}

export function useAppVersionGuard({
  isBusy,
  checkVersion = () => isNewVersionDeployed(),
  reload = () => window.location.reload(),
  now = () => Date.now(),
  minimumIntervalMs = MINIMUM_CHECK_INTERVAL_MS,
}: AppVersionGuardOptions): AppVersionGuard {
  const [updateAvailable, setUpdateAvailable] = useState(false);

  // Por referencia: los listeners se registran una vez y no deben volver a
  // hacerlo porque el consumidor pase una función nueva en cada render.
  const optionsRef = useRef({ isBusy, checkVersion, reload, now });
  optionsRef.current = { isBusy, checkVersion, reload, now };

  const lastCheckRef = useRef(Number.NEGATIVE_INFINITY);

  const applyUpdate = useCallback(() => {
    optionsRef.current.reload();
  }, []);

  useEffect(() => {
    let cancelled = false;

    const check = async (): Promise<void> => {
      const options = optionsRef.current;
      const timestamp = options.now();
      if (timestamp - lastCheckRef.current < minimumIntervalMs) return;
      lastCheckRef.current = timestamp;

      const hasNewVersion = await options.checkVersion();
      if (cancelled || !hasNewVersion) return;

      if (options.isBusy()) {
        setUpdateAvailable(true);
        return;
      }
      options.reload();
    };

    const onVisibilityChange = (): void => {
      if (document.visibilityState === 'visible') void check();
    };

    const onPageShow = (event: PageTransitionEvent): void => {
      // Solo la restauración desde el bfcache: una carga normal ya comprueba al
      // montar, y contarla dos veces gasta el intervalo mínimo para nada.
      if (event.persisted) void check();
    };

    void check();
    document.addEventListener('visibilitychange', onVisibilityChange);
    window.addEventListener('pageshow', onPageShow);

    return () => {
      cancelled = true;
      document.removeEventListener('visibilitychange', onVisibilityChange);
      window.removeEventListener('pageshow', onPageShow);
    };
  }, [minimumIntervalMs]);

  return { updateAvailable, applyUpdate };
}
