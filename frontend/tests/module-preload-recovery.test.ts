/**
 * Recuperación cuando falla la carga de un chunk.
 *
 * Es el síntoma de haberse quedado atrás: el HTML cargado hace días pide un
 * módulo que el deploy actual ya no contiene. Vite emite `vite:preloadError` y
 * la app se queda a medias; recargar la arregla, pero solo una vez por bundle:
 * si el fallo persiste, insistir sería un bucle de recargas.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  installModulePreloadRecovery,
  PRELOAD_RECOVERY_STORAGE_KEY,
} from '@/lib/module-preload-recovery';

function firePreloadError(target: EventTarget): Event {
  const event = new Event('vite:preloadError', { cancelable: true });
  target.dispatchEvent(event);
  return event;
}

let storage: Storage;

beforeEach(() => {
  window.sessionStorage.clear();
  storage = window.sessionStorage;
});

describe('installModulePreloadRecovery', () => {
  it('recarga cuando un módulo del deploy anterior ya no existe', () => {
    const target = new EventTarget();
    const reload = vi.fn();

    installModulePreloadRecovery({ target, storage, reload, release: 'a1a1a1a1a1a1' });
    firePreloadError(target);

    expect(reload).toHaveBeenCalledTimes(1);
  });

  it('no vuelve a recargar por el mismo bundle', () => {
    const target = new EventTarget();
    const reload = vi.fn();

    installModulePreloadRecovery({ target, storage, reload, release: 'a1a1a1a1a1a1' });
    firePreloadError(target);
    firePreloadError(target);

    expect(reload).toHaveBeenCalledTimes(1);
    expect(storage.getItem(PRELOAD_RECOVERY_STORAGE_KEY)).toBe('a1a1a1a1a1a1');
  });

  it('vuelve a intentarlo cuando el bundle ya es otro', () => {
    const target = new EventTarget();
    const reload = vi.fn();
    storage.setItem(PRELOAD_RECOVERY_STORAGE_KEY, 'a1a1a1a1a1a1');

    installModulePreloadRecovery({ target, storage, reload, release: 'b2b2b2b2b2b2' });
    firePreloadError(target);

    expect(reload).toHaveBeenCalledTimes(1);
  });

  it('evita que el error de carga llegue al usuario', () => {
    const target = new EventTarget();

    installModulePreloadRecovery({ target, storage, reload: vi.fn(), release: 'a1a1a1a1a1a1' });

    expect(firePreloadError(target).defaultPrevented).toBe(true);
  });

  it('sigue recargando aunque el almacenamiento no esté disponible', () => {
    // Safari en navegación privada lanza al escribir en sessionStorage.
    const target = new EventTarget();
    const reload = vi.fn();
    const brokenStorage = {
      getItem: () => {
        throw new DOMException('denied', 'SecurityError');
      },
      setItem: () => {
        throw new DOMException('denied', 'SecurityError');
      },
    } as unknown as Storage;

    installModulePreloadRecovery({
      target,
      storage: brokenStorage,
      reload,
      release: 'a1a1a1a1a1a1',
    });
    firePreloadError(target);

    expect(reload).toHaveBeenCalledTimes(1);
  });

  it('deja de escuchar cuando se desinstala', () => {
    const target = new EventTarget();
    const reload = vi.fn();

    installModulePreloadRecovery({ target, storage, reload, release: 'a1a1a1a1a1a1' })();
    firePreloadError(target);

    expect(reload).not.toHaveBeenCalled();
  });
});
