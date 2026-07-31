/**
 * Aviso de versión nueva.
 *
 * Solo aparece cuando recargar destruiría algo (una respuesta llegando, una
 * pregunta a medio escribir); en cualquier otro caso la actualización es
 * silenciosa y este componente no llega a pintar nada.
 */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { AppUpdateBanner } from '@/components/layout/AppUpdateBanner';

describe('AppUpdateBanner', () => {
  it('no interrumpe mientras el despliegue siga siendo el mismo', async () => {
    const checkVersion = vi.fn(async () => false);

    render(<AppUpdateBanner checkVersion={checkVersion} isBusy={() => true} reload={vi.fn()} />);

    await waitFor(() => expect(checkVersion).toHaveBeenCalled());
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('avisa de la versión nueva sin recargar por su cuenta', async () => {
    const reload = vi.fn();

    render(<AppUpdateBanner checkVersion={async () => true} isBusy={() => true} reload={reload} />);

    expect(await screen.findByRole('status')).toHaveTextContent(/versión nueva/i);
    expect(reload).not.toHaveBeenCalled();
  });

  it('recarga cuando el usuario acepta actualizar', async () => {
    const reload = vi.fn();
    const user = userEvent.setup();

    render(<AppUpdateBanner checkVersion={async () => true} isBusy={() => true} reload={reload} />);
    await user.click(await screen.findByRole('button', { name: /actualizar/i }));

    expect(reload).toHaveBeenCalledTimes(1);
  });
});
