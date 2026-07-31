/**
 * Recuperación cuando falla la carga de un chunk.
 *
 * Es el síntoma de haberse quedado atrás: el HTML que el navegador tiene
 * cargado desde hace días pide un módulo que el deploy actual ya no contiene.
 * Vite emite `vite:preloadError` y la vista se queda a medias. Recargar trae el
 * HTML nuevo y con él los nombres de chunk correctos.
 *
 * Solo un intento por bundle: si tras recargar vuelve a fallar, el problema es
 * otro e insistir sería un bucle de recargas delante del usuario.
 */
import { APP_RELEASE } from '@/lib/app-version';

export const PRELOAD_RECOVERY_STORAGE_KEY = 'rf.preload-recovery';

interface ModulePreloadRecoveryOptions {
  target?: EventTarget;
  storage?: Storage;
  reload?: () => void;
  release?: string;
}

function readAttemptedRelease(storage: Storage | undefined): string | null {
  try {
    return storage?.getItem(PRELOAD_RECOVERY_STORAGE_KEY) ?? null;
  } catch {
    // Safari en navegación privada lanza al tocar sessionStorage. Sin memoria
    // del intento previo, es mejor recargar una vez de más que dejar la app rota.
    return null;
  }
}

function rememberAttempt(storage: Storage | undefined, release: string): void {
  try {
    storage?.setItem(PRELOAD_RECOVERY_STORAGE_KEY, release);
  } catch {
    /* ver readAttemptedRelease */
  }
}

/** @returns función para dejar de escuchar. */
export function installModulePreloadRecovery({
  target = window,
  storage = typeof sessionStorage === 'undefined' ? undefined : sessionStorage,
  reload = () => window.location.reload(),
  release = APP_RELEASE,
}: ModulePreloadRecoveryOptions = {}): () => void {
  const onPreloadError = (event: Event): void => {
    // Sin esto Vite relanza el error y llega al ErrorBoundary, que enseñaría un
    // fallo genérico en lugar de la recarga que lo arregla.
    event.preventDefault();

    if (readAttemptedRelease(storage) === release) return;
    rememberAttempt(storage, release);
    reload();
  };

  target.addEventListener('vite:preloadError', onPreloadError);
  return () => target.removeEventListener('vite:preloadError', onPreloadError);
}
