/**
 * Guardián de versión: cuándo se recarga y cuándo no.
 *
 * El caso que gobierna el diseño es un móvil que conserva la pestaña abierta
 * días: no revalida el HTML por su cuenta, así que hay que comprobarlo al
 * volver a la pestaña. Y recargar tiene coste —se pierde lo que el usuario
 * estuviera haciendo—, de modo que solo es automático si no hay nada en curso.
 */
import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAppVersionGuard } from '@/lib/useAppVersionGuard';

function fireVisible(): void {
  act(() => {
    document.dispatchEvent(new Event('visibilitychange'));
  });
}

function fireBackForwardCacheRestore(): void {
  act(() => {
    const event = new Event('pageshow');
    Object.defineProperty(event, 'persisted', { value: true });
    window.dispatchEvent(event);
  });
}

let clock = 0;
const now = () => clock;

beforeEach(() => {
  clock = 0;
});

describe('useAppVersionGuard', () => {
  it('recarga sola cuando hay versión nueva y no hay nada en curso', async () => {
    const reload = vi.fn();

    renderHook(() =>
      useAppVersionGuard({
        checkVersion: async () => true,
        isBusy: () => false,
        reload,
        now,
      })
    );

    await waitFor(() => expect(reload).toHaveBeenCalledTimes(1));
  });

  it('no recarga nada cuando el despliegue sigue siendo el mismo', async () => {
    const reload = vi.fn();
    const checkVersion = vi.fn(async () => false);

    const { result } = renderHook(() =>
      useAppVersionGuard({ checkVersion, isBusy: () => false, reload, now })
    );

    await waitFor(() => expect(checkVersion).toHaveBeenCalled());
    expect(reload).not.toHaveBeenCalled();
    expect(result.current.updateAvailable).toBe(false);
  });

  it('avisa en vez de recargar cuando hay una respuesta en curso', async () => {
    const reload = vi.fn();

    const { result } = renderHook(() =>
      useAppVersionGuard({
        checkVersion: async () => true,
        isBusy: () => true,
        reload,
        now,
      })
    );

    await waitFor(() => expect(result.current.updateAvailable).toBe(true));
    expect(reload).not.toHaveBeenCalled();
  });

  it('recarga cuando el usuario acepta el aviso', async () => {
    const reload = vi.fn();

    const { result } = renderHook(() =>
      useAppVersionGuard({
        checkVersion: async () => true,
        isBusy: () => true,
        reload,
        now,
      })
    );

    await waitFor(() => expect(result.current.updateAvailable).toBe(true));
    act(() => {
      result.current.applyUpdate();
    });

    expect(reload).toHaveBeenCalledTimes(1);
  });

  it('vuelve a comprobar cuando la pestaña recupera el foco', async () => {
    const checkVersion = vi.fn(async () => false);

    renderHook(() =>
      useAppVersionGuard({ checkVersion, isBusy: () => false, reload: vi.fn(), now })
    );
    await waitFor(() => expect(checkVersion).toHaveBeenCalledTimes(1));

    clock += 60_000;
    fireVisible();

    await waitFor(() => expect(checkVersion).toHaveBeenCalledTimes(2));
  });

  it('vuelve a comprobar cuando la página se restaura del back/forward cache', async () => {
    const checkVersion = vi.fn(async () => false);

    renderHook(() =>
      useAppVersionGuard({ checkVersion, isBusy: () => false, reload: vi.fn(), now })
    );
    await waitFor(() => expect(checkVersion).toHaveBeenCalledTimes(1));

    clock += 60_000;
    fireBackForwardCacheRestore();

    await waitFor(() => expect(checkVersion).toHaveBeenCalledTimes(2));
  });

  it('no repite la comprobación mientras el intervalo mínimo no haya pasado', async () => {
    // Cambiar de app y volver dispara `visibilitychange` continuamente: sin
    // freno, cada gesto del usuario sería una petición de red.
    const checkVersion = vi.fn(async () => false);

    renderHook(() =>
      useAppVersionGuard({ checkVersion, isBusy: () => false, reload: vi.fn(), now })
    );
    await waitFor(() => expect(checkVersion).toHaveBeenCalledTimes(1));

    clock += 5_000;
    fireVisible();
    fireVisible();

    expect(checkVersion).toHaveBeenCalledTimes(1);
  });
});
